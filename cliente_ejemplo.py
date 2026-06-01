"""Ejemplo de CLIENTE: cómo TU sistema le manda la imagen al servicio OCR.

Este archivo NO es parte del servidor. Es la pieza que va en tu sistema
(el "servidor ajeno" que consume la API). Copia esta función a tu proyecto
y cambiá OCR_URL por la dirección donde corre el microservicio.

Requiere:  pip install requests
"""
import sys

import requests

# <<< ACÁ va la dirección del servicio OCR >>>
# Mismo equipo:        http://localhost:8000
# Otro equipo en red:  http://IP_DEL_SERVIDOR:8000
OCR_URL = "http://localhost:8000"


def extraer_factura(ruta_imagen: str, timeout: int = 180) -> dict:
    """Envía una imagen al servicio OCR y devuelve el JSON con los campos."""
    with open(ruta_imagen, "rb") as f:
        archivos = {"file": (ruta_imagen, f, "image/png")}
        resp = requests.post(f"{OCR_URL}/extraer", files=archivos, timeout=timeout)
    resp.raise_for_status()  # lanza si el server devolvió 4xx/5xx
    return resp.json()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python cliente_ejemplo.py <ruta_imagen>")
        sys.exit(1)

    datos = extraer_factura(sys.argv[1])
    campos = datos["campos"]
    print("RUC emisor :", campos["ruc_emisor"])
    print("Nro factura:", campos["numero_factura"])
    print("Total      :", campos["total"])
    print("Total IVA  :", campos["total_iva"])
    # datos["texto_completo"] y datos["lineas"] traen el OCR crudo completo.
