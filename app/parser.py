"""Extracción de campos de una factura paraguaya a partir del texto OCR.

Probado contra 3 formatos reales: factura electrónica (KuDE), ticket de
supermercado, y factura de banco. Es best-effort: cada campo puede venir
None. El texto crudo siempre se devuelve para parseo propio.

Notas de formato paraguayo:
- Guaraníes (PYG) no tienen centavos. Miles se separan con '.' o ',' según
  el sistema POS, así que para montos quitamos TODOS los separadores.
- Etiqueta y valor suelen quedar en líneas distintas tras el OCR, por eso
  buscamos el valor "hacia adelante" desde la etiqueta.
"""
from __future__ import annotations

import re

# --- Identificadores ---------------------------------------------------------
# RUC paraguayo: 6-9 dígitos + guion + verificador. Ej: 80012345-6
RE_RUC = re.compile(r"\b(\d{5,9}-\d)\b")
# Timbrado: 7-8 dígitos tras la palabra "Timbrado".
RE_TIMBRADO = re.compile(r"timbrado\s*(?:electr[oó]nico)?\s*n?[º°o]?\.?\s*:?\s*(\d{7,8})", re.I)
# Número de factura: 3-3-(6 o 7), separados por '-' o espacio. Ej: 001-001-0026820
RE_NRO_FACTURA = re.compile(r"\b(\d{3})[\s\-](\d{3})[\s\-](\d{6,7})\b")

# --- Fechas ------------------------------------------------------------------
# dd/mm/yyyy, dd-mm-yyyy o dd-MMM-yyyy (mes abreviado en texto).
_FECHA = r"([0-3]?\d[/\-][A-Za-z0-9]{1,4}[/\-]\d{2,4})"
RE_FECHA = re.compile(_FECHA)
RE_VIGENCIA = re.compile(
    r"(?:inicio\s+de\s+vigencia|vigencia\s+timbrado|vigencia\s+desde|inicio\s+vigencia)"
    r"\s*:?\s*" + _FECHA,
    re.I,
)
RE_EMISION = re.compile(
    r"(?:fecha\s+de\s+emisi[oó]n|fecha\s+y\s+hora\s+de\s+emisi[oó]n|fecha\s+exp|fecha)"
    r"[^0-9]*" + _FECHA,
    re.I,
)

# --- Montos ------------------------------------------------------------------
# Un número con separadores de miles ('.' o ','). Guaraní = entero.
RE_MONTO = re.compile(r"\d{1,3}(?:[.,]\d{3})+|\d{4,}|\d+")


def _to_entero(token: str) -> int | None:
    """'21,600' / '128.334' / '2.663' -> entero (sin separadores)."""
    digitos = re.sub(r"[^\d]", "", token)
    return int(digitos) if digitos else None


def _primer_monto(texto: str) -> int | None:
    """Primer número 'tipo importe' de una cadena, como entero PYG."""
    m = RE_MONTO.search(texto)
    return _to_entero(m.group()) if m else None


def _valor_tras_etiqueta(
    lineas: list[str], etiqueta: re.Pattern, adelante: int = 4
) -> int | None:
    """Busca una etiqueta y devuelve el primer monto en su línea o las
    siguientes (el OCR separa etiqueta y valor en líneas distintas)."""
    for i, ln in enumerate(lineas):
        m = etiqueta.search(ln)
        if not m:
            continue
        # Mismo renglón, después de la etiqueta.
        v = _primer_monto(ln[m.end():])
        if v is not None:
            return v
        # Renglones siguientes.
        for j in range(i + 1, min(i + 1 + adelante, len(lineas))):
            v = _primer_monto(lineas[j])
            if v is not None:
                return v
    return None


def _primer(patron: re.Pattern, texto: str, grupo: int = 1) -> str | None:
    m = patron.search(texto)
    return m.group(grupo) if m else None


def _nombre_cliente(lineas: list[str]) -> str | None:
    """Nombre tras 'Cliente' / 'Nombre o razón social'."""
    pat = re.compile(r"(?:nombre\s+o\s+raz[oó]n\s+social|cliente)\s*:?\s*(.+)", re.I)
    for ln in lineas:
        m = pat.search(ln)
        if m and m.group(1).strip():
            return m.group(1).replace('"', "").strip()
    return None


