"""
Repositorio para OC cabecera y detalle.
Gestiona inserciones, actualizaciones, consultas y exportaciones.
"""
import logging
from datetime import datetime
from typing import List, Optional, Set, Tuple

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
                    factor_empaque, cantidad_sap, precio_sap,
                    itemcode_sap, descripcion_sap, estado_homologacion,
                    created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(codigo_oc, correlativo) DO UPDATE SET
                    codigo_mp           = excluded.codigo_mp,
                    itemcode_sap        = excluded.itemcode_sap,
                    descripcion_sap     = excluded.descripcion_sap,
                    factor_empaque      = excluded.factor_empaque,
                    cantidad_sap        = excluded.cantidad_sap,
                    precio_sap          = excluded.precio_sap,
                    estado_homologacion = excluded.estado_homologacion,
                    updated_at          = excluded.updated_at
            """, (
                linea.codigo_oc, linea.correlativo, linea.codigo_categoria,
                linea.categoria, linea.codigo_producto_api, linea.codigo_mp,
                linea.producto, linea.especificacion_comprador, linea.especificacion_proveedor,
                linea.cantidad, linea.unidad, linea.moneda, linea.precio_neto,
                linea.total_cargos, linea.total_descuentos, linea.total_impuestos, linea.total,
                linea.factor_empaque, linea.cantidad_sap, linea.precio_sap,
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


def marcar_ingresada(codigo_oc: str) -> None:
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute("""
            UPDATE oc_cabecera
            SET estado_interno = 'Ingresada',
                fecha_ingreso  = ?,
                updated_at     = ?
            WHERE codigo_oc = ?
              AND (fecha_ingreso IS NULL OR fecha_ingreso = '')
        """, (now, now, codigo_oc))
        conn.commit()
    finally:
        conn.close()


def actualizar_estado(codigo_oc: str, estado: str) -> None:
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute("""
            UPDATE oc_cabecera
            SET estado_interno = ?, updated_at = ?
            WHERE codigo_oc = ?
        """, (estado, now, codigo_oc))
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
    busqueda: Optional[str] = None,
    estado_mp=None,
    tipo_oc=None,
    holding=None,
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
        if fecha_desde:
            sql += " AND DATE(fecha_envio) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(fecha_envio) <= DATE(?)"
            params.append(fecha_hasta)
        if busqueda:
            sql += " AND (codigo_oc LIKE ? OR nombre_organismo LIKE ? OR cliente_sap_sugerido LIKE ?)"
            like = f"%{busqueda}%"
            params.extend([like, like, like])
        sql += " ORDER BY fecha_envio DESC"

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
            sql += " AND DATE(c.fecha_envio) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(c.fecha_envio) <= DATE(?)"
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
            sql += " AND DATE(c.fecha_envio) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(c.fecha_envio) <= DATE(?)"
            params.append(fecha_hasta)

        sql += """
            ORDER BY
                CASE
                    WHEN COALESCE(TRIM(l.itemcode_sap), '') = '' THEN 0
                    WHEN COALESCE(l.estado_homologacion, '') = 'manual' THEN 1
                    ELSE 2
                END,
                DATE(c.fecha_envio) DESC,
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
            date_filter += " AND DATE(fecha_envio) >= DATE(?)"
            date_params.append(fecha_desde)
        if fecha_hasta:
            date_filter += " AND DATE(fecha_envio) <= DATE(?)"
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
            sql += " AND DATE(c.fecha_envio) >= DATE(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(c.fecha_envio) <= DATE(?)"
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
    conn = get_connection()
    now = datetime.now().isoformat()
    _ESTADOS_VALIDOS = {"homologado", "sugerido", "manual"}
    estado = origen if origen in _ESTADOS_VALIDOS else "manual"
    try:
        conn.execute(
            """
            UPDATE oc_detalle
            SET itemcode_sap = ?, descripcion_sap = ?,
                estado_homologacion = ?, updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
            """,
            (itemcode_sap, descripcion_sap or None, estado, now, codigo_oc, correlativo),
        )
        conn.commit()
    finally:
        conn.close()


def limpiar_asignacion_linea(codigo_oc: str, correlativo: int) -> None:
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute(
            """
            UPDATE oc_detalle
            SET itemcode_sap = NULL, descripcion_sap = NULL,
                estado_homologacion = 'pendiente', updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
            """,
            (now, codigo_oc, correlativo),
        )
        conn.commit()
    finally:
        conn.close()


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
        itemcode_sap=r["itemcode_sap"],
        descripcion_sap=r["descripcion_sap"],
        estado_homologacion=r["estado_homologacion"] or "pendiente",
        created_at=r["created_at"] or "",
        updated_at=r["updated_at"] or "",
    )
