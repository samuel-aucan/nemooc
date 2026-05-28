"""
Orquestador de sincronizacion: descarga OCs desde la API, las transforma,
homologa (CM) y persiste. Corre en un thread separado y comunica progreso via Queue.
"""

import logging
import queue
import threading
import time
from datetime import datetime

from app.repositories import oc_repository
from app.services import transform_service
from app.services.homologacion_service import get_homologacion_service
from app.services.licitaciones_service import get_licitaciones_service
from app.services.mp_api_service import APIError, MercadoPublicoAPI
from app.services.sap_mode_service import apply_auto_mode_to_line, apply_learned_sap_values_to_line

logger = logging.getLogger(__name__)


def _normalizar_rut(valor: str) -> str:
    """Normaliza RUT a formato sin puntos, sin guión, sin DV (últimos 8 dígitos)."""
    rut = valor.upper().replace("CN", "", 1) if valor.upper().startswith("CN") else valor
    rut = rut.replace(".", "").replace("-", "").replace(" ", "")
    if len(rut) >= 9:
        rut = rut[:-1]
    return rut


def _preparar_oc_y_lineas(raw_detalle: dict, catalog) -> tuple:
    oc = transform_service.parse_cabecera_oc(raw_detalle)
    raw_items = (raw_detalle.get("Items") or {}).get("Listado", [])
    lineas = transform_service.parse_detalle_oc(raw_items, oc.codigo_oc)

    if oc.tipo_oc == "CM":
        lineas, sin_homo = transform_service.homologar_lineas(lineas, catalog)
    else:
        lics_svc = get_licitaciones_service()
        for linea in lineas:
            desc_query = linea.especificacion_comprador or linea.producto
            sugs = lics_svc.buscar_sugerencias(
                desc_query,
                rut_oc=oc.rut_unidad,
                max_results=1,
            )

            if sugs and sugs[0].score >= 0.35:
                linea.itemcode_sap = sugs[0].itemcode_sap
                linea.descripcion_sap = sugs[0].descripcion_sap
                linea.estado_homologacion = "asignado_auto"
            else:
                linea.estado_homologacion = "manual"

            apply_auto_mode_to_line(linea, oc.tipo_oc)
        sin_homo = []

    for linea in lineas:
        apply_learned_sap_values_to_line(linea, oc)

    return oc, lineas, sin_homo


def import_single_public_oc(
    ticket: str,
    codigo_empresa: str,
    codigo_oc: str,
) -> dict:
    codigo = (codigo_oc or "").strip().upper()
    if not codigo:
        raise ValueError("Debe indicar un codigo de OC")

    existente = oc_repository.get_oc(codigo)
    if existente:
        return {
            "ok": True,
            "created": False,
            "oc": existente,
            "lineas": oc_repository.get_lineas(codigo),
            "message": f"OC {codigo} ya existe en la base local.",
        }

    api = MercadoPublicoAPI(ticket=ticket, codigo_empresa=codigo_empresa)
    catalog = get_homologacion_service()
    raw_detalle = api.obtener_detalle_oc(codigo)
    oc, lineas, sin_homo = _preparar_oc_y_lineas(raw_detalle, catalog)

    if not oc.codigo_oc:
        oc.codigo_oc = codigo
        for linea in lineas:
            linea.codigo_oc = codigo

    oc_repository.save_oc(oc, lineas)

    try:
        from backend.supabase_write_service import upsert_oc as _upsert_sb
        _upsert_sb(oc, lineas)
    except Exception:
        pass

    n_homo = len(lineas) - len(sin_homo)
    return {
        "ok": True,
        "created": True,
        "oc": oc,
        "lineas": lineas,
        "message": f"OC {oc.codigo_oc} importada desde Mercado Publico: {len(lineas)} lineas, {n_homo} homologadas.",
    }


