"""
Parser de PDFs privadas estilo Banmedica / Clinica Santa Maria.
Formato similar a INDISA, con OCR variable en cantidad/unidad.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

_COMPANY_MARKERS = [
    ("CLINICA CIUDAD DEL MAR", "CLINICA CIUDAD DEL MAR S.A."),
    ("CLINICA SANTA MARIA", "CLINICA SANTA MARIA SPA"),
    ("CLINICA BIO BIO", "CLINICA BIO BIO SPA"),
    ("CLINICA BIOBIO", "CLINICA BIO BIO SPA"),
    ("CLINICA DAVILA", "CLINICA DAVILA Y SERVICIOS MEDICOS SPA"),
    ("CLINICA VESPUCIO", "CLINICA VESPUCIO SPA"),
]

_RE_NUM_OC = re.compile(r"ORDEN DE COMPRA N[°º\s]+(\d+)", re.IGNORECASE)
_RE_FECHA_LINEA = re.compile(r"FECHA\s*:\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
_RE_FECHA_OC = re.compile(r"FECHA OC\s*:?\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
_RE_RUT = re.compile(r"Rut\s*:\s*([\d.]+-[\dkK])", re.IGNORECASE)
_RE_SUCURSAL = re.compile(r"Sucursal\s*:\s*(.+)", re.IGNORECASE)
_RE_ENTREGA = re.compile(r"Lugar Entrega\s*:\s*(.+?)\s{2,}", re.IGNORECASE)
_RE_COND_PAGO = re.compile(r"Condici[oó]n Pago\s*:\s*(.+)", re.IGNORECASE)
_RE_TOTAL_OC = re.compile(r"TOTAL OC\s+([\d.]+,\d+)", re.IGNORECASE)
_RE_NETO = re.compile(r"^NETO\s+([\d.]+,\d+)", re.MULTILINE | re.IGNORECASE)
_RE_IVA = re.compile(r"^IVA\s+([\d.]+,\d+)", re.MULTILINE | re.IGNORECASE)
_RE_TABLE_HEADER = re.compile(r"CODIGO\s+DESCRIPCION DEL PRODUCTO", re.IGNORECASE)
_RE_TABLE_END = re.compile(r"^TOTAL OC\s", re.MULTILINE | re.IGNORECASE)
_RE_CODE_START = re.compile(r"^\d{7,9}\s")
_RE_MONEY = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d+$|^\d+,\d+$")


def _parse_cl_num(value: str) -> float:
    value = (value or "").strip()
    if not value:
        return 0.0
    if "," in value:
        return float(value.replace(".", "").replace(",", "."))
    return float(value.replace(".", ""))


def _fecha_iso(value: str) -> str:
    try:
        d, m, y = value.split("/")
        return f"{y}-{m}-{d}"
    except Exception:
        return value


def parse_pdf(pdf_path: str) -> Tuple[Dict, List[Dict]]:
    import pdfplumber

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    with pdfplumber.open(str(path)) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    return _parse_cabecera(full_text), _parse_lineas(full_text)


def _parse_cabecera(text: str) -> Dict:
    def _get(pattern, default=""):
        m = pattern.search(text)
        return m.group(1).strip() if m else default

    ruts = _RE_RUT.findall(text)
    rut_empresa = ruts[0].strip() if ruts else ""
    fecha_raw = _get(_RE_FECHA_OC) or _get(_RE_FECHA_LINEA)
    neto = _parse_cl_num(_get(_RE_NETO, "0"))
    iva = _parse_cl_num(_get(_RE_IVA, "0"))
    total_oc = _parse_cl_num(_get(_RE_TOTAL_OC, "0"))

    empresa = ""
    for line in text.splitlines():
        clean = line.strip()
        clean_upper = clean.upper()
        if not clean or "NEMO CHILE" in clean_upper:
            continue
        for marker, resolved in _COMPANY_MARKERS:
            if marker in clean_upper:
                empresa = resolved
                break
        if empresa:
            break
        if "BANMEDICA" in clean_upper:
            empresa = clean
            break

    return {
        "empresa": empresa or "",
        "rut_empresa": rut_empresa,
        "sucursal": _get(_RE_SUCURSAL),
        "numero_oc": _get(_RE_NUM_OC),
        "fecha_oc": _fecha_iso(fecha_raw) if fecha_raw else "",
        "dir_entrega": _get(_RE_ENTREGA),
        "condicion_pago": _get(_RE_COND_PAGO),
        "neto_afecto": neto if neto > 0 else total_oc,
        "iva": iva,
        "total_bruto": total_oc if total_oc > 0 else neto + iva,
    }


def _parse_lineas(text: str) -> List[Dict]:
    start = _RE_TABLE_HEADER.search(text)
    end = _RE_TABLE_END.search(text)
    section = text[start.end():end.start()] if start and end else text
    lines = [line.strip() for line in section.splitlines() if line.strip()]

    groups: list[str] = []
    current = ""
    for line in lines:
        if _RE_CODE_START.match(line):
            if current:
                groups.append(current)
            current = line
        elif current:
            current += " " + line
    if current:
        groups.append(current)

    parsed: list[Dict] = []
    for idx, raw in enumerate(groups, start=1):
        item = _parse_line(raw, idx)
        if item:
            parsed.append(item)
    return parsed


def _parse_line(raw: str, idx: int) -> Dict | None:
    tokens = raw.split()
    if len(tokens) < 4:
        return None

    codigo = tokens[0]
    money_idx = [i for i, token in enumerate(tokens) if _RE_MONEY.match(token)]
    if len(money_idx) < 2:
        logger.debug(f"No se pudo detectar precio/total en linea Banmedica: {raw}")
        return None

    price_idx = money_idx[-2]
    total_idx = money_idx[-1]
    precio_unit = _parse_cl_num(tokens[price_idx])
    valor_total = _parse_cl_num(tokens[total_idx])
    left = tokens[1:price_idx]

    qty, qty_idx = _find_quantity_candidate(left, precio_unit, valor_total)
    if qty <= 0 and precio_unit > 0:
        qty = round(valor_total / precio_unit, 3)

    desc_tokens = left[:qty_idx] if qty_idx is not None else left
    descripcion = " ".join(desc_tokens).strip()

    return {
        "pos": idx,
        "codigo": codigo,
        "descripcion": descripcion or codigo,
        "cantidad": qty if qty > 0 else 1.0,
        "unidad": "UN",
        "precio_unit": precio_unit,
        "valor_total": valor_total,
    }


def _find_quantity_candidate(tokens: List[str], precio_unit: float, valor_total: float) -> Tuple[float, int | None]:
    if not tokens or precio_unit <= 0 or valor_total <= 0:
        return 0.0, None

    for i in range(len(tokens) - 1, -1, -1):
        cleaned = re.sub(r"[^0-9.,]", "", tokens[i])
        if not cleaned:
            continue
        try:
            qty = _parse_cl_num(cleaned)
        except Exception:
            continue
        if qty <= 0:
            continue
        if abs((qty * precio_unit) - valor_total) <= max(2.0, valor_total * 0.02):
            return qty, i
    return 0.0, None
