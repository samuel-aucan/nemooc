"""
Orquestador de sincronización: descarga OCs desde la API, las transforma,
homologa (CM) y persiste. Corre en un thread separado y comunica progreso via Queue.
"""
import logging
import queue
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from app.services.mp_api_service import MercadoPublicoAPI, APIError
from app.services import transform_service
from app.services.homologacion_service import get_homologacion_service
from app.services.licitaciones_service import get_licitaciones_service
from app.repositories import oc_repository

logger = logging.getLogger(__name__)


def run_sync(
    ticket: str,
    codigo_empresa: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    progress_queue: queue.Queue,
    solo_cm: bool = False,
) -> None:
    """
    Función que corre en un thread worker.
    Emite mensajes al progress_queue:
        {"type": "log",      "message": str}
        {"type": "progress", "current": int, "total": int}
        {"type": "done",     "message": str, "nuevas": int, "errores": int}
        {"type": "error",    "message": str}
    """
    def emit(tipo: str, **kwargs):
        progress_queue.put({"type": tipo, **kwargs})

    emit("log", message="Iniciando sincronización con Mercado Público...")

    api = MercadoPublicoAPI(ticket=ticket, codigo_empresa=codigo_empresa)
    catalog = get_homologacion_service()

    # 1. Obtener lista de OCs
    tipo_label = "CM" if solo_cm else "todas"
    try:
        lista_raw = api.obtener_lista_oc(fecha_desde, fecha_hasta, solo_cm=solo_cm)
    except APIError as e:
        emit("error", message=f"Error de API: {e}")
        return
    except Exception as e:
        emit("error", message=f"Error inesperado obteniendo lista: {e}")
        return

    total = len(lista_raw)
    emit("log", message=f"Se encontraron {total} OC(s) ({tipo_label}) en el período.")
    emit("progress", current=0, total=total)

    if total == 0:
        emit("done", message=f"No hay OCs ({tipo_label}) en el rango seleccionado.", nuevas=0, errores=0)
        return

    # 2. Pre-cargar códigos existentes para evitar re-descarga innecesaria
    try:
        existentes = oc_repository.get_existing_codes()
    except Exception as e:
        emit("error", message=f"Error accediendo a la base de datos: {e}")
        return

    nuevas = 0
    errores = 0
    omitidas = 0

    # Contar cuántas ya existen para informar rápido
    nuevas_en_api = [oc for oc in lista_raw if oc.get("Codigo", "") not in existentes]
    ya_existentes = total - len(nuevas_en_api)
    if ya_existentes:
        emit("log", message=f"  {ya_existentes} OC(s) ya existen en la base de datos — se omiten.")
    if not nuevas_en_api:
        emit("log", message="No hay OCs nuevas por descargar.")
        emit("done", message="Sin OCs nuevas.", nuevas=0, errores=0)
        return

    emit("log", message=f"  {len(nuevas_en_api)} OC(s) nuevas por descargar...")
    total_nuevas = len(nuevas_en_api)

    for i, oc_summary in enumerate(lista_raw, start=1):
        codigo = oc_summary.get("Codigo", "")
        emit("progress", current=i, total=total)

        if codigo in existentes:
            omitidas += 1
            continue

        emit("log", message=f"  [{i}/{total}] {codigo}: procesando...")

        # 3. Usar datos de la lista directamente (ya incluye Items completo)
        # Si no tiene Items, intentar obtener detalle por separado
        raw_detalle = oc_summary
        items_data = (oc_summary.get("Items") or {})
        tiene_items = items_data.get("Cantidad", 0) or 0

        if not tiene_items or not items_data.get("Listado"):
            emit("log", message=f"    Sin ítems en lista, consultando detalle...")
            time.sleep(0.8)  # pausa para respetar rate limit del servidor
            try:
                raw_detalle = api.obtener_detalle_oc(codigo)
            except APIError as e:
                emit("log", message=f"    ERROR detalle: {e}")
                errores += 1
                continue
            except Exception as e:
                emit("log", message=f"    ERROR inesperado: {e}")
                errores += 1
                continue

        # 4. Transformar
        try:
            oc = transform_service.parse_cabecera_oc(raw_detalle)
            raw_items = (raw_detalle.get("Items") or {}).get("Listado", [])
            lineas = transform_service.parse_detalle_oc(raw_items, oc.codigo_oc)
        except Exception as e:
            emit("log", message=f"    ERROR transformando {codigo}: {e}")
            errores += 1
            continue

        # 5. Homologar
        if oc.tipo_oc == "CM":
            lineas, sin_homo = transform_service.homologar_lineas(lineas, catalog)
        else:
            lics_svc = get_licitaciones_service()
            for l in lineas:
                # Intentar auto-asignar la mejor sugerencia
                desc_query = l.especificacion_comprador or l.producto
                sugs = lics_svc.buscar_sugerencias(
                    desc_query, 
                    rut_oc=oc.rut_unidad, 
                    max_results=1
                )
                
                if sugs and sugs[0].score >= 0.35: # Umbral de confianza
                    l.itemcode_sap = sugs[0].itemcode_sap
                    l.descripcion_sap = sugs[0].descripcion_sap
                    l.estado_homologacion = "asignado_auto"
                else:
                    l.estado_homologacion = "manual"
                
                l.cantidad_sap = l.cantidad
                l.precio_sap = l.precio_neto
            sin_homo = []

        # 6. Persistir
        try:
            oc_repository.save_oc(oc, lineas)
            nuevas += 1
            n_homo = len(lineas) - len(sin_homo)
            msg = f"    OK: {len(lineas)} líneas, {n_homo} homologadas"
            if sin_homo:
                msg += f", {len(sin_homo)} SIN homologación (correlativo: {sin_homo})"
            emit("log", message=msg)
        except Exception as e:
            emit("log", message=f"    ERROR guardando {codigo}: {e}")
            errores += 1
            continue

        # 7. Notificación email — solo para OCs en estado inicial (no finales)
        _ESTADOS_FINALES = {
            "recepción conforme", "recepcion conforme",
            "cerrada", "cerrado",
            "cancelada", "cancelado",
        }
        _estado_lower = (oc.estado_mp or "").strip().lower()
        if _estado_lower in _ESTADOS_FINALES:
            emit("log", message=f"    Email omitido: OC en estado final ({oc.estado_mp})")
        else:
            try:
                from app.config import load_config as _load_cfg
                from app.services.email_service import get_email_service
                from app.services.cartera_service import get_cartera_service
                _cfg = _load_cfg()
                if _cfg.smtp_enabled:
                    _cliente = get_cartera_service().lookup(oc.cliente_sap_sugerido)
                    if _cliente:
                        get_email_service().enviar_notificacion_oc(oc, _cliente)
            except Exception as _e:
                logger.warning(f"Email no enviado para {oc.codigo_oc}: {_e}")

    resumen = (
        f"Sincronización completada. "
        f"Nuevas: {nuevas} | Errores: {errores} | "
        f"Omitidas (ya existían): {total - nuevas - errores}"
    )
    emit("log", message=resumen)
    emit("done", message=resumen, nuevas=nuevas, errores=errores)


