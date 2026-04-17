"""Servicios de analitica y revision experta para desktop."""

from __future__ import annotations

from typing import Optional

from app.repositories import maestra_repo, oc_repository
from app.services.cartera_service import get_cartera_service
from app.services.licitaciones_service import get_licitaciones_service


def get_analytics_data(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 220,
) -> dict:
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

    pendientes_con_sugerencia = 0
    pendientes_sin_sugerencia = 0
    queue: list[dict] = []

    for row in queue_rows:
        cliente = cartera_svc.lookup(row["cliente_sap_sugerido"]) if row["cliente_sap_sugerido"] else None
        is_pending = (row["estado_homologacion"] or "pendiente") == "pendiente" or not row["itemcode_sap"]

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
                    sugerencia_principal = {
                        "itemcode_sap": top.itemcode_sap,
                        "descripcion_sap": top.descripcion_sap,
                        "descripcion_match": top.descripcion_match,
                        "frecuencia": top.frecuencia,
                        "score": top.score,
                        "estrellas": max(1, round(top.score * 5)),
                    }
                    pendientes_con_sugerencia += 1
                else:
                    pendientes_sin_sugerencia += 1
            else:
                pendientes_sin_sugerencia += 1

        queue.append(
            {
                "codigo_oc": row["codigo_oc"],
                "correlativo": row["correlativo"],
                "fecha_envio": row["fecha_envio"] or "",
                "tipo_oc": row["tipo_oc"] or "",
                "nombre_organismo": row["nombre_organismo"] or "",
                "cliente_sap_sugerido": row["cliente_sap_sugerido"] or "",
                "cartera": cliente.cartera if cliente else "",
                "estado_interno": row["estado_interno"] or "Nueva",
                "estado_homologacion": row["estado_homologacion"] or "pendiente",
                "itemcode_sap": row["itemcode_sap"],
                "descripcion_sap": row["descripcion_sap"],
                "producto": row["producto"] or "",
                "especificacion_comprador": row["especificacion_comprador"] or "",
                "cantidad": float(row["cantidad"] or 0),
                "total": float(row["total"] or 0),
                "rut_unidad": row["rut_unidad"] or "",
                "sugerencia_principal": sugerencia_principal,
            }
        )

    return {
        "summary": {
            **summary,
            "cola_revision": len(queue),
            "total_cola_sin_limite": total_cola_sin_limite,
            "pendientes_con_sugerencia": pendientes_con_sugerencia,
            "pendientes_sin_sugerencia": pendientes_sin_sugerencia,
        },
        "queue": queue,
    }


def get_line_suggestions(codigo_oc: str, correlativo: int, max_results: int = 5) -> list[dict]:
    oc = oc_repository.get_oc(codigo_oc)
    if not oc:
        return []

    lineas = oc_repository.get_lineas(codigo_oc)
    linea = next((l for l in lineas if l.correlativo == correlativo), None)
    if not linea:
        return []

    texto = " ".join(filter(None, [linea.especificacion_comprador, linea.producto])).strip()
    if not texto:
        return []

    svc = get_licitaciones_service()
    sugs = svc.buscar_sugerencias(texto, rut_oc=oc.rut_unidad, max_results=max_results)
    return [
        {
            "itemcode_sap": s.itemcode_sap,
            "descripcion_sap": s.descripcion_sap,
            "descripcion_match": s.descripcion_match,
            "frecuencia": s.frecuencia,
            "score": s.score,
            "estrellas": max(1, round(s.score * 5)),
        }
        for s in sugs
    ]


def search_maestra_items(query: str, limit: int = 15) -> list[dict]:
    return maestra_repo.search_maestra(query, limit=limit)


def assign_itemcode(
    codigo_oc: str,
    correlativo: int,
    itemcode_sap: str,
    descripcion_sap: str = "",
    origen: str = "manual",
) -> None:
    oc_repository.asignar_itemcode_linea(codigo_oc, correlativo, itemcode_sap, descripcion_sap, origen)


def clear_itemcode(codigo_oc: str, correlativo: int) -> None:
    oc_repository.limpiar_asignacion_linea(codigo_oc, correlativo)
