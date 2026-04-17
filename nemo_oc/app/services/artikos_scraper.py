"""
Scraper para OCs del portal Artikos Chile.
Dada la URL del email de notificación, hace GET+POST con el RUT del proveedor
y parsea el HTML resultante para construir OrdenCompra + List[LineaOC].
"""
import logging
import re
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

from app.models.linea_oc import LineaOC
from app.models.orden_compra import OrdenCompra
from app.utils.rut_utils import rut_to_cliente_sap

logger = logging.getLogger(__name__)


def scrape_oc(url: str, rut_proveedor: str = "") -> Tuple[OrdenCompra, List[LineaOC]]:
    """
    Dado el link del email Artikos, devuelve (OrdenCompra, líneas) listos para
    guardar con oc_repository.save_oc().
    Lanza ValueError si el link expiró o el RUT es incorrecto.
    """
    from app.config import load_config
    rut = rut_proveedor or load_config().rut_proveedor or "76215260-6"
    # El portal Artikos no acepta RUT con puntos — normalizar
    rut = rut.replace(".", "")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "es-CL,es;q=0.9",
    })

    # 1. GET — obtiene cookies y los campos ocultos del formulario
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    resp.encoding = "iso-8859-1"

    # Extraer Key y Key2 desde los inputs hidden del formulario
    soup_form = BeautifulSoup(resp.text, "html.parser")
    hidden = {
        inp.get("name"): inp.get("value", "")
        for inp in soup_form.find_all("input", {"type": "hidden"})
        if inp.get("name")
    }

    # 2. POST — el JS copia el RUT al campo Clave y envía Key+Key2+Clave
    post_data = {**hidden, "Clave": rut}
    resp2 = session.post(url, data=post_data, timeout=20)
    resp2.raise_for_status()
    # Decodificar desde bytes con iso-8859-1 explícito (más fiable que .text)
    html = resp2.content.decode("iso-8859-1")

    # Verificar en el texto visible (no en el JS/HTML crudo) para evitar falsos positivos
    soup_check = BeautifulSoup(html, "html.parser")
    visible_text = soup_check.get_text(" ", strip=True)
    if "ORDEN DE COMPRA" not in visible_text.upper():
        raise ValueError(
            "No se pudo acceder a la OC. Posibles causas: link expirado, "
            "RUT de proveedor incorrecto, o la OC no está disponible."
        )

    logger.info(f"Artikos: respuesta recibida ({len(html)} chars), parseando OC...")
    return _parse_oc_html(html)


# ── Parser principal ─────────────────────────────────────────────────────────

def _parse_oc_html(html: str) -> Tuple[OrdenCompra, List[LineaOC]]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    # ── Número de OC ──────────────────────────────────────────────────────────
    # Intentar varias variantes: "N°660073", "Nro 660073", número en celda aparte
    m_num = re.search(r'ORDEN DE COMPRA[^0-9]{0,40}(\d{5,})', text, re.IGNORECASE)
    if not m_num:
        # Fallback 1: <title>Folio Artikos XXXXXX</title>
        title_tag = soup.find("title")
        if title_tag:
            m_num = re.search(r'(\d{5,})', title_tag.get_text())
    if not m_num:
        # Fallback 2: buscar en el HTML crudo (por si BS4 altera el texto)
        m_num = re.search(r'ORDEN DE COMPRA[^0-9]{0,40}(\d{5,})', html, re.IGNORECASE)
    if not m_num:
        logger.error("Texto extraído (primeros 600 chars): %s", text[:600])
        raise ValueError("No se encontró el número de OC en la respuesta")
    codigo_oc = m_num.group(1).strip()

    # ── Fecha ─────────────────────────────────────────────────────────────────
    m_fecha = re.search(r'Fecha\s*:\s*(\d{2}/\d{2}/\d{4})', text)
    fecha_str = ""
    if m_fecha:
        d, mo, y = m_fecha.group(1).split("/")
        fecha_str = f"{y}-{mo}-{d}"

    # ── RUT del comprador (header del documento, ej: "Rut : 96530470-3") ──────
    # Artikos usa \xa0 (nbsp) alrededor del ":", así que aceptar cualquier espacio/nbsp
    m_rut = re.search(r'Rut[\s\xa0]*:[\s\xa0]*([\d\.]+[-][\dkKxX])', text)
    rut_comprador = ""
    if m_rut:
        rut_comprador = m_rut.group(1).replace(".", "").strip()

    # ── Nombre del organismo ──────────────────────────────────────────────────
    nombre_org = ""
    if m_rut:
        antes = text[:m_rut.start()].strip()
        # Eliminar prefijo "Folio Artikos NNNNN" que aparece del <title>
        antes = re.sub(r'Folio\s+Artikos\s+\d+\s*', '', antes, flags=re.IGNORECASE).strip()
        palabras = [p for p in antes.split() if len(p) >= 2]
        nombre_org = " ".join(palabras[:12]) if palabras else ""

    # ── Totales ───────────────────────────────────────────────────────────────
    total_neto   = _extraer_monto(text, ["NETO"])
    total_gen    = _extraer_monto(text, ["TOTAL GENERAL"])
    iva          = _extraer_monto(text, ["IVA"])

    # ── Líneas ────────────────────────────────────────────────────────────────
    lineas = _parse_lineas(soup, codigo_oc)
    if not lineas:
        raise ValueError("No se encontraron líneas de productos en la OC")

    # Calcular totales desde líneas si no se extrajeron del HTML
    if not total_neto:
        total_neto = sum(
            (l.precio_neto or 0) * (l.cantidad or 0) for l in lineas
        )
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


