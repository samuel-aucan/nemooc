"""
Scraper para OCs del portal Artikos Chile.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime
from typing import Any, List, Tuple

import requests
from bs4 import BeautifulSoup

from app.models.linea_oc import LineaOC
from app.models.orden_compra import OrdenCompra
from app.utils.rut_utils import rut_to_cliente_sap

logger = logging.getLogger(__name__)


def scrape_oc(url: str, rut_proveedor: str = "") -> Tuple[OrdenCompra, List[LineaOC]]:
    oc, lineas, _ = scrape_oc_with_metadata(url, rut_proveedor=rut_proveedor)
    return oc, lineas


def scrape_oc_with_metadata(
    url: str,
    rut_proveedor: str = "",
    codigo_empresa: str = "",
) -> Tuple[OrdenCompra, List[LineaOC], dict[str, Any]]:
    """
    Dado el link del email Artikos, devuelve la OC, sus lineas y metadata
    del acceso usado para poder persistir trazabilidad del documento.
    """
    from app.config import load_config

    cfg = load_config()
    rut = rut_proveedor or cfg.rut_proveedor or "76215260-6"
    empresa = codigo_empresa or cfg.codigo_empresa or ""
    candidatos = _build_clave_candidates(rut, empresa)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "es-CL,es;q=0.9",
        }
    )

    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    resp.encoding = "iso-8859-1"

    soup_form = BeautifulSoup(resp.text, "html.parser")
    hidden = {
        inp.get("name"): inp.get("value", "")
        for inp in soup_form.find_all("input", {"type": "hidden"})
        if inp.get("name")
    }

    intentos: list[dict[str, Any]] = []
    html_ok = ""
    credencial_ok: dict[str, str] | None = None

    for candidato in candidatos:
        post_data = {**hidden, "Clave": candidato["value"]}
        resp2 = session.post(url, data=post_data, timeout=20)
        resp2.raise_for_status()
        html = resp2.content.decode("iso-8859-1")

        soup_check = BeautifulSoup(html, "html.parser")
        visible_text = soup_check.get_text(" ", strip=True)
        ok = "ORDEN DE COMPRA" in visible_text.upper()

        intentos.append(
            {
                "kind": candidato["kind"],
                "preview": candidato["preview"],
                "ok": ok,
            }
        )
        if ok:
            html_ok = html
            credencial_ok = candidato
            break

    if not html_ok or not credencial_ok:
        intentos_txt = ", ".join(
            f"{item['kind']}={item['preview']}" for item in intentos
        ) or "sin credenciales candidatas"
        raise ValueError(
            "No se pudo acceder a la OC. Posibles causas: link expirado, "
            f"credencial incorrecta o portal no disponible. Intentos: {intentos_txt}"
        )

    logger.info("Artikos: respuesta recibida (%s chars), parseando OC...", len(html_ok))
    oc, lineas = _parse_oc_html(html_ok)
    metadata = {
        "source_type": "artikos",
        "source_url": url,
        "verified_at": datetime.now().isoformat(),
        "hidden_fields": sorted(hidden.keys()),
        "credential_kind": credencial_ok["kind"],
        "credential_preview": credencial_ok["preview"],
        "credential_attempts": intentos,
        "print_available": "window.print()" in html_ok,
        "html": html_ok,
    }
    return oc, lineas, metadata


def _parse_oc_html(html: str) -> Tuple[OrdenCompra, List[LineaOC]]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    m_num = re.search(r"ORDEN DE COMPRA[^0-9]{0,40}(\d{5,})", text, re.IGNORECASE)
    if not m_num:
        title_tag = soup.find("title")
        if title_tag:
            m_num = re.search(r"(\d{5,})", title_tag.get_text())
    if not m_num:
        m_num = re.search(r"ORDEN DE COMPRA[^0-9]{0,40}(\d{5,})", html, re.IGNORECASE)
    if not m_num:
        logger.error("Texto extraido (primeros 600 chars): %s", text[:600])
        raise ValueError("No se encontro el numero de OC en la respuesta")
    codigo_oc = m_num.group(1).strip()

    m_fecha = re.search(r"Fecha\s*:\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    fecha_str = ""
    if m_fecha:
        d, mo, y = m_fecha.group(1).split("/")
        fecha_str = f"{y}-{mo}-{d}"

    nombre_org, rut_comprador = _extract_buyer_identity(soup)
    if nombre_org:
        nombre_org = re.sub(
            r"ORDEN\s+DE\s+COMPRA\s+N\S*\s*/?\d+\s*",
            "",
            nombre_org,
            flags=re.IGNORECASE,
        ).strip()

    if not rut_comprador:
        m_rut = re.search(r"Rut[\s\xa0]*:[\s\xa0]*([\d\.]+[-][\dkKxX])", text)
        if m_rut:
            rut_comprador = m_rut.group(1).replace(".", "").strip()
        else:
            m_rut = None
    else:
        m_rut = re.search(re.escape(rut_comprador), text)

    if not nombre_org and m_rut:
        antes = text[: m_rut.start()].strip()
        antes = re.sub(r"Folio\s+Artikos\s+\d+\s*", "", antes, flags=re.IGNORECASE).strip()
        antes = re.sub(r"ORDEN\s+DE\s+COMPRA[^A-Z0-9]{0,8}/?\d+\s*", "", antes, flags=re.IGNORECASE).strip()
        palabras = [p for p in antes.split() if len(p) >= 2]
        nombre_org = " ".join(palabras[:12]) if palabras else ""

    total_neto = _extraer_monto(text, ["NETO"])
    total_gen = _extraer_monto(text, ["TOTAL GENERAL"])
    iva = _extraer_monto(text, ["IVA"])

    lineas = _parse_lineas(soup, codigo_oc)
    if not lineas:
        raise ValueError("No se encontraron lineas de productos en la OC")

    if not total_neto:
        total_neto = sum((l.precio_neto or 0) * (l.cantidad or 0) for l in lineas)
    if not total_gen:
        total_gen = total_neto * 1.19
    if not iva:
        iva = total_gen - total_neto

    oc = OrdenCompra(
        codigo_oc=codigo_oc,
        nombre_oc=f"OC Artikos {codigo_oc}",
        codigo_estado_mp=0,
        estado_mp="Enviada",
        codigo_tipo="PV",
        tipo_oc="PRIVADA",
        fecha_creacion=fecha_str,
        fecha_envio=fecha_str,
        total_neto=round(total_neto, 2),
        total=round(total_gen, 2),
        impuestos=round(iva, 2),
        porcentaje_iva=19.0,
        moneda="CLP",
        nombre_organismo=nombre_org,
        rut_unidad=rut_comprador,
        nombre_proveedor="NEMO CHILE S.A.",
        cliente_sap_sugerido=rut_to_cliente_sap(rut_comprador),
        cantidad_lineas=len(lineas),
    )
    return oc, lineas


def _extract_buyer_identity(soup: BeautifulSoup) -> Tuple[str, str]:
    for table in soup.find_all("table")[:6]:
        first_cell = table.find("td")
        if first_cell is None:
            continue
        raw_text = " ".join(first_cell.stripped_strings)
        if not raw_text:
            continue
        rut_match = re.search(r"([\d\.]+[-][\dkKxX])", raw_text)
        if not rut_match:
            continue
        nombre = raw_text[:rut_match.start()].strip(" -:/")
        nombre = re.sub(r"\bRUT\s*:?\s*$", "", nombre, flags=re.IGNORECASE).strip(" -:/")
        nombre = re.sub(r"\s+", " ", nombre)
        if nombre:
            return nombre, rut_match.group(1).replace(".", "").strip()
    return "", ""


_HEADER_KEYWORDS = {"CODIGO", "DESCRIPCION", "ARTICULO", "CANTIDAD", "UNITARIO", "TOTAL"}


def _normalize_header_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_only).strip().upper()


def _parse_lineas(soup: BeautifulSoup, codigo_oc: str) -> List[LineaOC]:
    lineas: List[LineaOC] = []

    items_table = None
    for table in soup.find_all("table"):
        filas = table.find_all("tr")
        if not filas:
            continue
        header_cells = filas[0].find_all(["th", "td"])
        if len(header_cells) < 4:
            continue
        cabecera = [_normalize_header_text(c.get_text(" ", strip=True)) for c in header_cells]
        if any(len(col) > 80 for col in cabecera):
            continue
        coincidencias = sum(1 for kw in _HEADER_KEYWORDS if any(kw in col for col in cabecera))
        if coincidencias >= 3:
            items_table = table
            break

    if not items_table:
        return lineas

    filas = items_table.find_all("tr")
    cabecera = [_normalize_header_text(c.get_text(" ", strip=True)) for c in filas[0].find_all(["th", "td"])]

    def idx(*names: str) -> int:
        for name in names:
            normalized_name = _normalize_header_text(name)
            for i, col in enumerate(cabecera):
                if normalized_name in col:
                    return i
        return -1

    i_cod = idx("CODIGO")
    i_desc = idx("DESCRIPCION", "ARTICULO")
    i_cant = idx("CANTIDAD")
    i_prec = idx("UNITARIO", "P.UNIT", "VALOR UNITARIO")
    i_total = idx("TOTAL", "VALOR TOTAL")

    for correlativo, fila in enumerate(filas[1:], start=1):
        celdas = fila.find_all("td")
        if len(celdas) < 3:
            continue

        def celda(i: int) -> str:
            if i < 0 or i >= len(celdas):
                return ""
            return celdas[i].get_text(strip=True)

        descripcion = celda(i_desc)
        if not descripcion:
            continue

        desc_upper = descripcion.upper()
        if any(x in desc_upper for x in ("TOTAL", "NETO", "IVA", "DESCUENTO", "COSTO ADICIONAL")):
            continue

        codigo = celda(i_cod) or None
        cantidad = _num(celda(i_cant))
        precio_net = _num(celda(i_prec))
        total_line = _num(celda(i_total))

        if not precio_net and cantidad and total_line:
            precio_net = round(total_line / cantidad, 4)

        lineas.append(
            LineaOC(
                codigo_oc=codigo_oc,
                correlativo=correlativo,
                codigo_mp=codigo,
                producto=descripcion,
                especificacion_comprador=descripcion,
                cantidad=cantidad or 0.0,
                precio_neto=precio_net or 0.0,
                total=total_line or 0.0,
            )
        )

    return lineas


def _build_clave_candidates(rut_proveedor: str, codigo_empresa: str) -> List[dict[str, str]]:
    candidatos: List[dict[str, str]] = []
    seen: set[str] = set()

    def add(value: str, kind: str) -> None:
        normalized = (value or "").strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        candidatos.append(
            {
                "value": normalized,
                "kind": kind,
                "preview": _mask_value(normalized),
            }
        )

    rut_raw = (rut_proveedor or "").strip().replace(".", "")
    rut_digits = re.sub(r"\D+", "", rut_raw)

    add(rut_raw, "rut")
    if rut_digits:
        add(f"{rut_digits[:-1]}-{rut_digits[-1]}", "rut_normalizado")
        add(rut_digits, "rut_sin_guion")

    empresa_raw = (codigo_empresa or "").strip()
    empresa_digits = re.sub(r"\D+", "", empresa_raw)
    add(empresa_raw, "codigo_empresa")
    if empresa_digits and empresa_digits != empresa_raw:
        add(empresa_digits, "codigo_empresa_digitos")

    return candidatos


def _mask_value(value: str) -> str:
    value = (value or "").strip()
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * max(1, len(value) - 4)}{value[-2:]}"


def _extraer_monto(text: str, etiquetas: List[str]) -> float:
    for etiq in etiquetas:
        m = re.search(etiq + r"[\s:$]*([\d\.]+(?:,\d+)?)", text, re.IGNORECASE)
        if m:
            val = _num(m.group(1))
            if val > 0:
                return val
    return 0.0


def _num(s: str) -> float:
    if not s:
        return 0.0
    try:
        s = s.replace("$", "").replace(" ", "").strip()
        if "," in s:
            entero, decimal = s.rsplit(",", 1)
            return float(entero.replace(".", "") + "." + decimal[:2])
        return float(s.replace(".", ""))
    except Exception:
        return 0.0
