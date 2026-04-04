"""
Parser de PDFs privadas Clinica Indisa.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_RE_NUM_OC = re.compile(r"ORDEN DE COMPRA N[°º\s]+(\d+)", re.IGNORECASE)
_RE_SOLICITUD = re.compile(r"SOLICITUD N[°º\s]+(\d+)", re.IGNORECASE)
_RE_FECHA_OC = re.compile(r"FECHA OC\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
_RE_RUT = re.compile(r"Rut\s*:\s*([\d.]+-[\dkK])", re.IGNORECASE)
_RE_SUCURSAL = re.compile(r"Sucursal\s*:\s*(.+)", re.IGNORECASE)
_RE_ENTREGA = re.compile(r"Lugar Entrega\s*:\s*(.+?)\s{2,}", re.IGNORECASE)
_RE_COND_PAGO = re.compile(r"Condici[oó]n Pago\s*:\s*(.+)", re.IGNORECASE)
_RE_NETO = re.compile(r"^NETO\s+([\d.]+,\d+)", re.MULTILINE | re.IGNORECASE)
_RE_IVA = re.compile(r"^IVA\s+([\d.]+,\d+)", re.MULTILINE | re.IGNORECASE)
_RE_TOTAL = re.compile(r"TOTAL GENERAL\s+([\d.]+,\d+)", re.IGNORECASE)
_RE_TABLE_HEADER = re.compile(r"CODIGO\s+DESCRIPCION DEL PRODUCTO", re.IGNORECASE)
_RE_TABLE_END = re.compile(r"^TOTAL OC\s", re.MULTILINE | re.IGNORECASE)
_RE_LINEA = re.compile(
    r"^(\d{7,9})\s+(.+?)\s+([\d.]+(?:,\d+)?)\s+([\d.]+,\d+)\s+([\d.]+,\d+)$",
    re.MULTILINE,
)


def _parse_clp(value: str) -> float:
    value = (value or "").strip()
    if not value:
        return 0.0
    if "," in value:
        return float(value.replace(".", "").replace(",", "."))
    return float(value.replace(".", ""))


def _fecha_iso(fecha_str: str) -> str:
    try:
        d, m, y = fecha_str.split("/")
        return f"{y}-{m}-{d}"
    except Exception:
        return fecha_str


def parse_pdf(pdf_path: str) -> Tuple[Dict, List[Dict]]:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber no esta instalado. Ejecute: pip install pdfplumber")

    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    with pdfplumber.open(str(path_obj)) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    return _parse_cabecera(full_text), _parse_lineas(full_text)


def quick_extract_rut(pdf_path: str) -> Optional[str]:
    try:
        import pdfplumber
        from app.utils.rut_utils import normalize_rut

        with pdfplumber.open(str(pdf_path)) as pdf:
            text = pdf.pages[0].extract_text() or ""
        m = _RE_RUT.search(text)
        return normalize_rut(m.group(1)) if m else None
    except Exception as e:
        logger.warning(f"quick_extract_rut fallo para {pdf_path}: {e}")
        return None


def _parse_cabecera(text: str) -> Dict:
    def _get(pattern, default=""):
        m = pattern.search(text)
        return m.group(1).strip() if m else default

    ruts = _RE_RUT.findall(text)
    rut_empresa = ruts[0].strip() if ruts else ""
    fecha_raw = _get(_RE_FECHA_OC)
    neto = _parse_clp(_get(_RE_NETO, "0"))
    iva = _parse_clp(_get(_RE_IVA, "0"))
    total = _parse_clp(_get(_RE_TOTAL, "0"))

    empresa = "INSTITUTO DE DIAGNOSTICO S.A."
    for line in text.splitlines():
        clean = line.strip()
        if "INSTITUTO DE DIAGNOSTICO" in clean.upper():
            empresa = clean.split("FECHA", 1)[0].strip()
            break

    return {
        "empresa": empresa,
        "rut_empresa": rut_empresa,
        "sucursal": _get(_RE_SUCURSAL),
        "numero_oc": _get(_RE_NUM_OC),
        "solicitud": _get(_RE_SOLICITUD),
        "fecha_oc": _fecha_iso(fecha_raw) if fecha_raw else "",
        "dir_entrega": _get(_RE_ENTREGA),
        "condicion_pago": _get(_RE_COND_PAGO),
        "neto_afecto": neto,
        "iva": iva,
        "total_bruto": total if total > 0 else neto + iva,
    }


def _parse_lineas(text: str) -> List[Dict]:
    start_m = _RE_TABLE_HEADER.search(text)
    end_m = _RE_TABLE_END.search(text)
    if start_m:
        section = text[start_m.end(): end_m.start() if end_m else len(text)]
    else:
        section = text

    lines = [line.strip() for line in section.splitlines() if line.strip()]
    groups: List[str] = []
    current = ""
    for line in lines:
        if re.match(r"^\d{7,9}\s", line):
            if current:
                groups.append(current)
            current = line
        elif current:
            current += " " + line
    if current:
        groups.append(current)

    result: List[Dict] = []
    for raw in groups:
        item = _parse_linea_robusta(raw)
        if item:
            result.append(item)

    if not result:
        logger.warning("No se encontraron lineas de producto en el PDF INDISA")
    return result


def _parse_linea_robusta(raw: str) -> Optional[Dict]:
    m = _RE_LINEA.search(raw)
    if m:
        return {
            "codigo": m.group(1).strip(),
            "descripcion": m.group(2).strip(),
            "cantidad": _parse_clp(m.group(3)),
            "unidad": "UN",
            "precio_unit": _parse_clp(m.group(4)),
            "valor_total": _parse_clp(m.group(5)),
        }

    tokens = raw.split()
    if len(tokens) < 4:
        return None

    codigo = tokens[0].strip()
    money_idx = [i for i, token in enumerate(tokens) if re.match(r"^\d{1,3}(?:\.\d{3})*,\d+$|^\d+,\d+$", token)]
    if len(money_idx) < 2:
        logger.debug(f"Linea INDISA no parseada: {raw}")
        return None

    price_idx = money_idx[-2]
    total_idx = money_idx[-1]
    precio_unit = _parse_clp(tokens[price_idx])
    valor_total = _parse_clp(tokens[total_idx])
    left = tokens[1:price_idx]

    cantidad = 0.0
    qty_idx = None
    for i in range(len(left) - 1, -1, -1):
        cleaned = re.sub(r"[^0-9.,]", "", left[i])
        if not cleaned:
            continue
        try:
            qty = _parse_clp(cleaned)
        except Exception:
            continue
        if qty <= 0:
            continue
        if abs((qty * precio_unit) - valor_total) <= max(2.0, valor_total * 0.02):
            cantidad = qty
            qty_idx = i
            break

    if cantidad <= 0 and precio_unit > 0:
        cantidad = round(valor_total / precio_unit, 3)

    descripcion_tokens = left[:qty_idx] if qty_idx is not None else left
    descripcion = " ".join(descripcion_tokens).strip()

    return {
        "codigo": codigo,
        "descripcion": descripcion or codigo,
        "cantidad": cantidad if cantidad > 0 else 1.0,
        "unidad": "UN",
        "precio_unit": precio_unit,
        "valor_total": valor_total,
    }
