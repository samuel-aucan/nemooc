"""
Supabase OC Repository — Fase 1 NemoKey Migration
Lee/escribe oc_cabecera y oc_detalle desde Supabase PostgreSQL.
Misma interfaz publica que app/repositories/oc_repository.py (SQLite).

Cobertura:
  - CRUD completo: get_oc, get_lineas, get_all_ocs, get_existing_codes, etc.
  - Writes: save_oc, actualizar_estado, marcar_ingresada, asignar_itemcode_linea, etc.
  - Analytics: nativo PostgreSQL (Fase 1b). Sin dependencia de SQLite.
"""
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Set

logger = logging.getLogger(__name__)

# ── Importar modelos (path nemo_oc debe estar en sys.path) ────────────────────
try:
    from app.models.orden_compra import OrdenCompra
    from app.models.linea_oc import LineaOC
except ImportError:
    # Intentar agregar nemo_oc al path si no esta
    _nemo_oc = Path(__file__).parent.parent.parent / "nemo_oc"
    if str(_nemo_oc) not in sys.path:
        sys.path.insert(0, str(_nemo_oc))
    from app.models.orden_compra import OrdenCompra
    from app.models.linea_oc import LineaOC

# ── Cliente Supabase (lazy) ───────────────────────────────────────────────────
_sb = None


def _get_sb():
    global _sb
    if _sb:
        return _sb
    from supabase import create_client
    _sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )
    return _sb


# ── Management API para SQL raw (analytics) ──────────────────────────────────
def _raw_sql(sql: str, params: list | None = None) -> list[dict]:
    """
    Ejecuta SQL raw via Supabase Management API.
    Usar solo para analytics/queries complejas (no CRUD frecuente).
    """
    import requests

    pat = os.environ.get("SUPABASE_PAT", "")
    project = os.environ.get("SUPABASE_PROJECT", "")
    if not pat or not project:
        raise RuntimeError("SUPABASE_PAT y SUPABASE_PROJECT requeridos para SQL raw")

    url = f"https://api.supabase.com/v1/projects/{project}/database/query"
    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    # Supabase Management API no acepta parametros posicionales como psycopg2.
    # Sustituir manualmente (solo para queries internas — no expuestas al usuario).
    if params:
        for p in params:
            if p is None:
                replacement = "NULL"
            elif isinstance(p, str):
                safe = p.replace("'", "''")
                replacement = f"'{safe}'"
            elif isinstance(p, bool):
                replacement = "TRUE" if p else "FALSE"
            else:
                replacement = str(p)
            sql = sql.replace("%s", replacement, 1)

    r = requests.post(url, headers=headers, json={"query": sql}, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"SQL raw error {r.status_code}: {r.text[:300]}")
    data = r.json()
    return data if isinstance(data, list) else []


# ── Mapeo Supabase → modelos ──────────────────────────────────────────────────

def _row_to_oc(r: dict) -> OrdenCompra:
    """Convierte fila de oc_cabecera de Supabase a OrdenCompra."""
    return OrdenCompra(
        codigo_oc=r.get("codigo_oc") or "",
        nombre_oc=r.get("nombre_oc") or "",
        codigo_estado_mp=int(r.get("codigo_estado_mp") or 0),
        estado_mp=r.get("estado_mp") or "",
        codigo_tipo=r.get("codigo_tipo") or "",
        tipo_oc=r.get("tipo_oc") or "",
        fecha_creacion=r.get("fecha_creacion") or "",
        fecha_envio=r.get("fecha_envio") or "",
        fecha_aceptacion=r.get("fecha_aceptacion") or "",
        fecha_cancelacion=r.get("fecha_cancelacion") or "",
        fecha_ultima_modificacion=r.get("fecha_ultima_modificacion") or "",
        total_neto=float(r.get("total_neto") or 0),
        # Supabase guarda impuestos en total_impuestos (write service los mapea asi)
        impuestos=float(r.get("total_impuestos") or r.get("impuestos") or 0),
        total=float(r.get("total") or 0),
        porcentaje_iva=float(r.get("porcentaje_iva") or 0),
        descuentos=float(r.get("descuentos") or 0),
        cargos=float(r.get("cargos") or 0),
        moneda=r.get("moneda") or "CLP",
        codigo_organismo=r.get("codigo_organismo") or "",
        nombre_organismo=r.get("nombre_organismo") or "",
        rut_unidad=r.get("rut_unidad") or r.get("rut_organismo") or "",
        codigo_unidad=r.get("codigo_unidad") or "",
        nombre_unidad=r.get("nombre_unidad") or "",
        direccion_unidad=r.get("direccion_unidad") or "",
        comuna_unidad=r.get("comuna_unidad") or "",
        region_unidad=r.get("region_unidad") or "",
        codigo_licitacion=r.get("codigo_licitacion") or "",
        direccion_despacho=r.get("direccion_despacho") or "",
        direccion_facturacion=r.get("direccion_facturacion") or "",
        codigo_proveedor=r.get("codigo_proveedor") or "",
        nombre_proveedor=r.get("nombre_proveedor") or "",
        rut_proveedor=r.get("rut_proveedor") or "",
        cliente_sap_sugerido=r.get("cliente_sap_sugerido") or "",
        cantidad_lineas=int(r.get("cantidad_lineas") or 0),
        estado_interno=r.get("estado_interno") or "Nueva",
        fecha_ingreso=r.get("fecha_ingreso"),
        responsable_ingreso_user_id=None,  # no en Supabase (era ID local SQLite)
        responsable_ingreso_username=r.get("responsable_ingreso_username") or "",
        ingresado_por_user_id=None,        # no en Supabase
        ingresado_por_username=r.get("ingresado_por_username") or "",
        ingreso_sap_acuerdo_global=bool(r.get("ingreso_sap_acuerdo_global") or False),
        notas=r.get("notas"),
        created_at=r.get("created_at") or "",
        updated_at=r.get("updated_at") or "",
    )