def run_sync(
    ticket: str,
    codigo_empresa: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    progress_queue: queue.Queue,
    solo_cm: bool = False,
    ruts_filter: list[str] | None = None,
) -> dict[str, int | bool]:
    """
    Funcion que corre en un thread worker.
    Emite mensajes al progress_queue:
        {"type": "log", "message": str}
        {"type": "progress", "current": int, "total": int}
        {"type": "done", "message": str, "nuevas": int, "errores": int}
        {"type": "error", "message": str}
    """

    def emit(tipo: str, **kwargs):
        progress_queue.put({"type": tipo, **kwargs})

    emit("log", message="Iniciando sincronizacion con Mercado Publico...")

    api = MercadoPublicoAPI(ticket=ticket, codigo_empresa=codigo_empresa)
    catalog = get_homologacion_service()

    tipo_label = "CM" if solo_cm else "todas"
    try:
        lista_raw = api.obtener_lista_oc(fecha_desde, fecha_hasta, solo_cm=solo_cm)
    except APIError as e:
        emit("error", message=f"Error de API: {e}")
        return {"ok": False, "nuevas": 0, "errores": 1}
    except Exception as e:
        emit("error", message=f"Error inesperado obteniendo lista: {e}")
        return {"ok": False, "nuevas": 0, "errores": 1}

    total_encontradas = len(lista_raw)
    emit("log", message=f"Se encontraron {total_encontradas} OC(s) ({tipo_label}) en el periodo.")

    if ruts_filter:
        ruts_set = set(ruts_filter)
        lista_raw = [
            oc for oc in lista_raw
            if _normalizar_rut((oc.get("Comprador") or {}).get("RutUnidad", "")) in ruts_set
        ]
        emit("log", message=f"Filtro de cartera activo: {len(lista_raw)} OC(s) corresponden a tu cartera.")

    if total_encontradas == 0:
        emit("done", message=f"No hay OCs ({tipo_label}) en el rango seleccionado.", nuevas=0, errores=0)
        return {"ok": True, "nuevas": 0, "errores": 0}

    try:
        existentes = oc_repository.get_existing_codes()
    except Exception as e:
        emit("error", message=f"Error accediendo a la base de datos: {e}")
        return {"ok": False, "nuevas": 0, "errores": 1}

    nuevas = 0
    errores = 0

    nuevas_en_api = [oc for oc in lista_raw if oc.get("Codigo", "") not in existentes]
    ya_existentes = total_encontradas - len(nuevas_en_api)

    if ya_existentes:
        emit("log", message=f"  {ya_existentes} OC(s) ya existen en la base de datos y se omiten.")
    if not nuevas_en_api:
        emit("log", message="No hay OCs nuevas por descargar.")
        emit("done", message="Sin OCs nuevas.", nuevas=0, errores=0)
        return {"ok": True, "nuevas": 0, "errores": 0}

    total_nuevas = len(nuevas_en_api)
    emit("log", message=f"  {total_nuevas} OC(s) nuevas por descargar...")
    emit("progress", current=0, total=total_nuevas)

    for i, oc_summary in enumerate(nuevas_en_api, start=1):
        codigo = oc_summary.get("Codigo", "")
        emit("log", message=f"  [{i}/{total_nuevas}] {codigo}: procesando...")

        raw_detalle = oc_summary
        items_data = oc_summary.get("Items") or {}
        tiene_items = items_data.get("Cantidad", 0) or 0

        if not tiene_items or not items_data.get("Listado"):
            emit("log", message="    Sin items en lista, consultando detalle...")
            time.sleep(0.8)
            try:
                raw_detalle = api.obtener_detalle_oc(codigo)
            except APIError as e:
                emit("log", message=f"    ERROR detalle: {e}")
                errores += 1
                emit("progress", current=i, total=total_nuevas)
                continue
            except Exception as e:
                emit("log", message=f"    ERROR inesperado: {e}")
                errores += 1
                emit("progress", current=i, total=total_nuevas)
                continue

        try:
            oc, lineas, sin_homo = _preparar_oc_y_lineas(raw_detalle, catalog)
        except Exception as e:
            emit("log", message=f"    ERROR transformando {codigo}: {e}")
            errores += 1
            emit("progress", current=i, total=total_nuevas)
            continue

        try:
            oc_repository.save_oc(oc, lineas)
            nuevas += 1
            n_homo = len(lineas) - len(sin_homo)
            msg = f"    OK: {len(lineas)} lineas, {n_homo} homologadas"
            if sin_homo:
                msg += f", {len(sin_homo)} SIN homologacion (correlativo: {sin_homo})"
            emit("log", message=msg)
        except Exception as e:
            emit("log", message=f"    ERROR guardando {codigo}: {e}")
            errores += 1
            emit("progress", current=i, total=total_nuevas)
            continue

        # Sincronizar en Supabase (silencioso, no interrumpe el flujo)
        try:
            from backend.supabase_write_service import upsert_oc as _upsert_sb
            _upsert_sb(oc, lineas)
        except Exception:
            pass

        estados_finales = {
            "recepcion conforme",
            "recepci\u00f3n conforme",
            "cerrada",
            "cerrado",
            "cancelada",
            "cancelado",
        }
        estado_lower = (oc.estado_mp or "").strip().lower()
        if estado_lower in estados_finales:
            emit("log", message=f"    Email omitido: OC en estado final ({oc.estado_mp})")
        else:
            try:
                from app.config import load_config as _load_cfg
                from app.services.cartera_service import get_cartera_service
                from app.services.email_service import get_email_service

                cfg = _load_cfg()
                if cfg.smtp_enabled:
                    cliente = get_cartera_service().lookup(oc.cliente_sap_sugerido)
                    if cliente:
                        get_email_service().enviar_notificacion_oc(oc, cliente)
            except Exception as exc:
                logger.warning(f"Email no enviado para {oc.codigo_oc}: {exc}")

        emit("progress", current=i, total=total_nuevas)

    resumen = (
        "Sincronizacion completada. "
        f"Nuevas: {nuevas} | Errores: {errores} | "
        f"Omitidas (ya existian): {ya_existentes}"
    )
    emit("log", message=resumen)
    emit("done", message=resumen, nuevas=nuevas, errores=errores)
    return {"ok": True, "nuevas": nuevas, "errores": errores}


