"""Wrapper de PaddleOCR aislado del resto del sistema.

Carga el modelo una sola vez (es caro) y normaliza la salida, que cambia
de formato entre versiones 2.x y 3.x de PaddleOCR.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

import numpy as np
from PIL import Image, ImageOps
from paddleocr import PaddleOCR

# Lado máximo en píxeles. Imágenes más grandes se reescalan antes del OCR:
# paddle aloca memoria ~cuadrática con la resolución y revienta (vimos un
# intento de 46 GB con un PNG escaneado a alta resolución).
MAX_LADO = 1600


@dataclass
class Linea:
    """Una línea de texto detectada con su caja y confianza."""
    texto: str
    confianza: float
    # caja = [x_min, y_min, x_max, y_max] (bounding box rectangular)
    caja: list[float]


_ocr: PaddleOCR | None = None
_lock = Lock()


def _get_ocr() -> PaddleOCR:
    """Carga perezosa + thread-safe del modelo."""
    global _ocr
    if _ocr is None:
        with _lock:
            if _ocr is None:
                # lang='es' usa el modelo latino (cubre español/guaraní).
                # En PaddleOCR 3.x los argumentos cambiaron: probamos la
                # firma nueva y caemos a la vieja (2.x) si no aplica.
                try:
                    _ocr = PaddleOCR(
                        lang="es",
                        use_textline_orientation=True,
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        # MKLDNN/oneDNN rompe en algunas CPUs con paddle 3.x
                        # (ConvertPirAttribute2RuntimeAttribute). Lo apagamos.
                        enable_mkldnn=False,
                        # Modelo de detección MOBILE (no server): el server_det
                        # alocaba varios GB con A4 a alta resolución y disparaba
                        # el OOM killer del sistema.
                        text_detection_model_name="PP-OCRv5_mobile_det",
                        # Nombrar el det resetea el rec al server (pesado): lo
                        # forzamos de vuelta al latin mobile (liviano, español).
                        text_recognition_model_name="latin_PP-OCRv5_mobile_rec",
                        # Tope duro interno: el lado mayor que entra al detector
                        # se limita a 1280 px. Evita feature maps gigantes.
                        text_det_limit_side_len=1280,
                        text_det_limit_type="max",
                    )
                except (TypeError, ValueError):
                    _ocr = PaddleOCR(use_angle_cls=True, lang="es")
    return _ocr


def _bbox_rect(poly) -> list[float]:
    """Convierte un polígono de 4 puntos a [x_min, y_min, x_max, y_max]."""
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    return [min(xs), min(ys), max(xs), max(ys)]


def _cargar_imagen(ruta: str) -> np.ndarray:
    """Abre, corrige orientación EXIF, pasa a RGB y limita el tamaño.

    Devuelve un array numpy que paddle acepta directamente, evitando que
    reprocese un archivo gigante en disco.
    """
    img = Image.open(ruta)
    img = ImageOps.exif_transpose(img)  # respeta rotación de la cámara
    img = img.convert("RGB")
    w, h = img.size
    lado = max(w, h)
    if lado > MAX_LADO:
        escala = MAX_LADO / lado
        img = img.resize((round(w * escala), round(h * escala)), Image.LANCZOS)
    return np.asarray(img)


def extraer_lineas(ruta: str) -> list[Linea]:
    """Corre OCR sobre la imagen y devuelve líneas normalizadas.

    Soporta tanto la API vieja (ocr.ocr) como la nueva (ocr.predict).
    """
    ocr = _get_ocr()
    img = _cargar_imagen(ruta)

    # --- API 3.x: predict() -> lista de dicts con rec_texts/rec_polys ---
    if hasattr(ocr, "predict"):
        try:
            resultado = ocr.predict(input=img)
            lineas: list[Linea] = []
            for bloque in resultado:
                d = bloque if isinstance(bloque, dict) else getattr(bloque, "json", {}).get("res", {})
                textos = d.get("rec_texts", [])
                scores = d.get("rec_scores", [])
                polys = d.get("rec_polys", d.get("dt_polys", []))
                for i, txt in enumerate(textos):
                    score = float(scores[i]) if i < len(scores) else 0.0
                    poly = polys[i] if i < len(polys) else [[0, 0], [0, 0], [0, 0], [0, 0]]
                    lineas.append(Linea(txt, score, _bbox_rect(poly)))
            if lineas:
                return lineas
        except (TypeError, AttributeError, KeyError):
            pass  # cae al formato viejo

    # --- API 2.x: ocr.ocr() -> [[ [poly, (texto, score)], ... ]] ---
    resultado = ocr.ocr(img, cls=True)
    lineas = []
    for bloque in resultado or []:
        for item in bloque or []:
            poly, (texto, score) = item[0], item[1]
            lineas.append(Linea(texto, float(score), _bbox_rect(poly)))
    return lineas
