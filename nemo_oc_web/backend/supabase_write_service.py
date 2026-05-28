"""
Servicio de escritura en Supabase.
Sincroniza OC desde SQLite → Supabase PostgreSQL después de cada sync.
Usa Management API (raw SQL) — NO depende del SDK supabase-py.
Errores son silenciosos para no interrumpir el flujo principal.
"""
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _raw_sql(sql: str, params: list | None = None) -> list[dict]:
    """Ejecuta SQL raw via Supabase Management API."""
    import requests

    pat = os.environ.get("SUPABASE_PAT", "")
    project = os.environ.get("SUPABASE_PROJECT", "")
    if not pat or not project:
        raise RuntimeError("SUPABASE_PAT y SUPABASE_PROJECT requeridos")

    url = f"https://api.supabase.com/v1/projects/{project}/database/query"
    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

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


def _extraer_rut_base(valor: str) -> str:
    if not valor:
        return ""
    rut = re.sub(r"^CN", "", valor, flags=re.IGNORECASE)
    rut = re.sub(r"[.\-\s]", "", rut)
    if len(rut) >= 9:
        rut = rut[:-1]
    return rut


def _lookup_cartera_id(rut_base: str) -> Optional[str]:
    if not rut_base:
        return None
    try:
        candidatos = f"'CN{rut_base}', '{rut_base}'"
        rows = _raw_sql(
            f"SELECT cartera_id FROM clientes WHERE codigo_sap IN ({candidatos}) LIMIT 1"
        )
        if rows:
            return rows[0].get("cartera_id")
    except Exception as e:
        logger.debug(f"[supabase_write] lookup_cartera_id({rut_base}): {e}")
    return None


def _map_estado_homo(estado: str) -> str:
    mapping = {
        "homologado": "homologada",
        "asignado_auto": "homologada",
        "manual": "manual",
        "sugerido": "sugerida",
        "pendiente": "pendiente",
        "sin_homo": "pendiente",
        "bloqueado": "bloqueada",
    }
    return mapping.get(str(estado).lower(), "pendiente")