def run_sync_light(
    ticket: str,
    codigo_empresa: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    progress_queue: queue.Queue,
) -> dict[str, int | bool]:
    """
    Sincronizacion ligera: solo actualiza estado_mp de OCs existentes.
    NO descarga lineas completas, solo estado.
    Corre en thread separado.
    """

    def emit(tipo: str, **kwargs):
        progress_queue.put({"type": tipo, **kwargs})

    emit("log", message="Iniciando sincronizacion ligera de estados (Mercado Publico)...")

    api = MercadoPublicoAPI(ticket=ticket, codigo_empresa=codigo_empresa)

    try:
        lista_raw = api.obtener_lista_oc(fecha_desde, fecha_hasta, solo_cm=False)
    except Exception as e:
        emit("error", message=f"Error obteniendo lista: {e}")
        return {"ok": False, "nuevas": 0, "errores": 1}

    total = len(lista_raw)
    emit("log", message=f"Se encontraron {total} OC(s) en el periodo.")
    emit("progress", current=0, total=total)

    if total == 0:
        emit("done", message="No hay OCs en el rango seleccionado.", nuevas=0, errores=0)
        return {"ok": True, "nuevas": 0, "errores": 0}

    try:
        existentes = oc_repository.get_existing_codes()
    except Exception as e:
        emit("error", message=f"Error accediendo BD: {e}")
        return {"ok": False, "nuevas": 0, "errores": 1}

    actualizadas = 0
    errores = 0

    for idx, raw in enumerate(lista_raw, 1):
        codigo = raw.get("Codigo", "")
        if not codigo:
            continue

        if codigo not in existentes:
            emit("log", message=f"  [{idx}/{total}] {codigo} - omitida (no existe en BD)")
            emit("progress", current=idx, total=total)
            continue

        try:
            codigo_estado_mp = int(raw.get("CodigoEstado", 0) or 0)
            estado_mp = transform_service.resolve_estado_mp(
                raw.get("Estado", ""),
                codigo_estado_mp,
            )

            from app.db import get_connection

            conn = get_connection()
            try:
                if estado_mp:
                    conn.execute(
                        """
                        UPDATE oc_cabecera
                        SET estado_mp = ?, codigo_estado_mp = ?, fecha_ultima_modificacion = ?
                        WHERE codigo_oc = ?
                        """,
                        (estado_mp, codigo_estado_mp, datetime.now().isoformat(), codigo),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE oc_cabecera
                        SET codigo_estado_mp = ?, fecha_ultima_modificacion = ?
                        WHERE codigo_oc = ?
                        """,
                        (codigo_estado_mp, datetime.now().isoformat(), codigo),
                    )
                conn.commit()
                actualizadas += 1
                estado_log = estado_mp or f"codigo {codigo_estado_mp} (sin texto)"
                emit("log", message=f"  [{idx}/{total}] {codigo} -> {estado_log} OK")
            finally:
                conn.close()

            # Sincronizar estado en Supabase (silencioso)
            try:
                from backend.supabase_write_service import upsert_oc as _upsert_sb
                oc_obj = oc_repository.get_oc(codigo)
                if oc_obj:
                    lineas_obj = oc_repository.get_lineas(codigo)
                    _upsert_sb(oc_obj, lineas_obj)
            except Exception:
                pass

        except Exception as e:
            emit("log", message=f"  [{idx}/{total}] {codigo} - ERROR: {e}")
            errores += 1

        emit("progress", current=idx, total=total)

    resumen = f"Sincronizacion ligera completada. Actualizadas: {actualizadas} | Errores: {errores}"
    emit("log", message=resumen)
    emit("done", message=resumen, nuevas=actualizadas, errores=errores)
    return {"ok": True, "nuevas": actualizadas, "errores": errores}


def refresh_oc_status_from_portal(
    ticket: str,
    codigo_empresa: str,
    codigo_oc: str,
) -> dict[str, str | int | bool]:
    """
    Refresca el estado de portal de una sola OC ya existente.
    Devuelve el estado resuelto para que la capa web pueda decidir si lo informa.
    """

    api = MercadoPublicoAPI(ticket=ticket, codigo_empresa=codigo_empresa)
    raw = api.obtener_detalle_oc(codigo_oc)

    codigo_estado_mp = int(raw.get("CodigoEstado", 0) or 0)
    estado_mp = transform_service.resolve_estado_mp(
        raw.get("Estado", ""),
        codigo_estado_mp,
    )
    updated = oc_repository.actualizar_estado_mp_oc(
        codigo_oc,
        codigo_estado_mp=codigo_estado_mp,
        estado_mp=estado_mp,
    )

    return {
        "updated": updated,
        "estado_mp": estado_mp,
        "codigo_estado_mp": codigo_estado_mp,
    }


def start_sync_thread(
    ticket: str,
    codigo_empresa: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    solo_cm: bool = False,
) -> queue.Queue:
    """
    Inicia la sincronizacion en un thread daemon y retorna la Queue de progreso.
    """

    q: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=run_sync,
        args=(ticket, codigo_empresa, fecha_desde, fecha_hasta, q, solo_cm),
        daemon=True,
        name="SyncThread",
    )
    t.start()
    return q


def start_sync_light_thread(
    ticket: str,
    codigo_empresa: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
) -> queue.Queue:
    """
    Inicia sincronizacion ligera en thread daemon.
    """

    q: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=run_sync_light,
        args=(ticket, codigo_empresa, fecha_desde, fecha_hasta, q),
        daemon=True,
        name="SyncLightThread",
    )
    t.start()
    return q
