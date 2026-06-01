"""Microservicio de OCR de facturas.

Recibe la imagen por HTTP, hace OCR + extracción, devuelve JSON.
El OCR vive aislado acá; el resto del sistema solo consume esta API.
"""
from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.ocr_engine import extraer_lineas
from app.parser import parsear

app = FastAPI(title="OCR Facturas", version="1.0")

# Tipos de imagen aceptados
TIPOS_OK = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/tiff"}
MAX_BYTES = 15 * 1024 * 1024  # 15 MB


@app.get("/salud")
def salud():
    """Healthcheck simple para el sistema consumidor."""
    return {"estado": "ok"}


@app.post("/extraer")
async def extraer(file: UploadFile):
    if file.content_type not in TIPOS_OK:
        raise HTTPException(415, f"Tipo no soportado: {file.content_type}")

    contenido = await file.read()
    if len(contenido) == 0:
        raise HTTPException(400, "Archivo vacío")
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, "Imagen demasiado grande (máx 15 MB)")

    suf = os.path.splitext(file.filename or "")[1] or ".jpg"
    ruta = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suf, delete=False) as tmp:
            tmp.write(contenido)
            ruta = tmp.name

        lineas = extraer_lineas(ruta)
        textos = [ln.texto for ln in lineas]
        campos = parsear("\n".join(textos), textos)

        return JSONResponse(
            {
                "archivo": file.filename,
                "campos": campos,
                "texto_completo": "\n".join(textos),
                "lineas": [
                    {"texto": ln.texto, "confianza": round(ln.confianza, 4), "caja": ln.caja}
                    for ln in lineas
                ],
            }
        )
    finally:
        if ruta and os.path.exists(ruta):
            os.remove(ruta)  # no dejamos la imagen del cliente en disco