def _sql_val(v) -> str:
    """Convierte un valor Python a literal SQL."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    safe = str(v).replace("'", "''")
    return f"'{safe}'"


def upsert_oc(oc, lineas: list) -> None:
    """Escribe una OC y sus líneas en Supabase via raw SQL."""
    try:
        pat = os.environ.get("SUPABASE_PAT", "")
        project = os.environ.get("SUPABASE_PROJECT", "")
        if not pat or not project:
            return

        # Determinar cartera_id
        cartera_id = None
        for candidato in [
            getattr(oc, "cliente_sap_sugerido", ""),
            getattr(oc, "rut_unidad", ""),
        ]:
            if candidato:
                rut_base = _extraer_rut_base(candidato)
                if rut_base:
                    cartera_id = _lookup_cartera_id(rut_base)
                    if cartera_id:
                        break

        # Upsert cabecera
        cab_cols = {
            "codigo_oc": oc.codigo_oc,
            "nombre_oc": getattr(oc, "nombre_oc", None) or None,
            "estado_mp": getattr(oc, "estado_mp", None) or None,
            "codigo_estado_mp": getattr(oc, "codigo_estado_mp", None),
            "tipo_oc": getattr(oc, "tipo_oc", None) or None,
            "fecha_envio": getattr(oc, "fecha_envio", None) or None,
            "fecha_aceptacion": getattr(oc, "fecha_aceptacion", None) or None,
            "total_neto": getattr(oc, "total_neto", None),
            "total_impuestos": getattr(oc, "impuestos", None),
            "total": getattr(oc, "total", None),
            "moneda": getattr(oc, "moneda", "CLP") or "CLP",
            "nombre_organismo": (
                getattr(oc, "nombre_unidad", None)
                or getattr(oc, "nombre_organismo", None)
                or None
            ),
            "codigo_organismo": getattr(oc, "rut_unidad", None) or None,
            "rut_organismo": getattr(oc, "rut_unidad", None) or None,
            "nombre_comprador": (
                getattr(oc, "nombre_responsable", None)
                or getattr(oc, "nombre_comprador", None)
                or None
            ),
            "cargo_comprador": (
                getattr(oc, "cargo_responsable", None)
                or getattr(oc, "cargo_comprador", None)
                or None
            ),
            "direccion_despacho": getattr(oc, "direccion_despacho", None) or None,
            "comuna_despacho": getattr(oc, "comuna_unidad", None) or None,
            "region_despacho": getattr(oc, "region_unidad", None) or None,
            "cliente_sap_sugerido": getattr(oc, "cliente_sap_sugerido", None) or None,
            "cartera_id": cartera_id,
            "tipo_origen": getattr(oc, "tipo_origen", "PUBLICA") or "PUBLICA",
            "codigo_licitacion": getattr(oc, "codigo_licitacion", None) or None,
        }

        cols = ", ".join(cab_cols.keys())
        vals = ", ".join(_sql_val(v) for v in cab_cols.values())
        # On conflict, update everything except codigo_oc, estado_interno, notas
        update_parts = []
        for k in cab_cols:
            if k == "codigo_oc":
                continue
            update_parts.append(f"{k} = EXCLUDED.{k}")

        sql = f"""
            INSERT INTO oc_cabecera ({cols})
            VALUES ({vals})
            ON CONFLICT (codigo_oc) DO UPDATE SET
                {', '.join(update_parts)},
                updated_at = NOW()
            RETURNING id
        """
        rows = _raw_sql(sql)
        if not rows:
            logger.warning(f"[supabase_write] upsert sin id para {oc.codigo_oc}")
            return

        oc_id = rows[0]["id"]

        # Upsert líneas
        for l in lineas:
            det = {
                "oc_id": oc_id,
                "nro_linea": getattr(l, "correlativo", None),
                "codigo_mp": getattr(l, "codigo_mp", None) or getattr(l, "codigo_producto_api", None),
                "descripcion": getattr(l, "producto", None) or None,
                "especificacion": getattr(l, "especificacion_comprador", None) or None,
                "cantidad": getattr(l, "cantidad", None),
                "unidad_medida": getattr(l, "unidad", None) or None,
                "precio_unitario": getattr(l, "precio_neto", None),
                "total_linea": getattr(l, "total", None),
                "moneda": getattr(l, "moneda", "CLP") or "CLP",
                "itemcode_sap": getattr(l, "itemcode_sap", None) or None,
                "descripcion_sap": getattr(l, "descripcion_sap", None) or None,
                "cantidad_sap": getattr(l, "cantidad_sap", None),
                "precio_sap": getattr(l, "precio_sap", None),
                "estado_homologacion": _map_estado_homo(
                    getattr(l, "estado_homologacion", "pendiente")
                ),
                "sap_mode": getattr(l, "sap_mode", None) or None,
                "factor_empaque": getattr(l, "factor_empaque", None),
            }

            det_cols = ", ".join(det.keys())
            det_vals = ", ".join(_sql_val(v) for v in det.values())
            det_updates = ", ".join(
                f"{k} = EXCLUDED.{k}" for k in det if k not in ("oc_id", "nro_linea")
            )

            det_sql = f"""
                INSERT INTO oc_detalle ({det_cols})
                VALUES ({det_vals})
                ON CONFLICT (oc_id, nro_linea) DO UPDATE SET
                    {det_updates}
            """
            _raw_sql(det_sql)

        logger.debug(f"[supabase_write] {oc.codigo_oc} sincronizada ({len(lineas)} líneas)")

    except Exception as e:
        logger.warning(f"[supabase_write] Error en upsert_oc({getattr(oc, 'codigo_oc', '?')}): {e}")


def sync_estado_oc(codigo_oc: str, fields: dict) -> None:
    """Actualiza campos de estado/usuario en oc_cabecera."""
    if not fields:
        return
    try:
        set_parts = ", ".join(f"{k} = {_sql_val(v)}" for k, v in fields.items())
        _raw_sql(
            f"UPDATE oc_cabecera SET {set_parts}, updated_at = NOW() WHERE codigo_oc = %s",
            [codigo_oc],
        )
        logger.debug(f"[supabase_write] sync_estado_oc {codigo_oc}: {list(fields.keys())}")
    except Exception as e:
        logger.warning(f"[supabase_write] sync_estado_oc error ({codigo_oc}): {e}")


def sync_homologacion(
    codigo_oc: str,
    nro_linea: int,
    itemcode_sap: Optional[str],
    descripcion_sap: Optional[str],
    cantidad_sap: Optional[float],
    precio_sap: Optional[float],
    sap_mode: Optional[str],
    estado_homologacion: str,
) -> None:
    """Actualiza oc_detalle en Supabase cuando se asigna o limpia un código SAP."""
    try:
        rows = _raw_sql(
            "SELECT id FROM oc_cabecera WHERE codigo_oc = %s LIMIT 1",
            [codigo_oc],
        )
        if not rows:
            logger.debug(f"[supabase_write] sync_homologacion: {codigo_oc} no encontrada")
            return

        oc_id = rows[0]["id"]

        fields = {
            "itemcode_sap": itemcode_sap or None,
            "descripcion_sap": descripcion_sap or None,
            "cantidad_sap": cantidad_sap,
            "precio_sap": precio_sap,
            "sap_mode": sap_mode or None,
            "estado_homologacion": _map_estado_homo(estado_homologacion),
        }
        set_parts = ", ".join(f"{k} = {_sql_val(v)}" for k, v in fields.items())
        _raw_sql(
            f"UPDATE oc_detalle SET {set_parts} WHERE oc_id = {oc_id} AND nro_linea = {nro_linea}"
        )
        logger.debug(f"[supabase_write] sync_homologacion {codigo_oc} linea {nro_linea}: OK")

    except Exception as e:
        logger.warning(f"[supabase_write] sync_homologacion error: {e}")