def run_sync_light(
    ticket: str,
    codigo_empresa: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    progress_queue: queue.Queue,
) -> None:
    """
    Sincronización ligera: solo actualiza estado_mp de OCs existentes.
    NO descarga líneas completas, solo estado.
    Corre en thread separado.
    """
    def emit(tipo: str, **kwargs):
        progress_queue.put({"type": tipo, **kwargs})

    emit("log", message="Iniciando sincronización ligera de estados (Mercado Público)...")

    api = MercadoPublicoAPI(ticket=ticket, codigo_empresa=codigo_empresa)

    # Obtener lista simple de OCs
    try:
        lista_raw = api.obtener_lista_oc(fecha_desde, fecha_hasta, solo_cm=False)
    except Exception as e:
        emit("error", message=f"Error obteniendo lista: {e}")
        return

    total = len(lista_raw)
    emit("log", message=f"Se encontraron {total} OC(s) en el período.")
    emit("progress", current=0, total=total)

    if total == 0:
        emit("done", message="No hay OCs en el rango seleccionado.", nuevas=0, errores=0)
        return

    # Obtener códigos existentes
    try:
        existentes = oc_repository.get_existing_codes()
    except Exception as e:
        emit("error", message=f"Error accediendo BD: {e}")
        return

    actualizadas = 0
    errores = 0

    # Actualizar solo estado_mp de OCs existentes
    for idx, raw in enumerate(lista_raw, 1):
        codigo = raw.get("Codigo", "")
        if not codigo:
            continue

        if codigo not in existentes:
            emit("log", message=f"  [{idx}/{total}] {codigo} — omitida (no existe en BD)")
            emit("progress", current=idx, total=total)
            continue

        try:
            # En la lista el campo de estado se llama "Nombre" (no "Estado")
            estado_mp = raw.get("Nombre", "") or raw.get("Estado", "")
            codigo_estado_mp = raw.get("CodigoEstado", 0)

            # Actualizar en BD (pequeña operación)
            from app.db import get_connection
            conn = get_connection()
            try:
                conn.execute(
                    """
                    UPDATE oc_cabecera
                    SET estado_mp = ?, codigo_estado_mp = ?, fecha_ultima_modificacion = ?
                    WHERE codigo_oc = ?
                    """,
                    (estado_mp, codigo_estado_mp, datetime.now().isoformat(), codigo),
                )
                conn.commit()
                actualizadas += 1
                emit("log", message=f"  [{idx}/{total}] {codigo} → {estado_mp} ✓")
            finally:
                conn.close()

        except Exception as e:
            emit("log", message=f"  [{idx}/{total}] {codigo} — ERROR: {e}")
            errores += 1

        emit("progress", current=idx, total=total)

    resumen = f"Sincronización ligera completada. Actualizadas: {actualizadas} | Errores: {errores}"
    emit("log", message=resumen)
    emit("done", message=resumen, nuevas=actualizadas, errores=errores)


def start_sync_thread(
    ticket: str,
    codigo_empresa: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    solo_cm: bool = False,
) -> queue.Queue:
    """
    Inicia la sincronización en un thread daemon y retorna la Queue de progreso.
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
    Inicia sincronización ligera en thread daemon.
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
