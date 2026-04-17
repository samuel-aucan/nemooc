"""
Scraping liviano del portal publico de Mercado Publico para completar
metadatos que la API no expone en detalle, como direcciones visibles.
"""

from __future__ import annotations

from dataclasses import dataclass
import html
import io
import logging
import re

import pdfplumber
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PORTAL_DETAIL_URL = (
    "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/"
    "DetailsPurchaseOrder.aspx?codigoOC={codigo_oc}"
)
TIMEOUT = 20
PDF_QS_PATTERN = re.compile(r"PDFReport\.aspx\?qs=([^&]+?)&#39;", re.IGNORECASE)
PDF_REPORT_URL = (
    "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/"
    "PDFReport.aspx?qs={qs}"
)


@dataclass
class PublicOcPortalMeta:
    direccion_despacho: str = ""
    direccion_facturacion: str = ""


def get_public_oc_portal_meta(codigo_oc: str) -> PublicOcPortalMeta:
    try:
        response = requests.get(PORTAL_DETAIL_URL.format(codigo_oc=codigo_oc), timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("No se pudo leer portal publico para %s: %s", codigo_oc, exc)
        return PublicOcPortalMeta()

    soup = BeautifulSoup(response.text, "html.parser")
    pdf_meta = _extract_pdf_meta(response.text)

    direccion_despacho_portal = (
        _text_by_id(soup, "lblDirectionBuyerValue")
        or _text_by_id(soup, "lblDirectionDeliveryValue")
        or _text_by_id(soup, "lblDirectionValuePF")
        or ""
    )
    direccion_facturacion_portal = (
        _text_by_id(soup, "lblDirectionValuePF")
        or _text_by_id(soup, "lblDirectionInvoiseValue")
        or ""
    )

    direccion_despacho = (
        pdf_meta.direccion_despacho
        or _clean_address_value(direccion_despacho_portal)
        or ""
    )
    direccion_facturacion = (
        pdf_meta.direccion_facturacion
        or _clean_address_value(direccion_facturacion_portal)
        or ""
    )

    return PublicOcPortalMeta(
        direccion_despacho=direccion_despacho,
        direccion_facturacion=direccion_facturacion,
    )


def _text_by_id(soup: BeautifulSoup, element_id: str) -> str:
    node = soup.find(id=element_id)
    if not node:
        return ""
    return node.get_text(" ", strip=True)


def _extract_pdf_meta(html_text: str) -> PublicOcPortalMeta:
    qs_match = PDF_QS_PATTERN.search(html_text)
    if not qs_match:
        return PublicOcPortalMeta()

    qs = html.unescape(qs_match.group(1))
    try:
        response = requests.get(PDF_REPORT_URL.format(qs=qs), timeout=TIMEOUT)
        response.raise_for_status()
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception as exc:
        logger.warning("No se pudo leer PDF publico de %s: %s", qs, exc)
        return PublicOcPortalMeta()

    normalized = _normalize_pdf_text(text)
    return PublicOcPortalMeta(
        direccion_despacho=_extract_labeled_line(
            normalized,
            "DIRECCIONES DE DESPACHO",
            "DIRECCION DE DESPACHO",
            "DIRECCIÓN DE DESPACHO",
            "DIRECCIÓNES DE DESPACHO",
        ),
        direccion_facturacion=_extract_labeled_line(
            normalized,
            "DIRECCION DE ENVIO FACTURA",
            "DIRECCIÓN DE ENVÍO FACTURA",
            "DIRECCION DE FACTURACION",
            "DIRECCIÓN DE FACTURACIÓN",
        ),
    )


def _normalize_pdf_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split()).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _extract_labeled_line(text: str, *labels: str) -> str:
    for label in labels:
        pattern = re.compile(rf"^{re.escape(label)}\s*:?\s*(.+)$", re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        if match:
            return _clean_address_value(match.group(1))
    return ""


def _clean_address_value(value: str) -> str:
    cleaned = " ".join((value or "").replace("•", " ").split()).strip(" -:")
    if not cleaned:
        return ""

    lowered = cleaned.lower()
    generic_markers = (
        "sin dirección registrada para unidad de compra",
        "sin direccion registrada para unidad de compra",
        "bienes y servicios",
    )
    if lowered in generic_markers:
        return ""
    return cleaned
