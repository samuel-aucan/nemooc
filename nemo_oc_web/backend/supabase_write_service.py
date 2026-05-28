"""
Servicio de escritura en Supabase.
Sincroniza OC desde SQLite → Supabase PostgreSQL después de cada sync.
Usa service_role key para bypassar RLS.
Errores son silenciosos para no interrumpir el flujo principal.
"""
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Cliente lazy (se inicializa solo si están las variables de entorno)
_client = None


def _get_supabase():
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("[supabase_write] Cliente inicializado.")
    except Exception as e:
        logger.warning(f"[supabase_write] No se pudo inicializar cliente Supabase: {e}")
        return None

    return _client


def _extraer_rut_base(valor: str) -> str:
    """
    Normaliza un RUT a solo dígitos sin DV.
    '61.608.408-9' → '61608408'
    'CN61608408'   → '61608408'
    """
    if not valor:
        return ""
    rut = re.sub(r"^CN", "", valor, flags=re.IGNORECASE)
    rut = re.sub(r"[.\-\s]", "", rut)
    if len(rut) >= 9:
        rut = rut[:-1]  # quitar DV
    return rut


def _lookup_cartera_id(rut_base: str) -> Optional[str]:
    """Busca cartera_id en Supabase por codigo_sap.
    Intenta con 'CN{rut}' (formato cartera Excel) y sin prefijo.
    """
    if not rut_base:
        return None
    sb = _get_supabase()
    if not sb:
        return None
    # Buscar con ambos formatos: con prefijo CN y sin prefijo
    candidatos = [f"CN{rut_base}", rut_base]
    try:
        res = (
            sb.table("clientes")
            .select("cartera_id")
            .in_("codigo_sap", candidatos)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0].get("cartera_id")
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


def upsert_oc(oc, lineas: list) -> None:
    """
    Escribe una OC y sus líneas en Supabase (upsert por codigo_oc / nro_linea).
    Recibe los objetos OrdenCompra y List[LineaOC] tal como vienen de sync_service.
    """
    sb = _get_supabase()
    if not sb:
        return

    try:
        # ── Determinar cartera_id ─────────────────────────────────────────────
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

        # ── Cabecera ──────────────────────────────────────────────────────────
        cab = {
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
            # Preservar estado_interno/notas si ya existen: el upsert solo actualiza
            # campos de API. Estado/notas del usuario no se sobrescriben porque
            # en Supabase el ON CONFLICT lo gestiona con merge parcial.
            # (Ver nota abajo sobre campos preservados)
        }

        # Upsert cabecera — on_conflict='codigo_oc'
        result = sb.table("oc_cabecera").upsert(
            cab,
            on_conflict="codigo_oc",
            returning="representation",
        ).execute()

        if not result.data:
            logger.warning(f"[supabase_write] upsert sin data para {oc.codigo_oc}")
            return

        oc_id = result.data[0]["id"]

        # ── Líneas ────────────────────────────────────────────────────────────
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
            sb.table("oc_detalle").upsert(
                det,
                on_conflict="oc_id,nro_linea",
            ).execute()

        logger.debug(f"[supabase_write] {oc.codigo_oc} sincronizada ({len(lineas)} líneas)")

    except Exception as e:
        logger.warning(f"[supabase_write] Error en upsert_oc({getattr(oc, 'codigo_oc', '?')}): {e}")


def sync_estado_oc(
    codigo_oc: str,
    fields: dict,
) -> None:
    """
    Actualiza campos de estado/usuario en oc_cabecera de Supabase.
    Llamar desde update_estado, marcar_ingresada, update_responsable, update_notas.
    `fields` es un dict con las columnas Supabase a actualizar.
    """
    sb = _get_supabase()
    if not sb:
        return

    if not fields:
        return

    try:
        sb.table("oc_cabecera").update(fields).eq("codigo_oc", codigo_oc).execute()
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
    """
    Actualiza oc_detalle en Supabase cuando se asigna o limpia un código SAP.
    Llamar desde los endpoints asignar/limpiar de oc_routes.py.
    """
    sb = _get_supabase()
    if not sb:
        return

    try:
        # Obtener oc_id
        res = (
            sb.table("oc_cabecera")
            .select("id")
            .eq("codigo_oc", codigo_oc)
            .single()
            .execute()
        )
        if not res.data:
            logger.debug(f"[supabase_write] sync_homologacion: {codigo_oc} no encontrada en Supabase")
            return

        oc_id = res.data["id"]

        sb.table("oc_detalle").update(
            {
                "itemcode_sap": itemcode_sap or None,
                "descripcion_sap": descripcion_sap or None,
                "cantidad_sap": cantidad_sap,
                "precio_sap": precio_sap,
                "sap_mode": sap_mode or None,
                "estado_homologacion": _map_estado_homo(estado_homologacion),
            }
        ).eq("oc_id", oc_id).eq("nro_linea", nro_linea).execute()

        logger.debug(f"[supabase_write] sync_homologacion {codigo_oc} linea {nro_linea}: OK")

    except Exception as e:
        logger.warning(f"[supabase_write] sync_homologacion error: {e}")
