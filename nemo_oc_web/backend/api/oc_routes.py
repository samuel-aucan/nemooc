"""
Endpoints REST para Órdenes de Compra.
"""
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

_nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))

from app.repositories import oc_repository
from app.config import load_config
from app.utils.clipboard_utils import generar_texto_sap
from app.services.cartera_service import get_cartera_service
from app.services.licitaciones_service import get_licitaciones_service
from app.services.mp_api_service import MercadoPublicoAPI
from app.services.mp_portal_service import get_public_oc_portal_meta

from .schemas import (
    OrdenCompraOut, LineaOCOut, OcDetailOut, StatsOut, FiltrosOut, HoldingOut,
    SapTextOut, AsignarItemcodeIn, EstadoIn, NotasIn, SugerenciaOut,
    CatalogImportOut, AnalyticsOut, AnalyticsSummaryOut, ReviewQueueItemOut,
    AuditoriaResponse, OcAuditoriaItem,
)

router = APIRouter(prefix="/api/ocs", tags=["ocs"])


def _enrich_oc(oc, holdings_map: dict | None = None) -> dict:
    """Añade campos de cartera y holding a una OC."""
    d = oc.__dict__.copy()
    cartera_svc = get_cartera_service()
    cliente = cartera_svc.lookup(oc.cliente_sap_sugerido) if oc.cliente_sap_sugerido else None
    d["cartera"]       = cliente.cartera if cliente else ""
    d["region_nombre"] = cliente.region_nombre if cliente else ""
    d["razon_social"]  = cliente.razon if cliente else ""
    if holdings_map is None:
        holdings_map = oc_repository.get_holdings_map()
    d["holding_nombre"] = holdings_map.get(oc.codigo_organismo, "") if oc.codigo_organismo else ""
    return d


def _looks_like_public_oc(codigo_oc: str) -> bool:
    return bool(re.search(r"-[A-Z]{2,4}\d{2}$", (codigo_oc or "").upper()))


