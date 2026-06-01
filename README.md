# kude-ocr-py — microservicio OCR de facturas

OCR aislado. Recibe imagen de factura por HTTP, devuelve JSON con campos
extraídos. Corre **local** (PaddleOCR), no manda datos a ningún lado.

## Arquitectura

```
[tu sistema]  --POST imagen-->  [este servicio :8000]  --JSON-->  [tu sistema]
```

El OCR vive solo acá. Todo lo demás consume `/extraer`.

## Requisitos

- Python 3.10+ (probado en 3.12)
- ~2 GB de disco (modelos PaddleOCR se descargan en el primer arranque)
- Linux/macOS/WSL

## Instalación

```bash
# 1. Clonar
git clone https://github.com/<tu-usuario>/kude-ocr-py.git
cd kude-ocr-py

# 2. Entorno virtual (Ubuntu marca el Python del sistema como
#    "externally-managed", por eso usamos venv)
python3 -m venv venv

# 3. Dependencias
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

La primera vez que llega una imagen, PaddleOCR descarga los modelos
(det + rec mobile) a `~/.paddlex/`. Tarda; las siguientes ya van cacheadas.

## Levantar

```bash
./run.sh
# o:  ./venv/bin/uvicorn app.main:app --port 8000
```

## Endpoints

| Método | Ruta       | Descripción                          |
|--------|------------|--------------------------------------|
| GET    | `/salud`   | Healthcheck                          |
| POST   | `/extraer` | Sube imagen (`file`), devuelve JSON  |
| GET    | `/docs`    | Swagger UI (probar desde el browser) |

## Probar

```bash
curl -X POST http://localhost:8000/extraer \
  -F "file=@factura.jpg"
```

## Respuesta

```json
{
  "archivo": "factura.png",
  "campos": {
    "ruc_emisor": "80011122-3",
    "razon_social_emisor": "EMPRESA EJEMPLO",
    "timbrado": "14722988",
    "fecha_inicio_vigencia": "12/03/2021",
    "numero_factura": "001-001-7719249",
    "condicion_venta": "Contado",
    "fecha_emision": "31/12/2025",
    "ruc_ci_cliente": "80044455-6",
    "nombre_cliente": "CLIENTE EJEMPLO SOCIEDAD ANÓNIMA",
    "moneda": "PYG",
    "total": 128334,
    "total_iva": 11667
  },
  "texto_completo": "...",
  "lineas": [{"texto": "...", "confianza": 0.98, "caja": [x0,y0,x1,y1]}]
}
```

Verificado contra 3 formatos reales: factura electrónica (KuDE), ticket de
supermercado y factura de banco.

## Consumir desde tu sistema (el POST)

Tu sistema (el "servidor ajeno") le manda la imagen a este servicio y recibe
el JSON. Ejemplo completo en [cliente_ejemplo.py](cliente_ejemplo.py).

**Lo único que configurás es la URL del servicio**, en la constante
`OCR_URL`:

```python
import requests

OCR_URL = "http://localhost:8000"        # mismo equipo
# OCR_URL = "http://192.168.1.50:8000"   # servicio en otro equipo de la red

def extraer_factura(ruta_imagen):
    with open(ruta_imagen, "rb") as f:
        resp = requests.post(
            f"{OCR_URL}/extraer",
            files={"file": (ruta_imagen, f, "image/png")},
            timeout=180,
        )
    resp.raise_for_status()
    return resp.json()

datos = extraer_factura("factura.png")
print(datos["campos"]["total"])
```

Desde otro lenguaje, es un `multipart/form-data` POST a `/extraer` con el
campo `file`. Equivalente en curl:

```bash
curl -X POST http://localhost:8000/extraer -F "file=@factura.png"
```

> Para exponer el servicio a otros equipos, levantalo con
> `--host 0.0.0.0` (ya lo hace [run.sh](run.sh)) y abrí el puerto 8000 en el
> firewall. Está pensado para red interna; no lo publiques a internet sin un
> proxy/auth delante.

## Probar sin servidor (CLI)

```bash
./venv/bin/python probar.py "img_pruebas/factura.png"
# sin args procesa todas las de img_pruebas/
```

## Notas

- `campos` es **best-effort** por regex/heurística; cada campo puede venir
  `null`. `texto_completo` y `lineas` siempre vienen para parseo propio.
- **Montos** son enteros en guaraníes (PYG no tiene centavos); se quitan
  todos los separadores de miles (`.` o `,` según el POS).
- `total_iva` viene `null` si la factura no trae una línea rotulada
  "TOTAL IVA" (algunos tickets solo listan el monto suelto).
- `razon_social_emisor` es la más difícil de aislar; el `ruc_emisor`
  identifica al emisor de forma única igual.
- La imagen del cliente se borra del disco apenas se procesa.
- Reglas de extracción en [app/parser.py](app/parser.py).

## Memoria / seguridad (importante)

Facturas escaneadas A4 vienen a ~9 MP. PaddleOCR aloca RAM de forma
~cuadrática con la resolución: una imagen grande con el modelo de detección
"server" intentó alocar **46 GB** y disparó el OOM killer (tumba el sistema).
Mitigaciones ya aplicadas:

- La imagen se **reescala** a 1600 px de lado máx antes del OCR
  ([app/ocr_engine.py](app/ocr_engine.py), `MAX_LADO`).
- Se usan los modelos **mobile** (det + rec), no los "server".
- Tope interno del detector a 1280 px.
- [run.sh](run.sh) pone `ulimit -v 8000000`: si algo se dispara, muere solo
  el proceso, no la máquina.