def _razon_social_emisor(lineas: list[str], ruc_emisor: str | None) -> str | None:
    """Heurística: línea mayormente alfabética cerca del RUC del emisor.

    Se prueba la línea anterior y posterior al RUC; si no sirven, la primera
    línea 'con cuerpo' del encabezado.
    """
    # Palabras de etiqueta que NO son la razón social.
    bloqueadas = ("factura", "timbrado", "electr", "kude", "vigencia",
                  "emision", "emisión", "condicion", "condición", "telefono",
                  "teléfono", "ruc", "moneda", "comercio")

    def es_nombre(s: str) -> bool:
        s = s.strip()
        bajo = s.lower()
        letras = sum(c.isalpha() for c in s)
        return (
            len(s) >= 5
            and letras >= len(s) * 0.6
            and not RE_RUC.search(s)
            and not any(b in bajo for b in bloqueadas)
        )

    if ruc_emisor:
        for i, ln in enumerate(lineas):
            if ruc_emisor in ln:
                for cand in (lineas[i - 1] if i > 0 else "",
                             lineas[i + 1] if i + 1 < len(lineas) else ""):
                    if es_nombre(cand):
                        return cand.strip()
                break
    for ln in lineas[:6]:
        if es_nombre(ln):
            return ln.strip()
    return None


def parsear(texto: str, lineas: list[str]) -> dict:
    """Mapea el texto OCR a campos de factura paraguaya."""
    bajo = texto.lower()
    rucs = RE_RUC.findall(texto)
    # 1er RUC = emisor (encabezado); el que sigue a "Cliente/RUC" = cliente.
    ruc_emisor = rucs[0] if rucs else None
    ruc_cliente = None
    m_cli = re.search(r"(?:cliente|ruc/documento|documento\s+de\s+identidad)[^\n]*?"
                      r"(\d{5,9}-\d)", texto, re.I)
    if m_cli:
        ruc_cliente = m_cli.group(1)
    elif len(rucs) > 1:
        ruc_cliente = rucs[1]

    # Condición de venta
    condicion = None
    if "contado" in bajo:
        condicion = "Contado"
    elif "credito" in bajo or "crédito" in bajo:
        condicion = "Crédito"

    # Moneda
    moneda = None
    if re.search(r"\b(gs|guaran[ií]|₲)\b", bajo) or "guaraníes" in bajo:
        moneda = "PYG"
    elif re.search(r"\bus\$|d[óo]lares?\s*:?\s*total|moneda\s*:?\s*d[óo]lar", bajo):
        moneda = "USD"
    elif ruc_emisor:
        # Sin marca explícita pero con RUC paraguayo -> PYG por defecto.
        # (Evita falsos USD por la cotización 'DOLARES: 4,51' del pie.)
        moneda = "PYG"

    # Número de factura (normaliza separadores a guiones).
    nro = None
    m_nro = RE_NRO_FACTURA.search(texto)
    if m_nro:
        nro = f"{m_nro.group(1)}-{m_nro.group(2)}-{m_nro.group(3)}"

    # Montos: etiqueta -> valor (mismo renglón o siguientes).
    total = _valor_tras_etiqueta(lineas, re.compile(r"total\s+a\s+pagar", re.I))
    if total is None:
        total = _valor_tras_etiqueta(lineas, re.compile(r"importe\s+total", re.I))
    if total is None:
        total = _valor_tras_etiqueta(lineas, re.compile(r"^\s*total\b", re.I), adelante=2)

    total_iva = _valor_tras_etiqueta(lineas, re.compile(r"total\s+i\.?v\.?a", re.I))

    return {
        "ruc_emisor": ruc_emisor,
        "razon_social_emisor": _razon_social_emisor(lineas, ruc_emisor),
        "timbrado": _primer(RE_TIMBRADO, texto),
        "fecha_inicio_vigencia": _primer(RE_VIGENCIA, texto),
        "numero_factura": nro,
        "condicion_venta": condicion,
        "fecha_emision": _primer(RE_EMISION, texto),
        "ruc_ci_cliente": ruc_cliente,
        "nombre_cliente": _nombre_cliente(lineas),
        "moneda": moneda,
        "total": total,
        "total_iva": total_iva,
    }