def _row_to_linea(r: dict, codigo_oc: str = "") -> LineaOC:
    """Convierte fila de oc_detalle de Supabase a LineaOC."""
    return LineaOC(
        codigo_oc=codigo_oc,
        # Supabase usa nro_linea, SQLite usa correlativo
        correlativo=int(r.get("nro_linea") or r.get("correlativo") or 0),
        codigo_categoria=int(r.get("codigo_categoria") or 0),
        categoria=r.get("categoria") or "",
        codigo_producto_api=r.get("codigo_mp") or r.get("codigo_producto_api") or "",
        codigo_mp=r.get("codigo_mp"),
        # Supabase usa descripcion, SQLite usa producto
        producto=r.get("descripcion") or r.get("producto") or "",
        especificacion_comprador=r.get("especificacion_comprador") or r.get("especificacion") or "",
        especificacion_proveedor=r.get("especificacion_proveedor") or "",
        cantidad=float(r.get("cantidad") or 0),
        # Supabase usa unidad_medida, SQLite usa unidad
        unidad=r.get("unidad_medida") or r.get("unidad") or "",
        moneda=r.get("moneda") or "CLP",
        # Supabase usa precio_unitario, SQLite usa precio_neto
        precio_neto=float(r.get("precio_unitario") or r.get("precio_neto") or 0),
        total_cargos=float(r.get("total_cargos") or 0),
        total_descuentos=float(r.get("total_descuentos") or 0),
        total_impuestos=float(r.get("total_impuestos") or 0),
        # Supabase usa total_linea, SQLite usa total
        total=float(r.get("total_linea") or r.get("total") or 0),
        factor_empaque=float(r.get("factor_empaque") or 1),
        cantidad_sap=r.get("cantidad_sap"),
        precio_sap=r.get("precio_sap"),
        sap_mode=r.get("sap_mode"),
        sap_mode_origen=r.get("sap_mode_origen"),
        sap_values_origen=None,          # no en Supabase (no se escribe)
        sap_values_updated_at=r.get("sap_values_updated_at") or "",
        sap_values_updated_by_user_id=None,  # no en Supabase
        sap_values_updated_by_username="",
        itemcode_sap=r.get("itemcode_sap"),
        descripcion_sap=r.get("descripcion_sap"),
        estado_homologacion=r.get("estado_homologacion") or "pendiente",
        created_at=r.get("created_at") or "",
        updated_at=r.get("updated_at") or "",
    )


# ── Lectura oc_cabecera ───────────────────────────────────────────────────────

def get_existing_codes() -> Set[str]:
    """Retorna el conjunto de codigo_oc existentes."""
    try:
        rows = _raw_sql("SELECT codigo_oc FROM oc_cabecera")
        return {row["codigo_oc"] for row in rows}
    except Exception as e:
        logger.error(f"[supa_repo] get_existing_codes: {e}")
        return set()


def get_oc(codigo_oc: str) -> Optional[OrdenCompra]:
    try:
        rows = _raw_sql("SELECT * FROM oc_cabecera WHERE codigo_oc = %s LIMIT 1", [codigo_oc])
        return _row_to_oc(rows[0]) if rows else None
    except Exception as e:
        logger.error(f"[supa_repo] get_oc({codigo_oc}): {e}")
        return None


def get_oc_with_id(codigo_oc: str) -> tuple[Optional[OrdenCompra], Optional[str]]:
    """Retorna (oc, oc_uuid) para evitar re-queries de _get_oc_id()."""
    try:
        rows = _raw_sql("SELECT * FROM oc_cabecera WHERE codigo_oc = %s LIMIT 1", [codigo_oc])
        if not rows:
            return None, None
        return _row_to_oc(rows[0]), rows[0].get("id")
    except Exception as e:
        logger.error(f"[supa_repo] get_oc_with_id({codigo_oc}): {e}")
        return None, None


def _build_oc_where(
    estado=None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    fecha_ingreso_desde: Optional[str] = None,
    fecha_ingreso_hasta: Optional[str] = None,
    busqueda: Optional[str] = None,
    estado_mp=None,
    tipo_oc=None,
    holding=None,
    responsable=None,
) -> tuple[str, list]:
    """Construye la clausula WHERE para queries de oc_cabecera."""
    where = "WHERE 1=1"
    params: list = []

    def _add_in(col: str, value) -> None:
        nonlocal where
        if not value:
            return
        vals = [value] if isinstance(value, str) else list(value)
        vals = [v for v in vals if v and v != "Todos"]
        if not vals:
            return
        placeholders = ", ".join(["%s"] * len(vals))
        where += f" AND {col} IN ({placeholders})"
        params.extend(vals)

    _add_in("estado_interno", estado)
    _add_in("estado_mp", estado_mp)
    _add_in("tipo_oc", tipo_oc)
    _add_in("codigo_organismo", holding)

    if responsable:
        vals = [responsable] if isinstance(responsable, str) else list(responsable)
        vals = [v for v in vals if v and v != "Todos"]
        if vals:
            clauses = []
            normal_vals = []
            for v in vals:
                if v == "__sin_responsable__":
                    clauses.append("(responsable_ingreso_username IS NULL OR responsable_ingreso_username = '')")
                else:
                    normal_vals.append(v)
            if normal_vals:
                ph = ", ".join(["%s"] * len(normal_vals))
                clauses.append(f"responsable_ingreso_username IN ({ph})")
                params.extend(normal_vals)
            if clauses:
                where += f" AND ({' OR '.join(clauses)})"

    if fecha_desde:
        where += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio::text), ''), created_at::text)) >= DATE(%s)"
        params.append(fecha_desde)
    if fecha_hasta:
        where += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio::text), ''), created_at::text)) <= DATE(%s)"
        params.append(fecha_hasta)
    if fecha_ingreso_desde:
        where += " AND DATE(fecha_ingreso) >= DATE(%s)"
        params.append(fecha_ingreso_desde)
    if fecha_ingreso_hasta:
        where += " AND DATE(fecha_ingreso) <= DATE(%s)"
        params.append(fecha_ingreso_hasta)
    if busqueda:
        like = f"%{busqueda}%"
        where += " AND (codigo_oc ILIKE %s OR nombre_organismo ILIKE %s OR cliente_sap_sugerido ILIKE %s)"
        params.extend([like, like, like])

    return where, params


def get_all_ocs(
    estado=None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    fecha_ingreso_desde: Optional[str] = None,
    fecha_ingreso_hasta: Optional[str] = None,
    busqueda: Optional[str] = None,
    estado_mp=None,
    tipo_oc=None,
    holding=None,
    responsable=None,
    limit: int = 0,
    offset: int = 0,
) -> tuple[List[OrdenCompra], int]:
    """Retorna (ocs, total_count). Si limit=0 retorna todas (sin paginacion)."""

    where, params = _build_oc_where(
        estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        fecha_ingreso_desde=fecha_ingreso_desde, fecha_ingreso_hasta=fecha_ingreso_hasta,
        busqueda=busqueda, estado_mp=estado_mp, tipo_oc=tipo_oc,
        holding=holding, responsable=responsable,
    )

    order = " ORDER BY COALESCE(NULLIF(TRIM(fecha_envio::text), ''), created_at::text) DESC"

    try:
        count_rows = _raw_sql(f"SELECT COUNT(*) AS total FROM oc_cabecera {where}", params[:] if params else None)
        total = int(count_rows[0]["total"]) if count_rows else 0

        sql = f"SELECT * FROM oc_cabecera {where}{order}"
        query_params = params[:]
        if limit > 0:
            sql += " LIMIT %s OFFSET %s"
            query_params.extend([limit, offset])

        rows = _raw_sql(sql, query_params or None)
        return [_row_to_oc(r) for r in rows], total
    except Exception as e:
        logger.error(f"[supa_repo] get_all_ocs error: {e}")
        return [], 0


def get_distinct_estados_mp() -> List[str]:
    try:
        rows = _raw_sql(
            "SELECT DISTINCT estado_mp FROM oc_cabecera "
            "WHERE estado_mp IS NOT NULL AND estado_mp != '' ORDER BY estado_mp"
        )
        return [r["estado_mp"] for r in rows]
    except Exception as e:
        logger.error(f"[supa_repo] get_distinct_estados_mp: {e}")
        return []