def _looks_generic_address(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {
        "",
        "sin dirección registrada para unidad de compra",
        "sin direccion registrada para unidad de compra",
        "bienes y servicios",
    }


def _enrich_public_metadata(oc) -> None:
    if not _looks_like_public_oc(oc.codigo_oc):
        return

    updated = False

    if not (oc.codigo_licitacion or "").strip():
        try:
            cfg = load_config()
            if cfg.api_ticket:
                raw = MercadoPublicoAPI(cfg.api_ticket, cfg.codigo_empresa).obtener_detalle_oc(oc.codigo_oc)
                codigo_licitacion = str(raw.get("CodigoLicitacion", "") or "").strip()
                if codigo_licitacion:
                    oc.codigo_licitacion = codigo_licitacion
                    updated = True
        except Exception:
            pass

    needs_despacho = _looks_generic_address(oc.direccion_despacho)
    needs_facturacion = _looks_generic_address(oc.direccion_facturacion)

    if needs_despacho or needs_facturacion:
        portal_meta = get_public_oc_portal_meta(oc.codigo_oc)
        if portal_meta.direccion_despacho and needs_despacho:
            oc.direccion_despacho = portal_meta.direccion_despacho
            updated = True
        if portal_meta.direccion_facturacion and needs_facturacion:
            oc.direccion_facturacion = portal_meta.direccion_facturacion
            updated = True

    if updated:
        oc_repository.actualizar_campos_publicos(
            oc.codigo_oc,
            codigo_licitacion=oc.codigo_licitacion or "",
            direccion_despacho=oc.direccion_despacho or "",
            direccion_facturacion=oc.direccion_facturacion or "",
        )


# ── Lista ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[OrdenCompraOut])
def list_ocs(
    estado:     List[str] = Query(default=[]),
    estado_mp:  List[str] = Query(default=[]),
    tipo_oc:    List[str] = Query(default=[]),
    cartera:    List[str] = Query(default=[]),
    holding:    List[str] = Query(default=[]),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    busqueda:   Optional[str] = Query(None),
):
    ocs = oc_repository.get_all_ocs(
        estado=estado or None,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        busqueda=busqueda,
        estado_mp=estado_mp or None,
        tipo_oc=tipo_oc or None,
        holding=holding or None,
    )
    holdings_map = oc_repository.get_holdings_map()
    enriched = [OrdenCompraOut(**_enrich_oc(oc, holdings_map)) for oc in ocs]
    if cartera:
        enriched = [o for o in enriched if o.cartera in cartera]
    return enriched


@router.get("/stats", response_model=StatsOut)
def get_stats():
    """Conteo rápido: total, sin homologar, ingresadas."""
    return StatsOut(**oc_repository.get_stats())


@router.get("/filtros", response_model=FiltrosOut)
def get_filtros():
    cartera_svc = get_cartera_service()
    carteras = sorted({
        c.cartera for c in cartera_svc._catalog.values() if c.cartera
    }) if hasattr(cartera_svc, "_catalog") else []

    raw_holdings = oc_repository.get_distinct_holdings()
    holdings = [HoldingOut(id=h["id"], nombre=h["nombre"]) for h in raw_holdings]

    return FiltrosOut(
        estados_mp=oc_repository.get_distinct_estados_mp(),
        tipos=oc_repository.get_distinct_tipos(),
        carteras=carteras,
        holdings=holdings,
    )


@router.get("/analytics", response_model=AnalyticsOut)
def get_analytics(
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    limit: int = Query(150, ge=20, le=400),
):
    cartera_svc = get_cartera_service()
    licitaciones_svc = get_licitaciones_service()

    summary = oc_repository.get_analytics_summary(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    total_cola_sin_limite = oc_repository.get_review_queue_count(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    queue_rows = oc_repository.get_review_queue(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )

    # Batch lookup: evitar N+1 queries (antes: 150 lookups, ahora: 1)
    cliente_codes = [r["cliente_sap_sugerido"] for r in queue_rows if r["cliente_sap_sugerido"]]
    clientes_map = cartera_svc.lookup_batch(cliente_codes) if cliente_codes else {}

    queue: list[ReviewQueueItemOut] = []

    for row in queue_rows:
        cliente = clientes_map.get(row["cliente_sap_sugerido"]) if row["cliente_sap_sugerido"] else None
        is_pending = (row["estado_homologacion"] or "pendiente") == "pendiente" or not (row["itemcode_sap"] or "").strip()

        sugerencia_principal = None
        if is_pending:
            texto = " ".join(filter(None, [row["especificacion_comprador"], row["producto"]])).strip()
            if texto:
                sugerencias = licitaciones_svc.buscar_sugerencias(
                    texto,
                    rut_oc=row["rut_unidad"],
                    max_results=1,
                )
                if sugerencias:
                    top = sugerencias[0]
                    sugerencia_principal = SugerenciaOut(
                        itemcode_sap=top.itemcode_sap,
                        descripcion_sap=top.descripcion_sap,
                        descripcion_match=top.descripcion_match,
                        frecuencia=top.frecuencia,
                        score=top.score,
                        estrellas=max(1, round(top.score * 5)),
                    )

        queue.append(
            ReviewQueueItemOut(
                codigo_oc=row["codigo_oc"],
                correlativo=row["correlativo"],
                fecha_envio=row["fecha_envio"] or "",
                tipo_oc=row["tipo_oc"] or "",
                nombre_organismo=row["nombre_organismo"] or "",
                cliente_sap_sugerido=row["cliente_sap_sugerido"] or "",
                cartera=cliente.cartera if cliente else "",
                estado_interno=row["estado_interno"] or "Nueva",
                estado_homologacion=row["estado_homologacion"] or "pendiente",
                itemcode_sap=row["itemcode_sap"],
                descripcion_sap=row["descripcion_sap"],
                producto=row["producto"] or "",
                especificacion_comprador=row["especificacion_comprador"] or "",
                cantidad=float(row["cantidad"] or 0),
                total=float(row["total"] or 0),
                rut_unidad=row["rut_unidad"] or "",
                sugerencia_principal=sugerencia_principal,
            )
        )

    return AnalyticsOut(
        summary=AnalyticsSummaryOut(
            **summary,
            cola_revision=len(queue),
            total_cola_sin_limite=total_cola_sin_limite,
        ),
        queue=queue,
    )


@router.get("/auditoria", response_model=AuditoriaResponse)
def get_auditoria(
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
):
    data = oc_repository.get_auditoria(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return AuditoriaResponse(
        aceptadas_sin_ingresar=[OcAuditoriaItem(**r) for r in data["aceptadas_sin_ingresar"]],
        ingresadas_sin_aceptar=[OcAuditoriaItem(**r) for r in data["ingresadas_sin_aceptar"]],
    )


@router.get("/export-all")
def export_all(
    estado:     List[str] = Query(default=[]),
    estado_mp:  List[str] = Query(default=[]),
    tipo_oc:    List[str] = Query(default=[]),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    busqueda:   Optional[str] = Query(None),
):
    import openpyxl
    from io import BytesIO

    ocs = oc_repository.get_all_ocs(
        estado=estado or None, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        busqueda=busqueda, estado_mp=estado_mp or None, tipo_oc=tipo_oc or None,
    )
    cartera_svc = get_cartera_service()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "OCs"

    headers = [
        "Código OC", "Tipo", "Estado MP", "Estado Interno",
        "Fecha Envío", "Comprador", "Cliente SAP", "Cartera",
        "Total Neto", "Impuestos", "Total", "Moneda",
        "Líneas", "Notas"
    ]
    ws.append(headers)

    for oc in ocs:
        cliente = cartera_svc.lookup(oc.cliente_sap_sugerido) if oc.cliente_sap_sugerido else None
        ws.append([
            oc.codigo_oc, oc.tipo_oc, oc.estado_mp, oc.estado_interno,
            oc.fecha_envio[:10] if oc.fecha_envio else "",
            oc.nombre_organismo, oc.cliente_sap_sugerido,
            cliente.cartera if cliente else "",
            oc.total_neto, oc.impuestos, oc.total, oc.moneda,
            oc.cantidad_lineas, oc.notas or "",
        ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=OCs_NemoChile_{fecha}.xlsx"},
    )


# ── Detalle ──────────────────────────────────────────────────────────────────

@router.get("/{codigo_oc}", response_model=OcDetailOut)
def get_oc(codigo_oc: str):
    oc = oc_repository.get_oc(codigo_oc)
    if not oc:
        raise HTTPException(404, detail=f"OC {codigo_oc} no encontrada")
    _enrich_public_metadata(oc)
    lineas = oc_repository.get_lineas(codigo_oc)
    return OcDetailOut(
        cabecera=OrdenCompraOut(**_enrich_oc(oc)),
        lineas=[LineaOCOut(**l.__dict__) for l in lineas],
    )


@router.put("/{codigo_oc}/estado")
def update_estado(codigo_oc: str, body: EstadoIn):
    oc_repository.actualizar_estado(codigo_oc, body.estado)
    return {"ok": True}


@router.put("/{codigo_oc}/ingresada")
def marcar_ingresada(codigo_oc: str):
    oc_repository.marcar_ingresada(codigo_oc)
    return {"ok": True}


@router.put("/{codigo_oc}/notas")
def update_notas(codigo_oc: str, body: NotasIn):
    oc_repository.guardar_notas(codigo_oc, body.notas)
    return {"ok": True}


@router.get("/{codigo_oc}/sap-text", response_model=SapTextOut)
def get_sap_text(codigo_oc: str):
    lineas = oc_repository.get_lineas(codigo_oc)
    texto, excluidos = generar_texto_sap(lineas)
    return SapTextOut(text=texto, excluidos=excluidos)


@router.get("/{codigo_oc}/export-excel")
def export_excel(codigo_oc: str):
    import openpyxl
    from io import BytesIO

    oc = oc_repository.get_oc(codigo_oc)
    if not oc:
        raise HTTPException(404)
    lineas = oc_repository.get_lineas(codigo_oc)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = codigo_oc

    ws.append(["Código OC", oc.codigo_oc])
    ws.append(["Tipo", oc.tipo_oc])
    ws.append(["Comprador", oc.nombre_organismo])
    ws.append(["Cliente SAP", oc.cliente_sap_sugerido])
    ws.append(["Total", oc.total, oc.moneda])
    ws.append([])

    headers = [
        "#", "Producto", "Espec. Comprador", "Cód MP",
        "ItemCode SAP", "Desc SAP", "Cantidad", "Cant SAP",
        "Precio Neto", "Precio SAP", "Total", "Estado"
    ]
    ws.append(headers)
    for l in lineas:
        ws.append([
            l.correlativo, l.producto, l.especificacion_comprador, l.codigo_mp or "",
            l.itemcode_sap or "", l.descripcion_sap or "",
            l.cantidad, l.cantidad_sap,
            l.precio_neto, l.precio_sap,
            l.total, l.estado_homologacion,
        ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={codigo_oc}.xlsx"},
    )


# ── Líneas ───────────────────────────────────────────────────────────────────

@router.put("/{codigo_oc}/lineas/{correlativo}/asignar")
def asignar_itemcode(codigo_oc: str, correlativo: int, body: AsignarItemcodeIn):
    from app.db import get_connection
    from datetime import datetime
    conn = get_connection()
    now = datetime.now().isoformat()
    estado = 'sugerido' if body.origen == 'sugerencia' else 'manual'
    try:
        conn.execute("""
            UPDATE oc_detalle
            SET itemcode_sap = ?, descripcion_sap = ?,
                estado_homologacion = ?, updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
        """, (body.itemcode_sap, body.descripcion_sap, estado, now, codigo_oc, correlativo))
        conn.commit()
    finally:
        conn.close()

    # Retroalimentar licitaciones_ref para mejorar sugerencias futuras
    try:
        oc = oc_repository.get_oc(codigo_oc)
        lineas = oc_repository.get_lineas(codigo_oc)
        linea = next((l for l in lineas if l.correlativo == correlativo), None)
        if oc and linea:
            from app.repositories.licitaciones_repo import upsert_from_assignment
            desc = linea.especificacion_comprador or linea.producto or ""
            upsert_from_assignment(
                descripcion_comprador=desc,
                itemcode_sap=body.itemcode_sap,
                rut_comprador=oc.rut_unidad or "",
                descripcion_nemo=body.descripcion_sap or "",
            )
    except Exception:
        pass  # No bloquear la asignación si falla el aprendizaje

    return {"ok": True}


@router.delete("/{codigo_oc}/lineas/{correlativo}/asignar")
def limpiar_asignacion(codigo_oc: str, correlativo: int):
    from app.db import get_connection
    from datetime import datetime
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute("""
            UPDATE oc_detalle
            SET itemcode_sap = NULL, descripcion_sap = NULL,
                estado_homologacion = 'pendiente', updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
        """, (now, codigo_oc, correlativo))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.post("/{codigo_oc}/rehomologar-privada")
def rehomologar_privada(codigo_oc: str):
    """Re-ejecuta el lookup del catálogo privado sobre las líneas sin itemcode."""
    from app.services.private_holding_service import lookup_private_catalog

    oc = oc_repository.get_oc(codigo_oc)
    if not oc:
        raise HTTPException(404, "OC no encontrada")
    if oc.tipo_oc != "PRIVADA":
        raise HTTPException(400, "Solo aplica a OCs privadas")

    holding_id = oc.codigo_organismo
    lineas = oc_repository.get_lineas(codigo_oc)
    actualizadas = 0

    for linea in lineas:
        if linea.itemcode_sap or not linea.codigo_mp:
            continue
        homo = lookup_private_catalog(holding_id, linea.codigo_mp)
        if homo and homo.itemcode_sap:
            oc_repository.asignar_itemcode_linea(
                codigo_oc,
                linea.correlativo,
                homo.itemcode_sap,
                homo.descripcion or "",
                origen="homologado",
            )
            actualizadas += 1

    return {"actualizadas": actualizadas}


@router.get("/{codigo_oc}/lineas/{correlativo}/sugerencias", response_model=list[SugerenciaOut])
def get_sugerencias(codigo_oc: str, correlativo: int):
    oc = oc_repository.get_oc(codigo_oc)
    if not oc:
        raise HTTPException(404)
        
    lineas = oc_repository.get_lineas(codigo_oc)
    linea = next((l for l in lineas if l.correlativo == correlativo), None)
    if not linea:
        raise HTTPException(404)

    texto = " ".join(filter(None, [linea.especificacion_comprador, linea.producto]))
    if not texto.strip():
        return []

    svc = get_licitaciones_service()
    sugs = svc.buscar_sugerencias(texto, rut_oc=oc.rut_unidad, max_results=5)
    return [
        SugerenciaOut(
            itemcode_sap=s.itemcode_sap,
            descripcion_sap=s.descripcion_sap,
            descripcion_match=s.descripcion_match,
            frecuencia=s.frecuencia,
            score=s.score,
            estrellas=max(1, round(s.score * 5)),
        )
        for s in sugs
    ]
