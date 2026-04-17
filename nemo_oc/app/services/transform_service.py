"""
Capa de transformación: JSON de API Mercado Público → modelos internos.
No hay I/O ni dependencias de UI en este módulo.
"""
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from app.models.orden_compra import OrdenCompra
from app.models.linea_oc import LineaOC
from app.models.homologacion import HomologacionItem
from app.utils.rut_utils import rut_to_cliente_sap
from app.utils.regex_utils import extraer_codigo_mp

logger = logging.getLogger(__name__)


def parse_cabecera_oc(raw: dict) -> OrdenCompra:
    """
    Transforma el JSON de detalle de OC (un ítem de Listado) a OrdenCompra.
    Maneja tanto la estructura del endpoint de lista como la de detalle.
    """
    now = datetime.now().isoformat()
    fechas = raw.get("Fechas", {}) or {}
    comprador = raw.get("Comprador", {}) or {}
    proveedor = raw.get("Proveedor", {}) or {}
    items = raw.get("Items", {}) or {}

    rut_unidad = comprador.get("RutUnidad", "")
    cliente_sap = rut_to_cliente_sap(rut_unidad)

    return OrdenCompra(
        codigo_oc=raw.get("Codigo", ""),
        nombre_oc=raw.get("Nombre", raw.get("Descripcion", "")),
        codigo_estado_mp=raw.get("CodigoEstado", 0),
        estado_mp=raw.get("Estado", ""),
        codigo_tipo=str(raw.get("CodigoTipo", "")),
        tipo_oc=raw.get("Tipo", ""),
        fecha_creacion=_fmt_fecha(fechas.get("FechaCreacion") or raw.get("FechaCreacion")),
        fecha_envio=_fmt_fecha(fechas.get("FechaEnvio")),
        fecha_aceptacion=_fmt_fecha(fechas.get("FechaAceptacion")),
        fecha_cancelacion=_fmt_fecha(fechas.get("FechaCancelacion")),
        fecha_ultima_modificacion=_fmt_fecha(fechas.get("FechaUltimaModificacion")),
        total_neto=float(raw.get("TotalNeto", 0) or 0),
        impuestos=float(raw.get("Impuestos", 0) or 0),
        total=float(raw.get("Total", 0) or 0),
        porcentaje_iva=float(raw.get("PorcentajeIva", 0) or 0),
        descuentos=float(raw.get("Descuentos", 0) or 0),
        cargos=float(raw.get("Cargos", 0) or 0),
        moneda=raw.get("TipoMoneda", "CLP"),
        codigo_organismo=comprador.get("CodigoOrganismo", ""),
        nombre_organismo=comprador.get("NombreOrganismo", ""),
        rut_unidad=rut_unidad,
        codigo_unidad=comprador.get("CodigoUnidad", ""),
        nombre_unidad=comprador.get("NombreUnidad", ""),
        direccion_unidad=comprador.get("DireccionUnidad", ""),
        comuna_unidad=comprador.get("ComunaUnidad", ""),
        region_unidad=comprador.get("RegionUnidad", ""),
        codigo_licitacion=str(raw.get("CodigoLicitacion", "") or ""),
        direccion_despacho=comprador.get("DireccionUnidad", ""),
        direccion_facturacion="",
        codigo_proveedor=proveedor.get("Codigo", ""),
        nombre_proveedor=proveedor.get("Nombre", ""),
        rut_proveedor=proveedor.get("RutSucursal", proveedor.get("Rut", "")),
        cliente_sap_sugerido=cliente_sap,
        cantidad_lineas=int(items.get("Cantidad", 0) or 0),
        created_at=now,
        updated_at=now,
    )


def parse_detalle_oc(raw_items: List[dict], codigo_oc: str) -> List[LineaOC]:
    """
    Transforma la lista de ítems de la API a LineaOC (sin homologación aún).
    """
    now = datetime.now().isoformat()
    lineas = []
    for item in raw_items:
        espec = item.get("EspecificacionComprador", "") or ""
        codigo_mp = extraer_codigo_mp(espec)
        if not codigo_mp:
            # Fallback a CodigoProducto si existe y no es 0
            cp = item.get("CodigoProducto", 0)
            if cp and cp != 0:
                codigo_mp = str(cp)

        cantidad = float(item.get("Cantidad", 0) or 0)
        precio_neto = float(item.get("PrecioNeto", 0) or 0)

        lineas.append(LineaOC(
            codigo_oc=codigo_oc,
            correlativo=int(item.get("Correlativo", 0)),
            codigo_categoria=int(item.get("CodigoCategoria", 0) or 0),
            categoria=item.get("Categoria", "") or "",
            codigo_producto_api=str(item.get("CodigoProducto", "") or ""),
            codigo_mp=codigo_mp,
            producto=item.get("Producto", "") or "",
            especificacion_comprador=espec,
            especificacion_proveedor=item.get("EspecificacionProveedor", "") or "",
            cantidad=cantidad,
            unidad=item.get("Unidad", "") or "",
            moneda=item.get("Moneda", "CLP") or "CLP",
            precio_neto=precio_neto,
            total_cargos=float(item.get("TotalCargos", 0) or 0),
            total_descuentos=float(item.get("TotalDescuentos", 0) or 0),
            total_impuestos=float(item.get("TotalImpuestos", 0) or 0),
            total=float(item.get("Total", 0) or 0),
            estado_homologacion="pendiente",
            created_at=now,
            updated_at=now,
        ))
    return lineas


def homologar_lineas(
    lineas: List[LineaOC],
    catalog  # HomologacionService
) -> Tuple[List[LineaOC], List[int]]:
    """
    Aplica homologación a cada línea usando el catálogo.
    Retorna (lineas_anotadas, correlativos_sin_homologacion).
    """
    sin_homo = []
    for linea in lineas:
        item: Optional[HomologacionItem] = None
        if linea.codigo_mp:
            item = catalog.lookup(linea.codigo_mp)

        if item:
            femp = item.factor_empaque if item.factor_empaque and item.factor_empaque > 0 else 1.0
            linea.itemcode_sap = item.itemcode_sap
            # Descripción: preferir Maestra SAP si está cargada
            linea.descripcion_sap = item.descripcion_sap
            linea.factor_empaque = femp
            linea.cantidad_sap = linea.cantidad * femp
            linea.precio_sap = round(linea.precio_neto / femp if femp != 0 else linea.precio_neto, 2)
            linea.estado_homologacion = "homologado"
        else:
            linea.itemcode_sap = None
            linea.descripcion_sap = None
            linea.factor_empaque = 1.0
            linea.cantidad_sap = linea.cantidad
            linea.precio_sap = round(linea.precio_neto, 2)
            linea.estado_homologacion = "sin_homologacion"
            sin_homo.append(linea.correlativo)

    return lineas, sin_homo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_fecha(raw: Optional[str]) -> str:
    """Normaliza fechas ISO de la API a string ISO, o '' si es None."""
    if not raw:
        return ""
    # La API devuelve formato "2026-03-17T11:18:49.037" — tomar solo hasta segundos
    return raw[:19] if len(raw) >= 19 else raw
