"""
Repositorio para OC cabecera y detalle.
Gestiona inserciones, actualizaciones, consultas y exportaciones.
"""
import json
import logging
from datetime import datetime
from typing import Any, List, Optional, Set, Tuple

from app.db import get_connection
from app.models.orden_compra import OrdenCompra
from app.models.linea_oc import LineaOC

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------

def save_oc(oc: OrdenCompra, lineas: List[LineaOC]) -> None:
    """
    Guarda cabecera y líneas en una sola transacción.
    Si la OC ya existe, actualiza los campos de API pero conserva
    estado_interno, fecha_ingreso y notas definidos por el usuario.
    """
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        # 1. Cabecera
        conn.execute("""
            INSERT INTO oc_cabecera (
                codigo_oc, nombre_oc, codigo_estado_mp, estado_mp,
                codigo_tipo, tipo_oc, fecha_creacion, fecha_envio,
                fecha_aceptacion, fecha_cancelacion, fecha_ultima_modificacion,
                total_neto, impuestos, total, porcentaje_iva,
                descuentos, cargos, moneda,
                codigo_organismo, nombre_organismo,
                rut_unidad, codigo_unidad, nombre_unidad,
                direccion_unidad, comuna_unidad, region_unidad,
                codigo_licitacion, direccion_despacho, direccion_facturacion,
                codigo_proveedor, nombre_proveedor, rut_proveedor,
                cliente_sap_sugerido, cantidad_lineas,
                estado_interno, fecha_ingreso, notas,
                created_at, updated_at
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(codigo_oc) DO UPDATE SET
                nombre_oc                = excluded.nombre_oc,
                codigo_estado_mp         = excluded.codigo_estado_mp,
                estado_mp                = excluded.estado_mp,
                fecha_ultima_modificacion= excluded.fecha_ultima_modificacion,
                total_neto               = excluded.total_neto,
                impuestos                = excluded.impuestos,
                total                    = excluded.total,
                porcentaje_iva           = excluded.porcentaje_iva,
                descuentos               = excluded.descuentos,
                cargos                   = excluded.cargos,
                codigo_licitacion        = excluded.codigo_licitacion,
                direccion_despacho       = excluded.direccion_despacho,
                direccion_facturacion    = excluded.direccion_facturacion,
                cantidad_lineas          = excluded.cantidad_lineas,
                updated_at               = excluded.updated_at
        """, (
            oc.codigo_oc, oc.nombre_oc, oc.codigo_estado_mp, oc.estado_mp,
            oc.codigo_tipo, oc.tipo_oc, oc.fecha_creacion, oc.fecha_envio,
            oc.fecha_aceptacion, oc.fecha_cancelacion, oc.fecha_ultima_modificacion,
            oc.total_neto, oc.impuestos, oc.total, oc.porcentaje_iva,
            oc.descuentos, oc.cargos, oc.moneda,
            oc.codigo_organismo, oc.nombre_organismo,
            oc.rut_unidad, oc.codigo_unidad, oc.nombre_unidad,
            oc.direccion_unidad, oc.comuna_unidad, oc.region_unidad,
            oc.codigo_licitacion, oc.direccion_despacho, oc.direccion_facturacion,
            oc.codigo_proveedor, oc.nombre_proveedor, oc.rut_proveedor,
            oc.cliente_sap_sugerido, oc.cantidad_lineas,
            oc.estado_interno or "Nueva", oc.fecha_ingreso, oc.notas,
            now, now
        ))

        # 2. Líneas (INSERT OR REPLACE actualiza si correlativo ya existe)
        for linea in lineas:
            conn.execute("""
                INSERT INTO oc_detalle (
                    codigo_oc, correlativo, codigo_categoria, categoria,
                    codigo_producto_api, codigo_mp, producto,
                    especificacion_comprador, especificacion_proveedor,
                    cantidad, unidad, moneda, precio_neto,
                    total_cargos, total_descuentos, total_impuestos, total,
                    factor_empaque, cantidad_sap, precio_sap, sap_mode, sap_mode_origen,
                    sap_values_origen, sap_values_updated_at, sap_values_updated_by_user_id,
                    sap_values_updated_by_username, itemcode_sap, descripcion_sap, estado_homologacion,
                    created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(codigo_oc, correlativo) DO UPDATE SET
                    codigo_mp           = excluded.codigo_mp,
                    itemcode_sap        = excluded.itemcode_sap,
                    descripcion_sap     = excluded.descripcion_sap,
                    factor_empaque      = excluded.factor_empaque,
                    cantidad_sap        = CASE
                                            WHEN COALESCE(oc_detalle.sap_values_origen, '') = 'manual'
                                            THEN oc_detalle.cantidad_sap
                                            ELSE excluded.cantidad_sap
                                          END,
                    precio_sap          = CASE
                                            WHEN COALESCE(oc_detalle.sap_values_origen, '') = 'manual'
                                            THEN oc_detalle.precio_sap
                                            ELSE excluded.precio_sap
                                          END,
                    sap_mode            = excluded.sap_mode,
                    sap_mode_origen     = excluded.sap_mode_origen,
                    sap_values_origen   = CASE
                                            WHEN COALESCE(oc_detalle.sap_values_origen, '') = 'manual'
                                            THEN oc_detalle.sap_values_origen
                                            ELSE COALESCE(excluded.sap_values_origen, 'auto')
                                          END,
                    sap_values_updated_at = CASE
                                            WHEN COALESCE(oc_detalle.sap_values_origen, '') = 'manual'
                                            THEN oc_detalle.sap_values_updated_at
                                            ELSE excluded.sap_values_updated_at
                                          END,
                    sap_values_updated_by_user_id = CASE
                                            WHEN COALESCE(oc_detalle.sap_values_origen, '') = 'manual'
                                            THEN oc_detalle.sap_values_updated_by_user_id
                                            ELSE excluded.sap_values_updated_by_user_id
                                          END,
                    sap_values_updated_by_username = CASE
                                            WHEN COALESCE(oc_detalle.sap_values_origen, '') = 'manual'
                                            THEN oc_detalle.sap_values_updated_by_username
                                            ELSE excluded.sap_values_updated_by_username
                                          END,
                    estado_homologacion = excluded.estado_homologacion,
                    updated_at          = excluded.updated_at
            """, (
                linea.codigo_oc, linea.correlativo, linea.codigo_categoria,
                linea.categoria, linea.codigo_producto_api, linea.codigo_mp,
                linea.producto, linea.especificacion_comprador, linea.especificacion_proveedor,
                linea.cantidad, linea.unidad, linea.moneda, linea.precio_neto,
                linea.total_cargos, linea.total_descuentos, linea.total_impuestos, linea.total,
                linea.factor_empaque, linea.cantidad_sap, linea.precio_sap, linea.sap_mode, linea.sap_mode_origen,
                linea.sap_values_origen or "auto", linea.sap_values_updated_at,
                linea.sap_values_updated_by_user_id, linea.sap_values_updated_by_username,
                linea.itemcode_sap, linea.descripcion_sap, linea.estado_homologacion,
                now, now
            ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error guardando OC {oc.codigo_oc}: {e}")
        raise
    finally:
        conn.close()


def upsert_document_source(
    codigo_oc: str,
    *,
    source_type: str,
    source_locator: str = "",
    access_payload: Optional[dict[str, Any] | str] = None,
    snapshot_type: str = "",
    snapshot_path: str = "",
    snapshot_sha256: str = "",
    snapshot_size_bytes: int = 0,
    document_available: bool = False,
    document_regenerable: bool = False,
    last_verified_at: str = "",
) -> None:
    conn = get_connection()
    now = datetime.now().isoformat()
    payload_serialized = access_payload
    if isinstance(access_payload, (dict, list)):
        payload_serialized = json.dumps(access_payload, ensure_ascii=False)

    try:
        conn.execute(
            """
            INSERT INTO oc_document_source (
                codigo_oc, source_type, source_locator, access_payload,
                snapshot_type, snapshot_path, snapshot_sha256, snapshot_size_bytes,
                document_available, document_regenerable, last_verified_at,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(codigo_oc) DO UPDATE SET
                source_type          = excluded.source_type,
                source_locator       = excluded.source_locator,
                access_payload       = excluded.access_payload,
                snapshot_type        = excluded.snapshot_type,
                snapshot_path        = excluded.snapshot_path,
                snapshot_sha256      = excluded.snapshot_sha256,
                snapshot_size_bytes  = excluded.snapshot_size_bytes,
                document_available   = excluded.document_available,
                document_regenerable = excluded.document_regenerable,
                last_verified_at     = excluded.last_verified_at,
                updated_at           = excluded.updated_at
            """,
            (
                codigo_oc,
                source_type,
                source_locator,
                payload_serialized or "",
                snapshot_type,
                snapshot_path,
                snapshot_sha256,
                int(snapshot_size_bytes or 0),
                1 if document_available else 0,
                1 if document_regenerable else 0,
                last_verified_at or now,
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _registrar_cambio_estado(
    conn,
    codigo_oc: str,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    origen: str,
    when: str,
    actor_user_id: Optional[int] = None,
    actor_username: str = "",
) -> None:
    conn.execute("""
        INSERT INTO oc_estado_historial (
            codigo_oc, estado_anterior, estado_nuevo, origen,
            actor_user_id, actor_username, changed_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        codigo_oc,
        estado_anterior,
        estado_nuevo,
        origen,
        actor_user_id,
        actor_username or "",
        when,
        when,
        when,
    ))


def _cambiar_estado_interno(
    codigo_oc: str,
    estado_nuevo: str,
    *,
    origen: str,
    registrar_fecha_ingreso: bool = False,
    actor_user_id: Optional[int] = None,
    actor_username: str = "",
    acuerdo_global: bool = False,
) -> None:
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        row = conn.execute("""
            SELECT estado_interno, fecha_ingreso
            FROM oc_cabecera
            WHERE codigo_oc = ?
        """, (codigo_oc,)).fetchone()
        if not row:
            return

        estado_actual = (row["estado_interno"] or "Nueva").strip() or "Nueva"
        fecha_ingreso_actual = (row["fecha_ingreso"] or "").strip()
        debe_marcar_ingreso = registrar_fecha_ingreso and not fecha_ingreso_actual

        if estado_actual == estado_nuevo and not debe_marcar_ingreso:
            return

        if debe_marcar_ingreso:
            conn.execute("""
                UPDATE oc_cabecera
                SET estado_interno = ?,
                    fecha_ingreso  = COALESCE(NULLIF(fecha_ingreso, ''), ?),
                    ingresado_por_user_id = COALESCE(ingresado_por_user_id, ?),
                    ingresado_por_username = COALESCE(NULLIF(ingresado_por_username, ''), ?),
                    ingreso_sap_acuerdo_global = ?,
                    updated_at     = ?
                WHERE codigo_oc = ?
            """, (
                estado_nuevo,
                now,
                actor_user_id,
                actor_username or "",
                1 if acuerdo_global else 0,
                now,
                codigo_oc,
            ))
        elif registrar_fecha_ingreso and estado_nuevo == "Ingresada":
            conn.execute("""
                UPDATE oc_cabecera
                SET estado_interno = ?,
                    ingresado_por_user_id = COALESCE(ingresado_por_user_id, ?),
                    ingresado_por_username = COALESCE(NULLIF(ingresado_por_username, ''), ?),
                    ingreso_sap_acuerdo_global = CASE
                        WHEN ingreso_sap_acuerdo_global IS NULL OR ingreso_sap_acuerdo_global = 0 THEN ?
                        ELSE ingreso_sap_acuerdo_global
                    END,
                    updated_at     = ?
                WHERE codigo_oc = ?
            """, (
                estado_nuevo,
                actor_user_id,
                actor_username or "",
                1 if acuerdo_global else 0,
                now,
                codigo_oc,
            ))
        else:
            conn.execute("""
                UPDATE oc_cabecera
                SET estado_interno = ?,
                    updated_at     = ?
                WHERE codigo_oc = ?
            """, (estado_nuevo, now, codigo_oc))

        if estado_actual != estado_nuevo:
            _registrar_cambio_estado(
                conn,
                codigo_oc,
                estado_actual,
                estado_nuevo,
                origen,
                now,
                actor_user_id=actor_user_id,
                actor_username=actor_username,
            )

        conn.commit()
    finally:
        conn.close()


def marcar_ingresada(
    codigo_oc: str,
    origen: str = "boton_ingresar",
    *,
    actor_user_id: Optional[int] = None,
    actor_username: str = "",
    acuerdo_global: bool = False,
) -> None:
    _cambiar_estado_interno(
        codigo_oc,
        "Ingresada",
        origen=origen,
        registrar_fecha_ingreso=True,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        acuerdo_global=acuerdo_global,
    )


def actualizar_estado(
    codigo_oc: str,
    estado: str,
    origen: str = "selector_estado",
    *,
    actor_user_id: Optional[int] = None,
    actor_username: str = "",
) -> None:
    _cambiar_estado_interno(
        codigo_oc,
        estado,
        origen=origen,
        registrar_fecha_ingreso=(estado == "Ingresada"),
        actor_user_id=actor_user_id,
        actor_username=actor_username,
    )


def asignar_responsable_ingreso(
    codigo_oc: str,
    user_id: Optional[int],
    username: str = "",
) -> None:
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute(
            """
            UPDATE oc_cabecera
            SET responsable_ingreso_user_id = ?,
                responsable_ingreso_username = ?,
                updated_at = ?
            WHERE codigo_oc = ?
            """,
            (user_id, username or "", now, codigo_oc),
        )
        conn.commit()
    finally:
        conn.close()


def guardar_notas(codigo_oc: str, notas: str) -> None:
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute("""
            UPDATE oc_cabecera SET notas = ?, updated_at = ? WHERE codigo_oc = ?
        """, (notas, now, codigo_oc))
        conn.commit()
    finally:
        conn.close()


def actualizar_estado_mp_oc(
    codigo_oc: str,
    codigo_estado_mp: int,
    estado_mp: str = "",
) -> bool:
    """Actualiza solo el estado de portal para una OC ya existente."""
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        if estado_mp:
            result = conn.execute(
                """
                UPDATE oc_cabecera
                SET estado_mp = ?,
                    codigo_estado_mp = ?,
                    fecha_ultima_modificacion = ?,
                    updated_at = ?
                WHERE codigo_oc = ?
                """,
                (estado_mp, codigo_estado_mp, now, now, codigo_oc),
            )
        else:
            result = conn.execute(
                """
                UPDATE oc_cabecera
                SET codigo_estado_mp = ?,
                    fecha_ultima_modificacion = ?,
                    updated_at = ?
                WHERE codigo_oc = ?
                """,
                (codigo_estado_mp, now, now, codigo_oc),
            )

        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()


def actualizar_campos_publicos(
    codigo_oc: str,
    *,
    codigo_licitacion: Optional[str] = None,
    direccion_despacho: Optional[str] = None,
    direccion_facturacion: Optional[str] = None,
) -> None:
    updates = []
    params = []
    if codigo_licitacion is not None:
        updates.append("codigo_licitacion = ?")
        params.append(codigo_licitacion)
    if direccion_despacho is not None:
        updates.append("direccion_despacho = ?")
        params.append(direccion_despacho)
    if direccion_facturacion is not None:
        updates.append("direccion_facturacion = ?")
        params.append(direccion_facturacion)
    if not updates:
        return

    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        updates.append("updated_at = ?")
        params.append(now)
        params.append(codigo_oc)
        conn.execute(
            f"""
            UPDATE oc_cabecera
            SET {", ".join(updates)}
            WHERE codigo_oc = ?
            """,
            params,
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

def get_existing_codes() -> Set[str]:
    """Retorna el conjunto de codigo_oc existentes (para evitar re-descarga)."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT codigo_oc FROM oc_cabecera").fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


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
) -> List[OrdenCompra]:
    """Retorna lista de OC según filtros opcionales. estado/estado_mp/tipo_oc/holding pueden ser str o List[str]."""
    conn = get_connection()
    try:
        sql = "SELECT * FROM oc_cabecera WHERE 1=1"
        params = []

        def _add_in_filter(field: str, value) -> None:
            if not value:
                return
            values = [value] if isinstance(value, str) else list(value)
            values = [v for v in values if v and v != "Todos"]
            if not values:
                return
            placeholders = ",".join("?" * len(values))
            nonlocal sql
            sql += f" AND {field} IN ({placeholders})"
            params.extend(values)

        _add_in_filter("estado_interno", estado)
        _add_in_filter("estado_mp", estado_mp)
        _add_in_filter("tipo_oc", tipo_oc)
        _add_in_filter("codigo_organismo", holding)
        if responsable:
            values = [responsable] if isinstance(responsable, str) else list(responsable)
            values = [v for v in values if v and v != "Todos"]
            if values:
                clauses = []
                normal_values = []
                for value in values:
                    if value == "__sin_responsable__":
                        clauses.append("COALESCE(TRIM(responsable_ingreso_username), '') = ''")
                    else:
                        normal_values.append(value)
                if normal_values:
                    placeholders = ",".join("?" * len(normal_values))
                    clauses.append(f"responsable_ingreso_username IN ({placeholders})")
                    params.extend(normal_values)
                if clauses:
                    sql += f" AND ({' OR '.join(clauses)})"
        if fecha_desde:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) <= DATE(?)"
            params.append(fecha_hasta)
        if fecha_ingreso_desde:
            sql += " AND DATE(fecha_ingreso) >= DATE(?)"
            params.append(fecha_ingreso_desde)
        if fecha_ingreso_hasta:
            sql += " AND DATE(fecha_ingreso) <= DATE(?)"
            params.append(fecha_ingreso_hasta)
        if busqueda:
            sql += " AND (codigo_oc LIKE ? OR nombre_organismo LIKE ? OR cliente_sap_sugerido LIKE ?)"
            like = f"%{busqueda}%"
            params.extend([like, like, like])
        sql += " ORDER BY COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at) DESC"

        rows = conn.execute(sql, params).fetchall()
        return [_row_to_oc(r) for r in rows]
    finally:
        conn.close()


def get_distinct_estados_mp() -> List[str]:
    """Retorna los valores únicos de estado_mp presentes en la BD."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT estado_mp FROM oc_cabecera "
            "WHERE estado_mp IS NOT NULL AND estado_mp != '' "
            "ORDER BY estado_mp"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def get_distinct_tipos() -> List[str]:
    """Retorna los valores únicos de tipo_oc presentes en la BD."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT tipo_oc FROM oc_cabecera "
            "WHERE tipo_oc IS NOT NULL AND tipo_oc != '' "
            "ORDER BY tipo_oc"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def get_holdings_map() -> dict:
    """Retorna dict {holding_id: nombre} desde la tabla holdings."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nombre FROM holdings WHERE activo = 1"
        ).fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


def get_distinct_holdings() -> List[dict]:
    """Retorna los holdings presentes en OCs privadas, con id y nombre."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT h.id, h.nombre
            FROM holdings h
            INNER JOIN oc_cabecera o ON h.id = o.codigo_organismo
            WHERE o.tipo_oc = 'PRIVADA'
            GROUP BY h.id, h.nombre
            ORDER BY h.nombre
        """).fetchall()
        return [{"id": r[0], "nombre": r[1]} for r in rows]
    finally:
        conn.close()


def get_oc(codigo_oc: str) -> Optional[OrdenCompra]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM oc_cabecera WHERE codigo_oc = ?", (codigo_oc,)
        ).fetchone()
        return _row_to_oc(row) if row else None
    finally:
        conn.close()


def get_document_source(codigo_oc: str) -> Optional[dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM oc_document_source
            WHERE codigo_oc = ?
            """,
            (codigo_oc,),
        ).fetchone()
        if not row:
            return None

        data = dict(row)
        payload = data.get("access_payload") or ""
        if payload:
            try:
                data["access_payload"] = json.loads(payload)
            except Exception:
                pass
        data["document_available"] = bool(data.get("document_available"))
        data["document_regenerable"] = bool(data.get("document_regenerable"))
        return data
    finally:
        conn.close()


def get_estado_historial(codigo_oc: str, limit: int = 10) -> List[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                id,
                codigo_oc,
                estado_anterior,
                estado_nuevo,
                origen,
                actor_user_id,
                actor_username,
                changed_at
            FROM oc_estado_historial
            WHERE codigo_oc = ?
            ORDER BY datetime(changed_at) DESC, id DESC
            LIMIT ?
        """, (codigo_oc, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_lineas(codigo_oc: str) -> List[LineaOC]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM oc_detalle
            WHERE codigo_oc = ?
            ORDER BY id ASC, correlativo ASC
            """,
            (codigo_oc,)
        ).fetchall()
        return [_row_to_linea(r) for r in rows]
    finally:
        conn.close()


def get_stats() -> dict:
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM oc_cabecera").fetchone()[0]
        sin_homolog = conn.execute("""
            SELECT COUNT(DISTINCT codigo_oc) FROM oc_detalle
            WHERE estado_homologacion != 'homologado'
        """).fetchone()[0]
        ingresadas = conn.execute(
            "SELECT COUNT(*) FROM oc_cabecera WHERE estado_interno='Ingresada'"
        ).fetchone()[0]
        return {"total": total, "sin_homolog": sin_homolog, "ingresadas": ingresadas}
    finally:
        conn.close()


def get_analytics_summary(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> dict:
    conn = get_connection()
    try:
        sql = """
            SELECT
                COUNT(DISTINCT c.codigo_oc) AS total_ocs,
                COUNT(l.correlativo) AS total_lineas,
                COALESCE(SUM(l.total), 0) AS monto_total,
                COALESCE(SUM(
                    CASE
                        WHEN COALESCE(TRIM(l.itemcode_sap), '') != '' THEN COALESCE(l.total, 0)
                        ELSE 0
                    END
                ), 0) AS monto_resuelto,
                COALESCE(SUM(
                    CASE
                        WHEN COALESCE(TRIM(l.itemcode_sap), '') != '' THEN 1
                        ELSE 0
                    END
                ), 0) AS lineas_resueltas,
                COALESCE(SUM(
                    CASE
                        WHEN COALESCE(l.estado_homologacion, '') = 'manual' THEN 1
                        ELSE 0
                    END
                ), 0) AS lineas_manuales,
                COALESCE(SUM(
                    CASE
                        WHEN COALESCE(l.estado_homologacion, '') = 'sugerido' THEN 1
                        ELSE 0
                    END
                ), 0) AS lineas_sugeridas,
                COALESCE(SUM(
                    CASE
                        WHEN COALESCE(l.estado_homologacion, '') = 'homologado' THEN 1
                        ELSE 0
                    END
                ), 0) AS lineas_homologadas,
                COALESCE(SUM(
                    CASE
                        WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                          OR COALESCE(l.estado_homologacion, 'pendiente') = 'pendiente'
                        THEN 1
                        ELSE 0
                    END
                ), 0) AS lineas_pendientes,
                COUNT(DISTINCT CASE
                    WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                      OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
                    THEN c.codigo_oc
                    ELSE NULL
                END) AS ocs_por_revisar,
                COALESCE(SUM(
                    CASE
                        WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                         AND (COALESCE(TRIM(l.especificacion_comprador), '') != ''
                              OR COALESCE(TRIM(l.producto), '') != '')
                        THEN 1 ELSE 0
                    END
                ), 0) AS pendientes_con_texto,
                COALESCE(SUM(
                    CASE
                        WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                         AND COALESCE(TRIM(l.especificacion_comprador), '') = ''
                         AND COALESCE(TRIM(l.producto), '') = ''
                        THEN 1 ELSE 0
                    END
                ), 0) AS pendientes_sin_texto
            FROM oc_cabecera c
            LEFT JOIN oc_detalle l ON l.codigo_oc = c.codigo_oc
            WHERE 1=1
        """
        params = []

        if fecha_desde:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) <= DATE(?)"
            params.append(fecha_hasta)

        row = conn.execute(sql, params).fetchone()
        total_lineas = int(row["total_lineas"] or 0)
        lineas_resueltas = int(row["lineas_resueltas"] or 0)
        monto_total = float(row["monto_total"] or 0.0)
        monto_resuelto = float(row["monto_resuelto"] or 0.0)

        return {
            "total_ocs": int(row["total_ocs"] or 0),
            "total_lineas": total_lineas,
            "lineas_resueltas": lineas_resueltas,
            "lineas_pendientes": int(row["lineas_pendientes"] or 0),
            "lineas_manuales": int(row["lineas_manuales"] or 0),
            "lineas_sugeridas": int(row["lineas_sugeridas"] or 0),
            "lineas_homologadas": int(row["lineas_homologadas"] or 0),
            "ocs_por_revisar": int(row["ocs_por_revisar"] or 0),
            "pendientes_con_texto": int(row["pendientes_con_texto"] or 0),
            "pendientes_sin_texto": int(row["pendientes_sin_texto"] or 0),
            "monto_total": monto_total,
            "monto_resuelto": monto_resuelto,
            "cobertura_lineas_pct": round((lineas_resueltas / total_lineas) * 100, 1) if total_lineas else 0.0,
            "cobertura_monto_pct": round((monto_resuelto / monto_total) * 100, 1) if monto_total else 0.0,
        }
    finally:
        conn.close()


def get_received_by_day(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> list[dict]:
    conn = get_connection()
    try:
        sql = """
            SELECT
                DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) AS fecha,
                COUNT(*) AS cantidad_ocs,
                COALESCE(SUM(COALESCE(total, total_neto, 0)), 0) AS monto_total
            FROM oc_cabecera
            WHERE COALESCE(NULLIF(TRIM(fecha_envio), ''), NULLIF(TRIM(created_at), ''), '') != ''
        """
        params = []

        if fecha_desde:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) <= DATE(?)"
            params.append(fecha_hasta)

        sql += """
            GROUP BY DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at))
            ORDER BY DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) ASC
        """
        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "fecha": row["fecha"] or "",
                "cantidad_ocs": int(row["cantidad_ocs"] or 0),
                "monto_total": float(row["monto_total"] or 0.0),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_entered_by_day(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> list[dict]:
    conn = get_connection()
    try:
        sql = """
            SELECT
                DATE(fecha_ingreso) AS fecha,
                COUNT(*) AS cantidad_ocs,
                COALESCE(SUM(COALESCE(total, total_neto, 0)), 0) AS monto_total
            FROM oc_cabecera
            WHERE COALESCE(TRIM(fecha_ingreso), '') != ''
        """
        params = []

        if fecha_desde:
            sql += " AND DATE(fecha_ingreso) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(fecha_ingreso) <= DATE(?)"
            params.append(fecha_hasta)

        sql += """
            GROUP BY DATE(fecha_ingreso)
            ORDER BY DATE(fecha_ingreso) ASC
        """
        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "fecha": row["fecha"] or "",
                "cantidad_ocs": int(row["cantidad_ocs"] or 0),
                "monto_total": float(row["monto_total"] or 0.0),
            }
            for row in rows
        ]
    finally:
        conn.close()