def get_distinct_tipos() -> List[str]:
    try:
        rows = _raw_sql(
            "SELECT DISTINCT tipo_oc FROM oc_cabecera "
            "WHERE tipo_oc IS NOT NULL AND tipo_oc != '' ORDER BY tipo_oc"
        )
        return [r["tipo_oc"] for r in rows]
    except Exception as e:
        logger.error(f"[supa_repo] get_distinct_tipos: {e}")
        return []


import time as _time

_holdings_cache: dict = {"data": {}, "ts": 0.0}
_HOLDINGS_TTL = 300


def get_holdings_map() -> dict:
    if _time.time() - _holdings_cache["ts"] < _HOLDINGS_TTL and _holdings_cache["data"]:
        return _holdings_cache["data"]
    try:
        rows = _raw_sql("SELECT id, nombre FROM holdings WHERE activo = TRUE")
        result = {row["id"]: row["nombre"] for row in rows}
        _holdings_cache["data"] = result
        _holdings_cache["ts"] = _time.time()
        return result
    except Exception as e:
        logger.error(f"[supa_repo] get_holdings_map: {e}")
        return _holdings_cache["data"] or {}


def get_distinct_holdings() -> List[dict]:
    try:
        rows = _raw_sql("""
            SELECT h.id, h.nombre
            FROM holdings h
            INNER JOIN oc_cabecera o ON h.id = o.codigo_organismo
            WHERE o.tipo_oc = 'PRIVADA'
            GROUP BY h.id, h.nombre
            ORDER BY h.nombre
        """)
        return [{"id": r["id"], "nombre": r["nombre"]} for r in rows]
    except Exception as e:
        logger.error(f"[supa_repo] get_distinct_holdings: {e}")
        return []


