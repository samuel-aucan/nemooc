"""
Parser de PDFs privadas ACHS.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

_RE_OC = re.compile(r"N[°º]\s*O\.?C\.?:\s*(\d+)", re.IGNORECASE)
_RE_RUT = re.compile(r"R\.?U\.?T\.?:\s*([\d.]+-[\dkK])", re.IGNORECASE)
_RE_FECHA_OC = re.compile(r"Fecha O\.C\.\s*:\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
_RE_DIR = re.compile(r"Direcci[oó]n Sede:\s*(.+)", re.IGNORECASE)
_RE_SEDE = re.compile(r"Sede Solicitante:\s*(.+?)(?:\s{2,}|$)", re.IGNORECASE)
_RE_TOTAL = re.compile(r"Total Bruto\s+([\d.]+(?:,\d+)?)", re.IGNORECASE)
_RE_NETO = re.compile(r"T\.\s*Afecto\s+([\d.]+(?:,\d+)?)", re.IGNORECASE)
_RE_IVA = re.compile(r"IVA\s+([\d.]+(?:,\d+)?)", re.IGNORECASE)
_RE_HEADER = re.compile(r"Pos\.\s+Cant\.\s+Un\.", re.IGNORECASE)
_RE_END = re.compile(r"^Subtotal\s", re.MULTILINE | re.IGNORECASE)
_RE_LINE_START = re.compile(r"^\d+\s+[\d.]+(?:,\d+)?\s+\S+")


def _parse_num(value: str) -> float:
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

    return {
        "empresa": "ASOCIACION CHILENA DE SEGURIDAD",
        "rut_empresa": _get(_RE_RUT),
        "numero_oc": _get(_RE_OC),
        "fecha_oc": _fecha_iso(_get(_RE_FECHA_OC)),
        "dir_entrega": _get(_RE_DIR),
        "nombre_unidad": _get(_RE_SEDE),
        "neto_afecto": _parse_num(_get(_RE_NETO, "0")),
        "iva": _parse_num(_get(_RE_IVA, "0")),
        "total_bruto": _parse_num(_get(_RE_TOTAL, "0")),
    }


def _parse_lineas(text: str) -> List[Dict]:
    start = _RE_HEADER.search(text)
    end = _RE_END.search(text)
    section = text[start.end():end.start()] if start and end else text
    lines = [line.strip() for line in section.splitlines() if line.strip()]

    groups: list[str] = []
    current = ""
    for line in lines:
        if _RE_LINE_START.match(line):
            if current:
                groups.append(current)
            current = line
        elif current:
            current += " " + line
    if current:
        groups.append(current)

    result: list[Dict] = []
    for raw in groups:
        item = _parse_line(raw)
        if item:
            result.append(item)
    return result


def _parse_line(raw: str) -> Dict | None:
    match = re.match(
        r"^(\d+)\s+([\d.]+(?:,\d+)?)\s+(\S+)\s+(\S+)\s+(.+?)\s+([\d.]+(?:,\d+)?)\s+[\d.]+(?:,\d+)?\s*%\s+([\d.]+(?:,\d+)?)(?:\s+(.+))?$",
        raw,
    )
    if not match:
        logger.debug(f"No se pudo parsear linea ACHS: {raw}")
        return None

    pos = int(match.group(1))
    cantidad = _parse_num(match.group(2))
    unidad = match.group(3)
    codigo = match.group(4)
    descripcion = " ".join(
        part.strip()
        for part in (match.group(5), match.group(8) or "")
        if part and part.strip()
    )
    precio_unit = _parse_num(match.group(6))
    valor_total = _parse_num(match.group(7))

    return {
        "pos": pos,
        "codigo": codigo,
        "descripcion": descripcion,
        "cantidad": cantidad,
        "unidad": unidad,
        "precio_unit": precio_unit,
        "valor_total": valor_total,
    }