def _date_part(value: str) -> str:
    return (value or "").strip()[:10]


def _parse_datetime(value: str) -> Optional[datetime]:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _pct(numerator: int | float, denominator: int | float) -> float:
    return round((float(numerator) / float(denominator)) * 100, 1) if denominator else 0.0


def get_control_analytics(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> dict:
    """
    KPIs operativos para el Centro de Control.
    Se calcula por OC para evitar que los JOIN de lineas dupliquen montos.
    """
    conn = get_connection()
    today = datetime.now().date().isoformat()
    now = datetime.now()
    try:
        rows = conn.execute(
            """
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
                c.responsable_ingreso_user_id,
                c.responsable_ingreso_username,
                c.ingresado_por_user_id,
                c.ingresado_por_username,
                COALESCE(c.ingreso_sap_acuerdo_global, 0) AS ingreso_sap_acuerdo_global,
                COALESCE(pa.requiere_revision, 0) AS privado_requiere_revision,
                COALESCE(pa.parser_usado, '') AS privado_parser_usado,
                COALESCE(pa.detalle_validacion, '') AS privado_detalle_validacion,
                COALESCE(ds.document_available, 0) AS document_available,
                COALESCE(ds.document_regenerable, 0) AS document_regenerable,
                COUNT(l.id) AS lineas_reales,
                COALESCE(SUM(CASE
                    WHEN COALESCE(TRIM(l.itemcode_sap), '') = ''
                      OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
                    THEN 1 ELSE 0
                END), 0) AS lineas_bloqueadas,
                COALESCE(SUM(CASE
                    WHEN COALESCE(TRIM(l.itemcode_sap), '') != ''
                    THEN 1 ELSE 0
                END), 0) AS lineas_resueltas
            FROM oc_cabecera c
            LEFT JOIN oc_detalle l ON l.codigo_oc = c.codigo_oc
            LEFT JOIN (
                SELECT
                    codigo_oc,
                    MAX(requiere_revision) AS requiere_revision,
                    MAX(parser_usado) AS parser_usado,
                    MAX(detalle_validacion) AS detalle_validacion
                FROM oc_privado_auditoria
                GROUP BY codigo_oc
            ) pa ON pa.codigo_oc = c.codigo_oc
            LEFT JOIN oc_document_source ds ON ds.codigo_oc = c.codigo_oc
            GROUP BY c.codigo_oc
            """
        ).fetchall()

        selected = []
        for row in rows:
            data = dict(row)
            received_date = _date_part(data.get("fecha_envio") or data.get("created_at") or "")
            data["_received_date"] = received_date
            data["_entered_date"] = _date_part(data.get("fecha_ingreso") or "")
            data["_line_count"] = int(data.get("cantidad_lineas") or data.get("lineas_reales") or 0)
            data["_amount"] = float(data.get("total") or data.get("total_neto") or 0.0)
            data["_blocked_lines"] = int(data.get("lineas_bloqueadas") or 0)
            data["_ready"] = (
                (data.get("estado_interno") or "") == "Lista para SAP"
                or (
                    (data.get("estado_interno") or "") != "Ingresada"
                    and int(data.get("lineas_reales") or 0) > 0
                    and int(data.get("lineas_bloqueadas") or 0) == 0
                )
            )
            in_range = True
            if fecha_desde and received_date:
                in_range = in_range and received_date >= fecha_desde
            if fecha_hasta and received_date:
                in_range = in_range and received_date <= fecha_hasta
            if in_range:
                selected.append(data)

        received_today = [r for r in rows if _date_part(r["fecha_envio"] or r["created_at"] or "") == today]
        entered_today = [r for r in rows if _date_part(r["fecha_ingreso"] or "") == today]
        same_day = [
            r for r in rows
            if _date_part(r["fecha_envio"] or r["created_at"] or "") == today
            and _date_part(r["fecha_ingreso"] or "") == today
        ]

        productividad_hoy = {
            "fecha": today,
            "recibidas_ocs": len(received_today),
            "recibidas_lineas": sum(int(r["cantidad_lineas"] or r["lineas_reales"] or 0) for r in received_today),
            "recibidas_monto": sum(float(r["total"] or r["total_neto"] or 0.0) for r in received_today),
            "ingresadas_ocs": len(entered_today),
            "ingresadas_lineas": sum(int(r["cantidad_lineas"] or r["lineas_reales"] or 0) for r in entered_today),
            "ingresadas_monto": sum(float(r["total"] or r["total_neto"] or 0.0) for r in entered_today),
            "same_day_ocs": len(same_day),
            "same_day_monto": sum(float(r["total"] or r["total_neto"] or 0.0) for r in same_day),
            "same_day_ratio_pct": _pct(len(same_day), len(received_today)),
            "throughput_pct": _pct(len(entered_today), len(received_today)),
            "backlog_neto": len(received_today) - len(entered_today),
            "listas_sap": sum(1 for r in rows if dict(r).get("estado_interno") != "Ingresada" and _is_ready_row(dict(r))),
            "bloqueadas": sum(1 for r in rows if (r["estado_interno"] or "") != "Ingresada" and int(r["lineas_bloqueadas"] or 0) > 0),
            "aceptadas_sin_ingresar": sum(1 for r in rows if (r["estado_mp"] or "") == "Aceptada" and (r["estado_interno"] or "") != "Ingresada"),
        }

        user_map: dict[tuple[Optional[int], str], dict] = {}

        def get_user_bucket(user_id: Optional[int], username: str) -> dict:
            clean_username = (username or "").strip()
            key = (user_id, clean_username or "Sin responsable")
            if key not in user_map:
                user_map[key] = {
                    "user_id": user_id,
                    "username": clean_username or "Sin responsable",
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

        for row in rows:
            data = dict(row)
            received_date = _date_part(data.get("fecha_envio") or data.get("created_at") or "")
            entered_date = _date_part(data.get("fecha_ingreso") or "")
            line_count = int(data.get("cantidad_lineas") or data.get("lineas_reales") or 0)
            amount = float(data.get("total") or data.get("total_neto") or 0.0)

            resp_id = data.get("responsable_ingreso_user_id")
            resp_username = data.get("responsable_ingreso_username") or ""
            resp_bucket = get_user_bucket(resp_id, resp_username)
            if resp_username:
                resp_bucket["ocs_asignadas"] += 1
            elif (data.get("estado_interno") or "") != "Ingresada":
                resp_bucket["ocs_asignadas"] += 1
            if received_date == today:
                resp_bucket["recibidas_hoy_asignadas"] += 1
            if (data.get("estado_interno") or "") != "Ingresada":
                resp_bucket["backlog_pendiente"] += 1

            ingresado_username = data.get("ingresado_por_username") or ""
            ingresado_id = data.get("ingresado_por_user_id")
            if entered_date:
                actor_bucket = get_user_bucket(ingresado_id, ingresado_username or "Sin dato")
                in_selected_entered_range = True
                if fecha_desde:
                    in_selected_entered_range = in_selected_entered_range and entered_date >= fecha_desde
                if fecha_hasta:
                    in_selected_entered_range = in_selected_entered_range and entered_date <= fecha_hasta
                if in_selected_entered_range:
                    actor_bucket["ingresadas_total_rango"] += 1
                    actor_bucket["lineas_ingresadas"] += line_count
                    actor_bucket["monto_ingresado"] += amount
                    if (data.get("tipo_oc") or "").upper() == "PRIVADA":
                        actor_bucket["privadas_ingresadas"] += 1
                    if int(data.get("ingreso_sap_acuerdo_global") or 0):
                        actor_bucket["acuerdos_globales_ingresados"] += 1
                if entered_date == today:
                    actor_bucket["ingresadas_hoy"] += 1
                if entered_date == today and received_date == today:
                    actor_bucket["same_day_ocs"] += 1

        productividad_usuarios = []
        for bucket in user_map.values():
            denominator = bucket["recibidas_hoy_asignadas"]
            bucket["same_day_ratio_pct"] = _pct(bucket["same_day_ocs"], denominator)
            if any(
                bucket[key]
                for key in (
                    "ocs_asignadas",
                    "recibidas_hoy_asignadas",
                    "same_day_ocs",
                    "ingresadas_hoy",
                    "ingresadas_total_rango",
                    "backlog_pendiente",
                )
            ):
                productividad_usuarios.append(bucket)

        productividad_usuarios.sort(
            key=lambda item: (
                -int(item["ingresadas_hoy"]),
                -int(item["ingresadas_total_rango"]),
                item["username"],
            )
        )

        def summarize_bucket(predicate) -> list[dict]:
            buckets = {
                "0-24h": {"bucket": "0-24h", "cantidad_ocs": 0, "monto_total": 0.0},
                "1-2d": {"bucket": "1-2d", "cantidad_ocs": 0, "monto_total": 0.0},
                "3-7d": {"bucket": "3-7d", "cantidad_ocs": 0, "monto_total": 0.0},
                "+7d": {"bucket": "+7d", "cantidad_ocs": 0, "monto_total": 0.0},
            }
            for data in selected:
                if not predicate(data):
                    continue
                received_dt = _parse_datetime(data.get("fecha_envio") or data.get("created_at") or "")
                age_hours = ((now - received_dt).total_seconds() / 3600) if received_dt else 0
                if age_hours <= 24:
                    key = "0-24h"
                elif age_hours <= 48:
                    key = "1-2d"
                elif age_hours <= 168:
                    key = "3-7d"
                else:
                    key = "+7d"
                buckets[key]["cantidad_ocs"] += 1
                buckets[key]["monto_total"] += data["_amount"]
            return list(buckets.values())

        aging = {
            "listas_sap": summarize_bucket(lambda r: r["_ready"] and r.get("estado_interno") != "Ingresada"),
            "bloqueadas": summarize_bucket(lambda r: r.get("estado_interno") != "Ingresada" and r["_blocked_lines"] > 0),
            "aceptadas_sin_ingresar": summarize_bucket(
                lambda r: r.get("estado_mp") == "Aceptada" and r.get("estado_interno") != "Ingresada"
            ),
        }

        def count_stage(predicate) -> dict:
            items = [r for r in selected if predicate(r)]
            return {
                "cantidad_ocs": len(items),
                "monto_total": sum(r["_amount"] for r in items),
            }

        funnel_defs = [
            ("recibidas", "Recibidas", lambda r: True),
            ("clasificadas", "Clasificadas", lambda r: bool(r.get("tipo_oc") or r.get("cliente_sap_sugerido"))),
            ("homologadas", "Homologadas", lambda r: int(r.get("lineas_reales") or 0) > 0 and r["_blocked_lines"] == 0),
            ("listas_sap", "Listas SAP", lambda r: r["_ready"]),
            ("ingresadas", "Ingresadas SAP", lambda r: bool(r.get("fecha_ingreso"))),
            ("aceptadas_mp", "Aceptadas MP", lambda r: r.get("estado_mp") == "Aceptada"),
        ]
        funnel = [
            {"stage": stage, "label": label, **count_stage(predicate)}
            for stage, label, predicate in funnel_defs
        ]

        privadas_rows = [r for r in selected if (r.get("tipo_oc") or "").upper() == "PRIVADA"]
        privadas = {
            "recibidas": len(privadas_rows),
            "requieren_revision": sum(1 for r in privadas_rows if int(r.get("privado_requiere_revision") or 0)),
            "parser_fallido": sum(
                1
                for r in privadas_rows
                if not (r.get("privado_parser_usado") or "").strip()
                or "error" in (r.get("privado_detalle_validacion") or "").lower()
            ),
            "pdf_recuperable": sum(
                1
                for r in privadas_rows
                if int(r.get("document_available") or 0) and int(r.get("document_regenerable") or 0)
            ),
        }

        top_blockers = get_top_blocking_products(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

        return {
            "productividad_hoy": productividad_hoy,
            "productividad_usuarios": productividad_usuarios,
            "aging": aging,
            "funnel": funnel,
            "privadas": privadas,
            "top_blockers": top_blockers,
        }
    finally:
        conn.close()


def _is_ready_row(row: dict) -> bool:
    return (
        (row.get("estado_interno") or "") == "Lista para SAP"
        or (
            (row.get("estado_interno") or "") != "Ingresada"
            and int(row.get("lineas_reales") or 0) > 0
            and int(row.get("lineas_bloqueadas") or 0) == 0
        )
    )


def get_top_blocking_products(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    conn = get_connection()
    try:
        sql = """
            SELECT
                COALESCE(NULLIF(TRIM(l.especificacion_comprador), ''), NULLIF(TRIM(l.producto), ''), 'Sin descripcion') AS label,
                COUNT(*) AS cantidad_lineas,
                COUNT(DISTINCT c.codigo_oc) AS cantidad_ocs,
                COALESCE(SUM(COALESCE(l.total, 0)), 0) AS monto_total
            FROM oc_cabecera c
            INNER JOIN oc_detalle l ON l.codigo_oc = c.codigo_oc
            WHERE (
                    COALESCE(TRIM(l.itemcode_sap), '') = ''
                 OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
            )
        """
        params = []
        if fecha_desde:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) <= DATE(?)"
            params.append(fecha_hasta)
        sql += """
            GROUP BY label
            ORDER BY cantidad_lineas DESC, monto_total DESC
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "label": row["label"] or "Sin descripcion",
                "cantidad_lineas": int(row["cantidad_lineas"] or 0),
                "cantidad_ocs": int(row["cantidad_ocs"] or 0),
                "monto_total": float(row["monto_total"] or 0.0),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_top_clients_by_amount(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 8,
) -> list[dict]:
    conn = get_connection()
    try:
        sql = """
            SELECT
                COALESCE(NULLIF(TRIM(cliente_sap_sugerido), ''), 'Sin cliente SAP') AS label,
                COUNT(*) AS cantidad_ocs,
                COALESCE(SUM(COALESCE(total, total_neto, 0)), 0) AS monto_total
            FROM oc_cabecera
            WHERE 1=1
        """
        params = []

        if fecha_desde:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) <= DATE(?)"
            params.append(fecha_hasta)

        sql += """
            GROUP BY COALESCE(NULLIF(TRIM(cliente_sap_sugerido), ''), 'Sin cliente SAP')
            ORDER BY monto_total DESC, cantidad_ocs DESC, label ASC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "label": row["label"] or "Sin cliente SAP",
                "cantidad_ocs": int(row["cantidad_ocs"] or 0),
                "monto_total": float(row["monto_total"] or 0.0),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_top_buyers_by_amount(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 8,
) -> list[dict]:
    conn = get_connection()
    try:
        sql = """
            SELECT
                COALESCE(NULLIF(TRIM(nombre_organismo), ''), 'Sin comprador') AS label,
                COUNT(*) AS cantidad_ocs,
                COALESCE(SUM(COALESCE(total, total_neto, 0)), 0) AS monto_total
            FROM oc_cabecera
            WHERE 1=1
        """
        params = []

        if fecha_desde:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) <= DATE(?)"
            params.append(fecha_hasta)

        sql += """
            GROUP BY COALESCE(NULLIF(TRIM(nombre_organismo), ''), 'Sin comprador')
            ORDER BY monto_total DESC, cantidad_ocs DESC, label ASC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "label": row["label"] or "Sin comprador",
                "cantidad_ocs": int(row["cantidad_ocs"] or 0),
                "monto_total": float(row["monto_total"] or 0.0),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_review_queue(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    conn = get_connection()
    try:
        sql = """
            SELECT
                c.codigo_oc,
                c.fecha_envio,
                c.tipo_oc,
                c.nombre_organismo,
                c.cliente_sap_sugerido,
                c.estado_interno,
                c.rut_unidad,
                l.correlativo,
                l.producto,
                l.especificacion_comprador,
                l.cantidad,
                l.total,
                l.itemcode_sap,
                l.descripcion_sap,
                l.estado_homologacion
            FROM oc_cabecera c
            INNER JOIN oc_detalle l ON l.codigo_oc = c.codigo_oc
            WHERE 1=1
              AND (
                    COALESCE(TRIM(l.itemcode_sap), '') = ''
                 OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
              )
        """
        params = []

        if fecha_desde:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) <= DATE(?)"
            params.append(fecha_hasta)

        sql += """
            ORDER BY
                CASE
                    WHEN COALESCE(TRIM(l.itemcode_sap), '') = '' THEN 0
                    WHEN COALESCE(l.estado_homologacion, '') = 'manual' THEN 1
                    ELSE 2
                END,
                DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) DESC,
                c.codigo_oc DESC,
                l.correlativo ASC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_auditoria(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> dict:
    """
    Retorna dos grupos de OCs con discrepancias entre estado_mp y estado_interno:
    - aceptadas_sin_ingresar: estado_mp='Aceptada' pero estado_interno != 'Ingresada'
    - ingresadas_sin_aceptar: estado_interno='Ingresada' pero estado_mp != 'Aceptada'
    """
    conn = get_connection()
    try:
        base_fields = """
            codigo_oc, tipo_oc, estado_mp, estado_interno,
            fecha_envio, nombre_organismo, total_neto, moneda
        """
        date_filter = ""
        date_params: list = []
        if fecha_desde:
            date_filter += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) >= DATE(?)"
            date_params.append(fecha_desde)
        if fecha_hasta:
            date_filter += " AND DATE(COALESCE(NULLIF(TRIM(fecha_envio), ''), created_at)) <= DATE(?)"
            date_params.append(fecha_hasta)

        rows_a = conn.execute(
            f"SELECT {base_fields} FROM oc_cabecera "
            f"WHERE estado_mp = 'Aceptada' AND estado_interno != 'Ingresada'"
            f"{date_filter} ORDER BY fecha_envio DESC",
            date_params,
        ).fetchall()

        rows_b = conn.execute(
            f"SELECT {base_fields} FROM oc_cabecera "
            f"WHERE estado_interno = 'Ingresada' AND estado_mp != 'Aceptada'"
            f"{date_filter} ORDER BY fecha_envio DESC",
            date_params,
        ).fetchall()

        return {
            "aceptadas_sin_ingresar": [dict(r) for r in rows_a],
            "ingresadas_sin_aceptar": [dict(r) for r in rows_b],
        }
    finally:
        conn.close()


def get_review_queue_count(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> int:
    """Total exacto de lineas en la cola de revision, sin limite."""
    conn = get_connection()
    try:
        sql = """
            SELECT COUNT(*) AS cnt
            FROM oc_cabecera c
            INNER JOIN oc_detalle l ON l.codigo_oc = c.codigo_oc
            WHERE 1=1
              AND (
                    COALESCE(TRIM(l.itemcode_sap), '') = ''
                 OR COALESCE(l.estado_homologacion, 'pendiente') IN ('pendiente', 'manual')
              )
        """
        params = []
        if fecha_desde:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(COALESCE(NULLIF(TRIM(c.fecha_envio), ''), c.created_at)) <= DATE(?)"
            params.append(fecha_hasta)
        row = conn.execute(sql, params).fetchone()
        return int(row["cnt"] or 0)
    finally:
        conn.close()


def asignar_itemcode_linea(
    codigo_oc: str,
    correlativo: int,
    itemcode_sap: str,
    descripcion_sap: str = "",
    origen: str = "manual",
) -> None:
    _ESTADOS_VALIDOS = {"homologado", "sugerido", "manual"}
    estado = origen if origen in _ESTADOS_VALIDOS else "manual"
    from app.services.sap_mode_service import assign_itemcode_with_mode

    assign_itemcode_with_mode(
        codigo_oc=codigo_oc,
        correlativo=correlativo,
        itemcode_sap=itemcode_sap,
        descripcion_sap=descripcion_sap,
        estado_homologacion=estado,
    )
    _registrar_aprendizaje_licitacion(
        codigo_oc=codigo_oc,
        correlativo=correlativo,
        itemcode_sap=itemcode_sap,
        descripcion_sap=descripcion_sap,
    )


def limpiar_asignacion_linea(codigo_oc: str, correlativo: int) -> None:
    from app.services.sap_mode_service import clear_itemcode_with_mode

    clear_itemcode_with_mode(codigo_oc, correlativo)


def _registrar_aprendizaje_licitacion(
    *,
    codigo_oc: str,
    correlativo: int,
    itemcode_sap: str,
    descripcion_sap: str = "",
) -> None:
    if not itemcode_sap:
        return

    try:
        from app.repositories.licitaciones_repo import upsert_from_assignment

        oc = get_oc(codigo_oc)
        if not oc:
            return

        linea = next(
            (item for item in get_lineas(codigo_oc) if item.correlativo == correlativo),
            None,
        )
        if not linea:
            return

        descripcion_comprador = (
            (linea.especificacion_comprador or "").strip()
            or (linea.producto or "").strip()
        )
        if not descripcion_comprador:
            return

        upsert_from_assignment(
            descripcion_comprador=descripcion_comprador,
            itemcode_sap=itemcode_sap,
            rut_comprador=oc.rut_unidad or "",
            descripcion_nemo=descripcion_sap or "",
        )
    except Exception as e:
        logger.warning(
            f"No se pudo registrar aprendizaje de licitacion para {codigo_oc}/{correlativo}: {e}"
        )


# ---------------------------------------------------------------------------
# Helpers de mapeo
# ---------------------------------------------------------------------------

def _row_to_oc(r) -> OrdenCompra:
    return OrdenCompra(
        codigo_oc=r["codigo_oc"],
        nombre_oc=r["nombre_oc"] or "",
        codigo_estado_mp=r["codigo_estado_mp"] or 0,
        estado_mp=r["estado_mp"] or "",
        codigo_tipo=r["codigo_tipo"] or "",
        tipo_oc=r["tipo_oc"] or "",
        fecha_creacion=r["fecha_creacion"] or "",
        fecha_envio=r["fecha_envio"] or "",
        fecha_aceptacion=r["fecha_aceptacion"] or "",
        fecha_cancelacion=r["fecha_cancelacion"] or "",
        fecha_ultima_modificacion=r["fecha_ultima_modificacion"] or "",
        total_neto=r["total_neto"] or 0.0,
        impuestos=r["impuestos"] or 0.0,
        total=r["total"] or 0.0,
        porcentaje_iva=r["porcentaje_iva"] or 0.0,
        descuentos=r["descuentos"] or 0.0,
        cargos=r["cargos"] or 0.0,
        moneda=r["moneda"] or "CLP",
        codigo_organismo=r["codigo_organismo"] or "",
        nombre_organismo=r["nombre_organismo"] or "",
        rut_unidad=r["rut_unidad"] or "",
        codigo_unidad=r["codigo_unidad"] or "",
        nombre_unidad=r["nombre_unidad"] or "",
        direccion_unidad=r["direccion_unidad"] or "",
        comuna_unidad=r["comuna_unidad"] or "",
        region_unidad=r["region_unidad"] or "",
        codigo_licitacion=r["codigo_licitacion"] or "",
        direccion_despacho=r["direccion_despacho"] or "",
        direccion_facturacion=r["direccion_facturacion"] or "",
        codigo_proveedor=r["codigo_proveedor"] or "",
        nombre_proveedor=r["nombre_proveedor"] or "",
        rut_proveedor=r["rut_proveedor"] or "",
        cliente_sap_sugerido=r["cliente_sap_sugerido"] or "",
        cantidad_lineas=r["cantidad_lineas"] or 0,
        estado_interno=r["estado_interno"] or "Nueva",
        fecha_ingreso=r["fecha_ingreso"],
        responsable_ingreso_user_id=r["responsable_ingreso_user_id"],
        responsable_ingreso_username=r["responsable_ingreso_username"] or "",
        ingresado_por_user_id=r["ingresado_por_user_id"],
        ingresado_por_username=r["ingresado_por_username"] or "",
        ingreso_sap_acuerdo_global=bool(r["ingreso_sap_acuerdo_global"] or 0),
        notas=r["notas"],
        created_at=r["created_at"] or "",
        updated_at=r["updated_at"] or "",
    )


def _row_to_linea(r) -> LineaOC:
    return LineaOC(
        codigo_oc=r["codigo_oc"],
        correlativo=r["correlativo"],
        codigo_categoria=r["codigo_categoria"] or 0,
        categoria=r["categoria"] or "",
        codigo_producto_api=r["codigo_producto_api"] or "",
        codigo_mp=r["codigo_mp"],
        producto=r["producto"] or "",
        especificacion_comprador=r["especificacion_comprador"] or "",
        especificacion_proveedor=r["especificacion_proveedor"] or "",
        cantidad=r["cantidad"] or 0.0,
        unidad=r["unidad"] or "",
        moneda=r["moneda"] or "CLP",
        precio_neto=r["precio_neto"] or 0.0,
        total_cargos=r["total_cargos"] or 0.0,
        total_descuentos=r["total_descuentos"] or 0.0,
        total_impuestos=r["total_impuestos"] or 0.0,
        total=r["total"] or 0.0,
        factor_empaque=r["factor_empaque"] or 1.0,
        cantidad_sap=r["cantidad_sap"],
        precio_sap=r["precio_sap"],
        sap_mode=r["sap_mode"],
        sap_mode_origen=r["sap_mode_origen"],
        sap_values_origen=r["sap_values_origen"],
        sap_values_updated_at=r["sap_values_updated_at"] or "",
        sap_values_updated_by_user_id=r["sap_values_updated_by_user_id"],
        sap_values_updated_by_username=r["sap_values_updated_by_username"] or "",
        itemcode_sap=r["itemcode_sap"],
        descripcion_sap=r["descripcion_sap"],
        estado_homologacion=r["estado_homologacion"] or "pendiente",
        created_at=r["created_at"] or "",
        updated_at=r["updated_at"] or "",
    )