def get_stats() -> dict:
    try:
        rows = _raw_sql("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN estado_interno = 'Ingresada' THEN 1 ELSE 0 END) AS ingresadas
            FROM oc_cabecera
        """)
        total = int(rows[0].get("total") or 0) if rows else 0
        ingresadas = int(rows[0].get("ingresadas") or 0) if rows else 0

        # OCs con al menos una linea sin homologar
        rows2 = _raw_sql("""
            SELECT COUNT(DISTINCT oc_id) AS sin_homolog
            FROM oc_detalle
            WHERE estado_homologacion NOT IN ('homologada', 'manual')
        """)
        sin_homolog = int(rows2[0].get("sin_homolog") or 0) if rows2 else 0

        return {"total": total, "sin_homolog": sin_homolog, "ingresadas": ingresadas}
    except Exception as e:
        logger.error(f"[supa_repo] get_stats: {e}")
        return {"total": 0, "sin_homolog": 0, "ingresadas": 0}


# ── Lectura oc_detalle ────────────────────────────────────────────────────────

def _get_oc_id(codigo_oc: str) -> Optional[str]:
    """Obtiene el UUID de oc_cabecera para un codigo_oc dado."""
    try:
        rows = _raw_sql("SELECT id FROM oc_cabecera WHERE codigo_oc = %s LIMIT 1", [codigo_oc])
        return rows[0]["id"] if rows else None
    except Exception:
        return None


def get_lineas(codigo_oc: str, oc_id: Optional[str] = None) -> List[LineaOC]:
    if not oc_id:
        oc_id = _get_oc_id(codigo_oc)
    if not oc_id:
        return []
    try:
        rows = _raw_sql(
            "SELECT * FROM oc_detalle WHERE oc_id = %s ORDER BY nro_linea",
            [oc_id],
        )
        return [_row_to_linea(row, codigo_oc) for row in rows]
    except Exception as e:
        logger.error(f"[supa_repo] get_lineas({codigo_oc}): {e}")
        return []


# ── Historial y document source ───────────────────────────────────────────────

def get_estado_historial(codigo_oc: str, limit: int = 10, oc_id: Optional[str] = None) -> List[dict]:
    if not oc_id:
        oc_id = _get_oc_id(codigo_oc)
    if not oc_id:
        return []
    try:
        rows = _raw_sql(
            "SELECT * FROM oc_estado_historial WHERE oc_id = %s ORDER BY created_at DESC LIMIT %s",
            [oc_id, limit],
        )
        result = []
        for row in rows:
            raw_id = row.get("id", "")
            int_id = abs(hash(str(raw_id))) % (2**31)
            result.append({
                "id": int_id,
                "codigo_oc": codigo_oc,
                "estado_anterior": row.get("estado_anterior"),
                "estado_nuevo": row.get("estado_nuevo"),
                "origen": row.get("origen"),
                "actor_user_id": None,
                "actor_username": row.get("actor_nombre") or "",
                "changed_at": row.get("created_at"),
            })
        return result
    except Exception as e:
        logger.error(f"[supa_repo] get_estado_historial({codigo_oc}): {e}")
        return []


def get_document_source(codigo_oc: str) -> Optional[dict]:
    try:
        rows = _raw_sql(
            "SELECT * FROM oc_document_source WHERE codigo_oc = %s LIMIT 1",
            [codigo_oc],
        )
        if not rows:
            return None
        data = dict(rows[0])
        payload = data.get("access_payload") or ""
        if isinstance(payload, str) and payload:
            import json
            try:
                data["access_payload"] = json.loads(payload)
            except Exception:
                pass
        data["document_available"] = bool(data.get("document_available"))
        data["document_regenerable"] = bool(data.get("document_regenerable"))
        return data
    except Exception as e:
        logger.error(f"[supa_repo] get_document_source({codigo_oc}): {e}")
        return None


# ── Escrituras ────────────────────────────────────────────────────────────────

def save_oc(oc: OrdenCompra, lineas: List[LineaOC]) -> None:
    """Guarda OC en Supabase (upsert por codigo_oc). Dual-write ya manejado."""
    from backend.supabase_write_service import upsert_oc
    upsert_oc(oc, lineas)


def upsert_document_source(
    codigo_oc: str,
    source_type: str,
    source_locator: str = "",
    access_payload=None,
    snapshot_type: str = "",
    snapshot_path: str = "",
    snapshot_sha256: str = "",
    snapshot_size_bytes: int = 0,
    document_available: bool = False,
    document_regenerable: bool = False,
    last_verified_at: str = "",
    **kwargs,
) -> None:
    import json
    payload_str = json.dumps(access_payload) if access_payload and not isinstance(access_payload, str) else (access_payload or "")
    try:
        _raw_sql("""
            INSERT INTO oc_document_source (codigo_oc, source_type, source_locator, access_payload,
                snapshot_type, snapshot_path, snapshot_sha256, snapshot_size_bytes,
                document_available, document_regenerable, last_verified_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (codigo_oc) DO UPDATE SET
                source_type = EXCLUDED.source_type,
                source_locator = EXCLUDED.source_locator,
                access_payload = EXCLUDED.access_payload,
                snapshot_type = EXCLUDED.snapshot_type,
                snapshot_path = EXCLUDED.snapshot_path,
                snapshot_sha256 = EXCLUDED.snapshot_sha256,
                snapshot_size_bytes = EXCLUDED.snapshot_size_bytes,
                document_available = EXCLUDED.document_available,
                document_regenerable = EXCLUDED.document_regenerable,
                last_verified_at = EXCLUDED.last_verified_at,
                updated_at = EXCLUDED.updated_at
        """, [
            codigo_oc, source_type, source_locator or None, payload_str or None,
            snapshot_type or None, snapshot_path or None, snapshot_sha256 or None,
            snapshot_size_bytes or 0, document_available, document_regenerable,
            last_verified_at or None, datetime.now(timezone.utc).isoformat(),
        ])
    except Exception as e:
        logger.warning(f"[supa_repo] upsert_document_source({codigo_oc}): {e}")


def actualizar_estado(
    codigo_oc: str,
    estado: str,
    actor_user_id=None,
    actor_username: str = "",
) -> None:
    """Cambia estado_interno en Supabase y registra en historial."""
    from backend.supabase_write_service import sync_estado_oc
    sync_estado_oc(codigo_oc, {"estado_interno": estado})
    # Registrar en historial
    try:
        oc_id = _get_oc_id(codigo_oc)
        if oc_id:
            _raw_sql("""
                INSERT INTO oc_estado_historial (oc_id, estado_anterior, estado_nuevo, origen, actor_nombre, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [oc_id, None, estado, "selector_estado", actor_username or None,
                  datetime.now(timezone.utc).isoformat()])
    except Exception as e:
        logger.debug(f"[supa_repo] historial actualizar_estado: {e}")


def marcar_ingresada(
    codigo_oc: str,
    actor_user_id=None,
    actor_username: str = "",
    acuerdo_global: bool = False,
) -> None:
    from backend.supabase_write_service import sync_estado_oc
    sync_estado_oc(codigo_oc, {
        "estado_interno": "Ingresada",
        "ingreso_sap_acuerdo_global": acuerdo_global,
        "ingresado_por_username": actor_username or None,
        "fecha_ingreso": datetime.now(timezone.utc).isoformat(),
    })
    try:
        oc_id = _get_oc_id(codigo_oc)
        if oc_id:
            _raw_sql("""
                INSERT INTO oc_estado_historial (oc_id, estado_anterior, estado_nuevo, origen, actor_nombre, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [oc_id, None, "Ingresada", "ingresada", actor_username or None,
                  datetime.now(timezone.utc).isoformat()])
    except Exception as e:
        logger.debug(f"[supa_repo] historial marcar_ingresada: {e}")


def asignar_responsable_ingreso(
    codigo_oc: str,
    user_id=None,
    username: str = "",
) -> None:
    from backend.supabase_write_service import sync_estado_oc
    sync_estado_oc(codigo_oc, {"responsable_ingreso_username": username or None})


def guardar_notas(codigo_oc: str, notas: str) -> None:
    from backend.supabase_write_service import sync_estado_oc
    sync_estado_oc(codigo_oc, {"notas": notas})


def actualizar_campos_publicos(codigo_oc: str, campos: dict) -> None:
    """Actualiza campos traidos de la API MP (estado_mp, fechas, etc.)"""
    from backend.supabase_write_service import sync_estado_oc
    # Filtrar solo campos validos de oc_cabecera
    allowed = {
        "estado_mp", "codigo_estado_mp", "fecha_envio", "fecha_aceptacion",
        "fecha_cancelacion", "fecha_ultima_modificacion", "total_neto",
        "total", "total_impuestos", "moneda", "codigo_licitacion",
        "direccion_despacho", "direccion_facturacion",
    }
    clean = {k: v for k, v in campos.items() if k in allowed}
    if clean:
        sync_estado_oc(codigo_oc, clean)


def asignar_itemcode_linea(
    codigo_oc: str,
    correlativo: int,
    itemcode_sap: str,
    descripcion_sap: str = "",
    origen: str = "manual",
) -> None:
    """Asigna itemcode SAP a una linea. Proxy al repo SQLite + dual-write Supabase."""
    # El repo SQLite maneja la logica de sap_mode + aprendizaje licitaciones
    try:
        from app.repositories.oc_repository import asignar_itemcode_linea as _sqlite_asignar
        _sqlite_asignar(codigo_oc, correlativo, itemcode_sap, descripcion_sap, origen)
    except Exception as e:
        logger.warning(f"[supa_repo] asignar_itemcode_linea SQLite error: {e}")

    # Sincronizar en Supabase
    from backend.supabase_write_service import sync_homologacion
    _ESTADOS = {"homologado": "homologada", "sugerido": "sugerida", "manual": "manual"}
    estado = _ESTADOS.get(origen, "manual")
    sync_homologacion(
        codigo_oc=codigo_oc,
        nro_linea=correlativo,
        itemcode_sap=itemcode_sap,
        descripcion_sap=descripcion_sap,
        cantidad_sap=None,
        precio_sap=None,
        sap_mode=None,
        estado_homologacion=estado,
    )


def limpiar_asignacion_linea(codigo_oc: str, correlativo: int) -> None:
    """Limpia itemcode SAP de una linea. Proxy al repo SQLite + dual-write Supabase."""
    try:
        from app.repositories.oc_repository import limpiar_asignacion_linea as _sqlite_limpiar
        _sqlite_limpiar(codigo_oc, correlativo)
    except Exception as e:
        logger.warning(f"[supa_repo] limpiar_asignacion_linea SQLite error: {e}")

    from backend.supabase_write_service import sync_homologacion
    sync_homologacion(
        codigo_oc=codigo_oc,
        nro_linea=correlativo,
        itemcode_sap=None,
        descripcion_sap=None,
        cantidad_sap=None,
        precio_sap=None,
        sap_mode=None,
        estado_homologacion="pendiente",
    )


def actualizar_estado_mp_oc(codigo_oc: str, codigo_estado_mp: int, estado_mp: str) -> None:
    from backend.supabase_write_service import sync_estado_oc
    sync_estado_oc(codigo_oc, {
        "codigo_estado_mp": codigo_estado_mp,
        "estado_mp": estado_mp,
    })


# ── Analytics — Fase 1b: nativo PostgreSQL ────────────────────────────────────
# Todas las funciones usan _raw_sql contra Supabase PostgreSQL.
# Adaptaciones respecto a SQLite:
#   - DATE(x)  →  (x)::date
#   - l.correlativo  →  l.nro_linea
#   - l.producto  →  l.descripcion
#   - l.total  →  l.total_linea
#   - LIMIT ?  →  LIMIT %s  (sustitucion manual en _raw_sql)

def _pct(numerator: float, denominator: float) -> float:
    return round((float(numerator) / float(denominator)) * 100, 1) if denominator else 0.0


def _date_part(value: str) -> str:
    return (value or "").strip()[:10]


def _parse_datetime(value) -> Optional[datetime]:
    raw = (value or "").strip() if isinstance(value, str) else str(value or "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw[:19])
    except ValueError:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _date_filter_sql(fecha_desde: Optional[str], fecha_hasta: Optional[str], params: list, col_expr: str) -> str:
    """Agrega filtros de fecha a una query PG. col_expr debe castear a date."""
    extra = ""
    if fecha_desde:
        extra += f" AND ({col_expr})::date >= %s::date"
        params.append(fecha_desde)
    if fecha_hasta:
        extra += f" AND ({col_expr})::date <= %s::date"
        params.append(fecha_hasta)
    return extra


def get_analytics_summary(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> dict:
    params: list = []
    date_expr = "COALESCE(NULLIF(TRIM(c.fecha_envio::text), ''), c.created_at::text)"
    date_filter = _date_filter_sql(fecha_desde, fecha_hasta, params, date_expr)

    sql = f"""
        SELECT
            COUNT(DISTINCT c.codigo_oc) AS total_ocs,
            COUNT(l.nro_linea)          AS total_lineas,
            COALESCE(SUM(l.total_linea), 0) AS monto_total,
            COALESCE(SUM(CASE WHEN COALESCE(TRIM(l.itemcode_sap), '') != ''
                              THEN COALESCE(l.total_linea, 0) ELSE 0 END), 0) AS monto_resuelto,
            COALESCE(SUM(CASE WHEN COALESCE(TRIM(l.itemcode_sap), '') != '' THEN 1 ELSE 0 END), 0) AS lineas_resueltas,
            COALESCE(SUM(CASE WHEN COALESCE(l.estado_homologacion, '') = 'manual'   THEN 1 ELSE 0 END), 0) AS lineas_manuales,
            COALESCE(SUM(CASE WHEN COALESCE(l.estado_homologacion, '') = 'sugerido' THEN 1 ELSE 0 END), 0) AS lineas_sugeridas,
            COALESCE(SUM(CASE WHEN COALESCE(l.estado_homologacion, '') = 'homologado' THEN 1 ELSE 0 END), 0) AS lineas_homologadas,
            COALESCE(SUM(CASE WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                               OR COALESCE(l.estado_homologacion, 'pendiente') = 'pendiente'
                              THEN 1 ELSE 0 END), 0) AS lineas_pendientes,
            COUNT(DISTINCT CASE WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                               OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
                              THEN c.codigo_oc ELSE NULL END) AS ocs_por_revisar,
            COALESCE(SUM(CASE WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                               AND (COALESCE(TRIM(l.especificacion_comprador), '') != ''
                                    OR COALESCE(TRIM(l.descripcion), '') != '')
                              THEN 1 ELSE 0 END), 0) AS pendientes_con_texto,
            COALESCE(SUM(CASE WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                               AND COALESCE(TRIM(l.especificacion_comprador), '') = ''
                               AND COALESCE(TRIM(l.descripcion), '') = ''
                              THEN 1 ELSE 0 END), 0) AS pendientes_sin_texto
        FROM oc_cabecera c
        LEFT JOIN oc_detalle l ON l.oc_id = c.id
        WHERE 1=1{date_filter}
    """
    try:
        rows = _raw_sql(sql, params)
        row = rows[0] if rows else {}
        total_lineas    = int(row.get("total_lineas") or 0)
        lineas_resueltas = int(row.get("lineas_resueltas") or 0)
        monto_total     = float(row.get("monto_total") or 0.0)
        monto_resuelto  = float(row.get("monto_resuelto") or 0.0)
        return {
            "total_ocs":           int(row.get("total_ocs") or 0),
            "total_lineas":        total_lineas,
            "lineas_resueltas":    lineas_resueltas,
            "lineas_pendientes":   int(row.get("lineas_pendientes") or 0),
            "lineas_manuales":     int(row.get("lineas_manuales") or 0),
            "lineas_sugeridas":    int(row.get("lineas_sugeridas") or 0),
            "lineas_homologadas":  int(row.get("lineas_homologadas") or 0),
            "ocs_por_revisar":     int(row.get("ocs_por_revisar") or 0),
            "pendientes_con_texto":int(row.get("pendientes_con_texto") or 0),
            "pendientes_sin_texto":int(row.get("pendientes_sin_texto") or 0),
            "monto_total":         monto_total,
            "monto_resuelto":      monto_resuelto,
            "cobertura_lineas_pct": _pct(lineas_resueltas, total_lineas),
            "cobertura_monto_pct":  _pct(monto_resuelto, monto_total),
        }
    except Exception as e:
        logger.error(f"[supa_repo] get_analytics_summary: {e}")
        return {k: 0 for k in ("total_ocs","total_lineas","lineas_resueltas","lineas_pendientes",
                                "lineas_manuales","lineas_sugeridas","lineas_homologadas",
                                "ocs_por_revisar","pendientes_con_texto","pendientes_sin_texto",
                                "monto_total","monto_resuelto","cobertura_lineas_pct","cobertura_monto_pct")}


def get_received_by_day(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> list:
    params: list = []
    date_expr = "COALESCE(NULLIF(TRIM(fecha_envio::text), ''), created_at::text)"
    date_filter = _date_filter_sql(fecha_desde, fecha_hasta, params, date_expr)
    sql = f"""
        SELECT
            ({date_expr})::date AS fecha,
            COUNT(*) AS cantidad_ocs,
            COALESCE(SUM(COALESCE(total, total_neto, 0)), 0) AS monto_total
        FROM oc_cabecera
        WHERE COALESCE(NULLIF(TRIM(fecha_envio::text), ''), NULLIF(created_at::text, ''), '') != ''
        {date_filter}
        GROUP BY ({date_expr})::date
        ORDER BY ({date_expr})::date ASC
    """
    try:
        rows = _raw_sql(sql, params)
        return [
            {
                "fecha": str(r.get("fecha") or "")[:10],
                "cantidad_ocs": int(r.get("cantidad_ocs") or 0),
                "monto_total": float(r.get("monto_total") or 0.0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[supa_repo] get_received_by_day: {e}")
        return []


def get_entered_by_day(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> list:
    params: list = []
    date_expr = "fecha_ingreso::text"
    date_filter = _date_filter_sql(fecha_desde, fecha_hasta, params, date_expr)
    sql = f"""
        SELECT
            fecha_ingreso::date AS fecha,
            COUNT(*) AS cantidad_ocs,
            COALESCE(SUM(COALESCE(total, total_neto, 0)), 0) AS monto_total
        FROM oc_cabecera
        WHERE fecha_ingreso IS NOT NULL
        {date_filter}
        GROUP BY fecha_ingreso::date
        ORDER BY fecha_ingreso::date ASC
    """
    try:
        rows = _raw_sql(sql, params)
        return [
            {
                "fecha": str(r.get("fecha") or "")[:10],
                "cantidad_ocs": int(r.get("cantidad_ocs") or 0),
                "monto_total": float(r.get("monto_total") or 0.0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[supa_repo] get_entered_by_day: {e}")
        return []


def get_top_clients_by_amount(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 8,
) -> list:
    params: list = []
    date_expr = "COALESCE(NULLIF(TRIM(fecha_envio::text), ''), created_at::text)"
    date_filter = _date_filter_sql(fecha_desde, fecha_hasta, params, date_expr)
    params.append(limit)
    sql = f"""
        SELECT
            COALESCE(NULLIF(TRIM(cliente_sap_sugerido), ''), 'Sin cliente SAP') AS label,
            COUNT(*) AS cantidad_ocs,
            COALESCE(SUM(COALESCE(total, total_neto, 0)), 0) AS monto_total
        FROM oc_cabecera
        WHERE 1=1{date_filter}
        GROUP BY COALESCE(NULLIF(TRIM(cliente_sap_sugerido), ''), 'Sin cliente SAP')
        ORDER BY monto_total DESC, cantidad_ocs DESC, label ASC
        LIMIT %s
    """
    try:
        rows = _raw_sql(sql, params)
        return [
            {
                "label": r.get("label") or "Sin cliente SAP",
                "cantidad_ocs": int(r.get("cantidad_ocs") or 0),
                "monto_total": float(r.get("monto_total") or 0.0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[supa_repo] get_top_clients_by_amount: {e}")
        return []


def get_top_buyers_by_amount(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 8,
) -> list:
    params: list = []
    date_expr = "COALESCE(NULLIF(TRIM(fecha_envio::text), ''), created_at::text)"
    date_filter = _date_filter_sql(fecha_desde, fecha_hasta, params, date_expr)
    params.append(limit)
    sql = f"""
        SELECT
            COALESCE(NULLIF(TRIM(nombre_organismo), ''), 'Sin comprador') AS label,
            COUNT(*) AS cantidad_ocs,
            COALESCE(SUM(COALESCE(total, total_neto, 0)), 0) AS monto_total
        FROM oc_cabecera
        WHERE 1=1{date_filter}
        GROUP BY COALESCE(NULLIF(TRIM(nombre_organismo), ''), 'Sin comprador')
        ORDER BY monto_total DESC, cantidad_ocs DESC, label ASC
        LIMIT %s
    """
    try:
        rows = _raw_sql(sql, params)
        return [
            {
                "label": r.get("label") or "Sin comprador",
                "cantidad_ocs": int(r.get("cantidad_ocs") or 0),
                "monto_total": float(r.get("monto_total") or 0.0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[supa_repo] get_top_buyers_by_amount: {e}")
        return []


def get_top_blocking_products(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 20,
) -> list:
    params: list = []
    date_expr = "COALESCE(NULLIF(TRIM(c.fecha_envio::text), ''), c.created_at::text)"
    date_filter = _date_filter_sql(fecha_desde, fecha_hasta, params, date_expr)
    params.append(limit)
    sql = f"""
        SELECT
            COALESCE(NULLIF(TRIM(l.especificacion_comprador), ''),
                     NULLIF(TRIM(l.descripcion), ''),
                     'Sin descripcion') AS label,
            COUNT(*) AS cantidad_lineas,
            COUNT(DISTINCT c.codigo_oc) AS cantidad_ocs,
            COALESCE(SUM(COALESCE(l.total_linea, 0)), 0) AS monto_total
        FROM oc_cabecera c
        INNER JOIN oc_detalle l ON l.oc_id = c.id
        WHERE (
              COALESCE(TRIM(l.itemcode_sap), '') = ''
           OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
        ){date_filter}
        GROUP BY COALESCE(NULLIF(TRIM(l.especificacion_comprador), ''),
                          NULLIF(TRIM(l.descripcion), ''),
                          'Sin descripcion')
        ORDER BY cantidad_lineas DESC, monto_total DESC
        LIMIT %s
    """
    try:
        rows = _raw_sql(sql, params)
        return [
            {
                "label": r.get("label") or "Sin descripcion",
                "cantidad_lineas": int(r.get("cantidad_lineas") or 0),
                "cantidad_ocs": int(r.get("cantidad_ocs") or 0),
                "monto_total": float(r.get("monto_total") or 0.0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[supa_repo] get_top_blocking_products: {e}")
        return []


def get_review_queue(
    estado: Optional[str] = None,
    responsable: Optional[str] = None,
    tipo_oc: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> list:
    params: list = []
    date_expr = "COALESCE(NULLIF(TRIM(c.fecha_envio::text), ''), c.created_at::text)"
    date_filter = _date_filter_sql(fecha_desde, fecha_hasta, params, date_expr)
    params.append(limit)
    sql = f"""
        SELECT
            c.codigo_oc,
            c.fecha_envio,
            c.tipo_oc,
            c.nombre_organismo,
            c.cliente_sap_sugerido,
            c.estado_interno,
            c.rut_unidad,
            l.nro_linea        AS correlativo,
            l.descripcion      AS producto,
            l.especificacion_comprador,
            l.cantidad,
            l.total_linea      AS total,
            l.itemcode_sap,
            l.descripcion_sap,
            l.estado_homologacion
        FROM oc_cabecera c
        INNER JOIN oc_detalle l ON l.oc_id = c.id
        WHERE (
              COALESCE(TRIM(l.itemcode_sap), '') = ''
           OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
        ){date_filter}
        ORDER BY
            CASE WHEN COALESCE(TRIM(l.itemcode_sap), '') = '' THEN 0
                 WHEN COALESCE(l.estado_homologacion, '') = 'manual' THEN 1
                 ELSE 2
            END,
            ({date_expr})::date DESC,
            c.codigo_oc DESC,
            l.nro_linea ASC
        LIMIT %s
    """
    try:
        return _raw_sql(sql, params)
    except Exception as e:
        logger.error(f"[supa_repo] get_review_queue: {e}")
        return []


def get_review_queue_count(
    estado: Optional[str] = None,
    responsable: Optional[str] = None,
    tipo_oc: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> int:
    params: list = []
    date_expr = "COALESCE(NULLIF(TRIM(c.fecha_envio::text), ''), c.created_at::text)"
    date_filter = _date_filter_sql(fecha_desde, fecha_hasta, params, date_expr)
    sql = f"""
        SELECT COUNT(*) AS cnt
        FROM oc_cabecera c
        INNER JOIN oc_detalle l ON l.oc_id = c.id
        WHERE (
              COALESCE(TRIM(l.itemcode_sap), '') = ''
           OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
        ){date_filter}
    """
    try:
        rows = _raw_sql(sql, params)
        return int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception as e:
        logger.error(f"[supa_repo] get_review_queue_count: {e}")
        return 0


def get_auditoria(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    tipo_oc: Optional[str] = None,
    limit: int = 200,
) -> dict:
    params_a: list = []
    params_b: list = []
    date_expr = "COALESCE(NULLIF(TRIM(fecha_envio::text), ''), created_at::text)"
    date_filter_a = _date_filter_sql(fecha_desde, fecha_hasta, params_a, date_expr)
    date_filter_b = _date_filter_sql(fecha_desde, fecha_hasta, params_b, date_expr)
    base_fields = "codigo_oc, tipo_oc, estado_mp, estado_interno, fecha_envio, nombre_organismo, total_neto, moneda"
    sql_a = f"SELECT {base_fields} FROM oc_cabecera WHERE estado_mp = 'Aceptada' AND estado_interno != 'Ingresada'{date_filter_a} ORDER BY fecha_envio DESC"
    sql_b = f"SELECT {base_fields} FROM oc_cabecera WHERE estado_interno = 'Ingresada' AND estado_mp != 'Aceptada'{date_filter_b} ORDER BY fecha_envio DESC"
    try:
        rows_a = _raw_sql(sql_a, params_a)
        rows_b = _raw_sql(sql_b, params_b)
        return {
            "aceptadas_sin_ingresar": rows_a,
            "ingresadas_sin_aceptar": rows_b,
        }
    except Exception as e:
        logger.error(f"[supa_repo] get_auditoria: {e}")
        return {"aceptadas_sin_ingresar": [], "ingresadas_sin_aceptar": []}


def _is_ready_row(row: dict) -> bool:
    return (
        (row.get("estado_interno") or "") == "Lista para SAP"
        or (
            (row.get("estado_interno") or "") != "Ingresada"
            and int(row.get("lineas_reales") or 0) > 0
            and int(row.get("lineas_bloqueadas") or 0) == 0
        )
    )


def get_control_analytics(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> dict:
    """KPIs operativos para el Centro de Control."""
    params: list = []
    date_expr_c = "COALESCE(NULLIF(TRIM(c.fecha_envio::text), ''), c.created_at::text)"

    sql = f"""
        SELECT
            c.codigo_oc,
            c.tipo_oc,
            c.estado_mp,
            c.estado_interno,
            c.fecha_envio,
            c.fecha_ingreso,
            c.created_at,
            c.total,
            c.total_neto,
            c.cantidad_lineas,
            c.responsable_ingreso_username,
            c.ingresado_por_username,
            COALESCE(c.ingreso_sap_acuerdo_global, FALSE) AS ingreso_sap_acuerdo_global,
            COALESCE(pa.requiere_revision, FALSE) AS privado_requiere_revision,
            COALESCE(pa.parser_usado, '') AS privado_parser_usado,
            COALESCE(pa.detalle_validacion, '') AS privado_detalle_validacion,
            COALESCE(ds.document_available, FALSE) AS document_available,
            COALESCE(ds.document_regenerable, FALSE) AS document_regenerable,
            COUNT(l.id) AS lineas_reales,
            COALESCE(SUM(CASE
                WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                  OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
                THEN 1 ELSE 0 END), 0) AS lineas_bloqueadas,
            COALESCE(SUM(CASE
                WHEN COALESCE(TRIM(l.itemcode_sap), '') != ''
                THEN 1 ELSE 0 END), 0) AS lineas_resueltas
        FROM oc_cabecera c
        LEFT JOIN oc_detalle l ON l.oc_id = c.id
        LEFT JOIN (
            SELECT codigo_oc,
                   BOOL_OR(requiere_revision) AS requiere_revision,
                   MAX(parser_usado) AS parser_usado,
                   MAX(detalle_validacion) AS detalle_validacion
            FROM oc_privado_auditoria
            GROUP BY codigo_oc
        ) pa ON pa.codigo_oc = c.codigo_oc
        LEFT JOIN oc_document_source ds ON ds.codigo_oc = c.codigo_oc
        GROUP BY c.codigo_oc, c.tipo_oc, c.estado_mp, c.estado_interno,
                 c.fecha_envio, c.fecha_ingreso, c.created_at, c.total, c.total_neto,
                 c.cantidad_lineas, c.responsable_ingreso_username, c.ingresado_por_username,
                 c.ingreso_sap_acuerdo_global, pa.requiere_revision, pa.parser_usado,
                 pa.detalle_validacion, ds.document_available, ds.document_regenerable
    """
    try:
        all_rows = _raw_sql(sql, [])
    except Exception as e:
        logger.error(f"[supa_repo] get_control_analytics SQL: {e}")
        return {
            "productividad_hoy": {},
            "productividad_usuarios": [],
            "aging": {},
            "funnel": [],
            "privadas": {},
            "top_blockers": [],
        }

    today = datetime.now().date().isoformat()
    now = datetime.now()

    # ── Filtrar rango seleccionado ──────────────────────────────────────────────
    selected = []
    for row in all_rows:
        received_date = _date_part(str(row.get("fecha_envio") or row.get("created_at") or ""))
        row["_received_date"] = received_date
        row["_entered_date"] = _date_part(str(row.get("fecha_ingreso") or ""))
        row["_amount"] = float(row.get("total") or row.get("total_neto") or 0.0)
        row["_blocked_lines"] = int(row.get("lineas_bloqueadas") or 0)
        row["_ready"] = _is_ready_row(row)
        in_range = True
        if fecha_desde and received_date:
            in_range = in_range and received_date >= fecha_desde
        if fecha_hasta and received_date:
            in_range = in_range and received_date <= fecha_hasta
        if in_range:
            selected.append(row)

    received_today = [r for r in all_rows if _date_part(str(r.get("fecha_envio") or r.get("created_at") or "")) == today]
    entered_today  = [r for r in all_rows if _date_part(str(r.get("fecha_ingreso") or "")) == today]
    same_day = [
        r for r in all_rows
        if _date_part(str(r.get("fecha_envio") or r.get("created_at") or "")) == today
        and _date_part(str(r.get("fecha_ingreso") or "")) == today
    ]

    productividad_hoy = {
        "fecha": today,
        "recibidas_ocs":    len(received_today),
        "recibidas_lineas": sum(int(r.get("cantidad_lineas") or r.get("lineas_reales") or 0) for r in received_today),
        "recibidas_monto":  sum(float(r.get("total") or r.get("total_neto") or 0.0) for r in received_today),
        "ingresadas_ocs":   len(entered_today),
        "ingresadas_lineas":sum(int(r.get("cantidad_lineas") or r.get("lineas_reales") or 0) for r in entered_today),
        "ingresadas_monto": sum(float(r.get("total") or r.get("total_neto") or 0.0) for r in entered_today),
        "same_day_ocs":     len(same_day),
        "same_day_monto":   sum(float(r.get("total") or r.get("total_neto") or 0.0) for r in same_day),
        "same_day_ratio_pct": _pct(len(same_day), len(received_today)),
        "throughput_pct":   _pct(len(entered_today), len(received_today)),
        "backlog_neto":     len(received_today) - len(entered_today),
        "listas_sap":       sum(1 for r in all_rows if _is_ready_row(r)),
        "bloqueadas":       sum(1 for r in all_rows if (r.get("estado_interno") or "") != "Ingresada" and int(r.get("lineas_bloqueadas") or 0) > 0),
        "aceptadas_sin_ingresar": sum(1 for r in all_rows if (r.get("estado_mp") or "") == "Aceptada" and (r.get("estado_interno") or "") != "Ingresada"),
    }

    # ── Productividad por usuario ───────────────────────────────────────────────
    user_map: dict = {}

    def get_user_bucket(username: str) -> dict:
        key = (username or "Sin responsable")
        if key not in user_map:
            user_map[key] = {
                "user_id": None,
                "username": key,
                "ocs_asignadas": 0,
                "recibidas_hoy_asignadas": 0,
                "same_day_ocs": 0,
                "same_day_ratio_pct": 0.0,
                "ingresadas_hoy": 0,
                "ingresadas_total_rango": 0,
                "lineas_ingresadas": 0,
                "monto_ingresado": 0.0,
                "privadas_ingresadas": 0,
                "acuerdos_globales_ingresados": 0,
                "backlog_pendiente": 0,
            }
        return user_map[key]

    for row in all_rows:
        received_date = _date_part(str(row.get("fecha_envio") or row.get("created_at") or ""))
        entered_date  = _date_part(str(row.get("fecha_ingreso") or ""))
        line_count    = int(row.get("cantidad_lineas") or row.get("lineas_reales") or 0)
        amount        = float(row.get("total") or row.get("total_neto") or 0.0)

        resp_username = (row.get("responsable_ingreso_username") or "").strip()
        resp_bucket = get_user_bucket(resp_username)
        if resp_username or (row.get("estado_interno") or "") != "Ingresada":
            resp_bucket["ocs_asignadas"] += 1
        if received_date == today:
            resp_bucket["recibidas_hoy_asignadas"] += 1
        if (row.get("estado_interno") or "") != "Ingresada":
            resp_bucket["backlog_pendiente"] += 1

        ingresado_username = (row.get("ingresado_por_username") or "").strip()
        if entered_date:
            actor_bucket = get_user_bucket(ingresado_username or "Sin dato")
            in_sel = True
            if fecha_desde:
                in_sel = in_sel and entered_date >= fecha_desde
            if fecha_hasta:
                in_sel = in_sel and entered_date <= fecha_hasta
            if in_sel:
                actor_bucket["ingresadas_total_rango"] += 1
                actor_bucket["lineas_ingresadas"] += line_count
                actor_bucket["monto_ingresado"] += amount
                if (row.get("tipo_oc") or "").upper() == "PRIVADA":
                    actor_bucket["privadas_ingresadas"] += 1
                if row.get("ingreso_sap_acuerdo_global"):
                    actor_bucket["acuerdos_globales_ingresados"] += 1
            if entered_date == today:
                actor_bucket["ingresadas_hoy"] += 1
            if entered_date == today and received_date == today:
                actor_bucket["same_day_ocs"] += 1

    productividad_usuarios = []
    for bucket in user_map.values():
        bucket["same_day_ratio_pct"] = _pct(bucket["same_day_ocs"], bucket["recibidas_hoy_asignadas"])
        if any(bucket[k] for k in ("ocs_asignadas","recibidas_hoy_asignadas","same_day_ocs",
                                   "ingresadas_hoy","ingresadas_total_rango","backlog_pendiente")):
            productividad_usuarios.append(bucket)
    productividad_usuarios.sort(key=lambda x: (-int(x["ingresadas_hoy"]), -int(x["ingresadas_total_rango"]), x["username"]))

    # ── Aging ───────────────────────────────────────────────────────────────────
    def summarize_bucket(predicate) -> list:
        buckets = {
            "0-24h": {"bucket": "0-24h", "cantidad_ocs": 0, "monto_total": 0.0},
            "1-2d":  {"bucket": "1-2d",  "cantidad_ocs": 0, "monto_total": 0.0},
            "3-7d":  {"bucket": "3-7d",  "cantidad_ocs": 0, "monto_total": 0.0},
            "+7d":   {"bucket": "+7d",   "cantidad_ocs": 0, "monto_total": 0.0},
        }
        for data in selected:
            if not predicate(data):
                continue
            received_dt = _parse_datetime(str(data.get("fecha_envio") or data.get("created_at") or ""))
            age_hours = ((now - received_dt).total_seconds() / 3600) if received_dt else 0
            key = "0-24h" if age_hours <= 24 else ("1-2d" if age_hours <= 48 else ("3-7d" if age_hours <= 168 else "+7d"))
            buckets[key]["cantidad_ocs"] += 1
            buckets[key]["monto_total"] += data["_amount"]
        return list(buckets.values())

    aging = {
        "listas_sap":           summarize_bucket(lambda r: r["_ready"] and r.get("estado_interno") != "Ingresada"),
        "bloqueadas":           summarize_bucket(lambda r: r.get("estado_interno") != "Ingresada" and r["_blocked_lines"] > 0),
        "aceptadas_sin_ingresar": summarize_bucket(lambda r: r.get("estado_mp") == "Aceptada" and r.get("estado_interno") != "Ingresada"),
    }

    # ── Funnel ──────────────────────────────────────────────────────────────────
    def count_stage(predicate) -> dict:
        items = [r for r in selected if predicate(r)]
        return {"cantidad_ocs": len(items), "monto_total": sum(r["_amount"] for r in items)}

    funnel = [
        {"stage": "recibidas",   "label": "Recibidas",      **count_stage(lambda r: True)},
        {"stage": "clasificadas","label": "Clasificadas",   **count_stage(lambda r: bool(r.get("tipo_oc") or r.get("cliente_sap_sugerido")))},
        {"stage": "homologadas", "label": "Homologadas",    **count_stage(lambda r: int(r.get("lineas_reales") or 0) > 0 and r["_blocked_lines"] == 0)},
        {"stage": "listas_sap",  "label": "Listas SAP",     **count_stage(lambda r: r["_ready"])},
        {"stage": "ingresadas",  "label": "Ingresadas SAP", **count_stage(lambda r: bool(r.get("fecha_ingreso")))},
        {"stage": "aceptadas_mp","label": "Aceptadas MP",   **count_stage(lambda r: r.get("estado_mp") == "Aceptada")},
    ]

    # ── OCs Privadas ────────────────────────────────────────────────────────────
    privadas_rows = [r for r in selected if (r.get("tipo_oc") or "").upper() == "PRIVADA"]
    privadas = {
        "recibidas":          len(privadas_rows),
        "requieren_revision": sum(1 for r in privadas_rows if r.get("privado_requiere_revision")),
        "parser_fallido":     sum(1 for r in privadas_rows
                                  if not (r.get("privado_parser_usado") or "").strip()
                                  or "error" in (r.get("privado_detalle_validacion") or "").lower()),
        "pdf_recuperable":    sum(1 for r in privadas_rows
                                  if r.get("document_available") and r.get("document_regenerable")),
    }

    top_blockers = get_top_blocking_products(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

    return {
        "productividad_hoy":     productividad_hoy,
        "productividad_usuarios": productividad_usuarios,
        "aging":                 aging,
        "funnel":                funnel,
        "privadas":              privadas,
        "top_blockers":          top_blockers,
    }
