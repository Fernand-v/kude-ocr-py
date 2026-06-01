"""Prueba OCR por CLI (sin servidor) sobre las imágenes de img_pruebas.

Uso:  ./venv/bin/python probar.py [archivo.png ...]
Sin args procesa todas. Pensado para correr bajo `ulimit -v` para que un
pico de memoria no tumbe el sistema entero.
"""
import json
import sys

from app.ocr_engine import extraer_lineas
from app.parser import parsear

archivos = sys.argv[1:] or [
    "img_pruebas/Imagen pegada (2).png",
    "img_pruebas/Imagen pegada.png",
    "img_pruebas/Imagen pegada (3).png",
]

for ruta in archivos:
    print(f"\n############ {ruta} ############")
    lineas = extraer_lineas(ruta)
    textos = [ln.texto for ln in lineas]
    campos = parsear("\n".join(textos), textos)
    print("--- CAMPOS ---")
    print(json.dumps(campos, indent=2, ensure_ascii=False))
    print("--- TEXTO ---")
    print("\n".join(textos))