# ── Parser de líneas ──────────────────────────────────────────────────────────

_HEADER_KEYWORDS = {"CODIGO", "DESCRIPCION", "CANTIDAD", "UNITARIO", "TOTAL"}


def _parse_lineas(soup: BeautifulSoup, codigo_oc: str) -> List[LineaOC]:
    """Busca la tabla de productos y construye una LineaOC por fila válida."""
    lineas: List[LineaOC] = []

    items_table = None
    for table in soup.find_all("table"):
        filas = table.find_all("tr")
        if not filas:
            continue
        header_cells = filas[0].find_all(["th", "td"])
        # Necesitamos al menos 4 columnas separadas con encabezados cortos
        if len(header_cells) < 4:
            continue
        cabecera = [c.get_text(strip=True).upper() for c in header_cells]
        # Descartar tablas donde las celdas son enormes (contienen todo el documento)
        if any(len(col) > 80 for col in cabecera):
            continue
        coincidencias = sum(
            1 for kw in _HEADER_KEYWORDS if any(kw in col for col in cabecera)
        )
        if coincidencias >= 3:
            items_table = table
            break

    if not items_table:
        return lineas

    filas = items_table.find_all("tr")
    cabecera = [c.get_text(strip=True).upper() for c in filas[0].find_all(["th", "td"])]

    def idx(*names: str) -> int:
        for name in names:
            for i, col in enumerate(cabecera):
                if name in col:
                    return i
        return -1

    i_cod   = idx("CODIGO")
    i_desc  = idx("DESCRIPCION")
    i_cant  = idx("CANTIDAD")
    i_prec  = idx("UNITARIO", "P.UNIT")
    i_total = idx("TOTAL")

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
        # Saltear filas de resumen (totales)
        desc_upper = descripcion.upper()
        if any(x in desc_upper for x in ("TOTAL", "NETO", "IVA", "DESCUENTO", "COSTO ADICIONAL")):
            continue

        codigo     = celda(i_cod) or None
        cantidad   = _num(celda(i_cant))
        precio_net = _num(celda(i_prec))
        total_line = _num(celda(i_total))

        if not precio_net and cantidad and total_line:
            precio_net = round(total_line / cantidad, 4)

        lineas.append(LineaOC(
            codigo_oc=codigo_oc,
            correlativo=correlativo,
            codigo_mp=codigo,
            producto=descripcion,
            especificacion_comprador=descripcion,
            cantidad=cantidad or 0.0,
            precio_neto=precio_net or 0.0,
            total=total_line or 0.0,
        ))

    return lineas


# ── Helpers numéricos ─────────────────────────────────────────────────────────

def _extraer_monto(text: str, etiquetas: List[str]) -> float:
    """Busca la primera etiqueta y extrae el número CLP que la sigue."""
    for etiq in etiquetas:
        m = re.search(etiq + r'[\s:$]*([\d\.]+(?:,\d+)?)', text, re.IGNORECASE)
        if m:
            val = _num(m.group(1))
            if val > 0:
                return val
    return 0.0


def _num(s: str) -> float:
    """Convierte '320.000' o '320.000,50' (formato CLP) a float."""
    if not s:
        return 0.0
    try:
        s = s.replace("$", "").replace(" ", "").strip()
        if "," in s:
            entero, decimal = s.rsplit(",", 1)
            return float(entero.replace(".", "") + "." + decimal[:2])
        else:
            return float(s.replace(".", ""))
    except Exception:
        return 0.0
