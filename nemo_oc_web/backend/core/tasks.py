import asyncio
import logging
import queue
import threading
from datetime import datetime, timedelta

from app.config import load_config
from app.services.sync_service import run_sync, run_sync_light
from backend.api.sync_routes import GLOBAL_SYNC_LOGS

logger = logging.getLogger(__name__)

_auto_sync_task = None
_stop_event = asyncio.Event()
_light_sync_task = None
_light_sync_stop_event = asyncio.Event()
_next_light_sync_time = None  # Almacena la próxima hora de sync ligero


def _add_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    GLOBAL_SYNC_LOGS.append({"time": ts, "message": msg})
    if len(GLOBAL_SYNC_LOGS) > 200:
        GLOBAL_SYNC_LOGS.pop(0)


async def _auto_sync_loop():
    _add_log("=== Auto-Sync Loop Iniciado ===")
    
    # Check if we should sync on startup
    cfg = load_config()
    if cfg.auto_sync and cfg.api_ticket:
        _add_log(f"Ejecutando sync inicial (Auto-sync activado, {cfg.auto_sync_days} días).")
        await _run_sync_once("startup")

    while not _stop_event.is_set():
        cfg = load_config()
        interval = cfg.auto_sync_interval
        
        if interval <= 0 or not cfg.api_ticket:
            await asyncio.sleep(60)
            continue
            
        # Esperar el intervalo
        for _ in range(interval * 60):
            if _stop_event.is_set():
                break
            await asyncio.sleep(1)

        if not _stop_event.is_set():
            _add_log(f"Ejecutando sync periódico (cada {interval} min).")
            await _run_sync_once("periodic")


async def _run_sync_once(trigger_type: str):
    cfg = load_config()
    if not cfg.api_ticket:
        return
        
    fecha_hasta = datetime.now()
    fecha_desde = fecha_hasta - timedelta(days=cfg.auto_sync_days or 7)
    
    q = queue.Queue()
    
    def _worker():
        try:
            run_sync(
                ticket=cfg.api_ticket,
                codigo_empresa=cfg.codigo_empresa,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                progress_queue=q,
                solo_cm=False, # Por defecto auto-sync baja todas, a menos que se quiera restringir
            )
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    threading.Thread(target=_worker, daemon=True).start()
    
    # Leer la cola sin bloquear el hilo principal de asyncio
    while True:
        try:
            msg = q.get_nowait()
            tipo = msg.get("type")
            if tipo == "log":
                _add_log(msg.get("message", ""))
            elif tipo in ("done", "error"):
                _add_log(f"Auto-sync finalizado: {msg.get('message', '')}")
                break
        except queue.Empty:
            await asyncio.sleep(0.5)


def start_auto_sync():
    global _auto_sync_task
    if _auto_sync_task and not _auto_sync_task.done():
        logger.info("Auto-sync ya estaba en ejecución; se reutiliza la tarea existente.")
        return
    _stop_event.clear()
    _auto_sync_task = asyncio.create_task(_auto_sync_loop())


def stop_auto_sync():
    global _auto_sync_task
    _stop_event.set()
    if _auto_sync_task:
        _auto_sync_task.cancel()
        _auto_sync_task = None


# ── Sincronización Ligera (cada 2 horas, solo estados) ──────────────────────

def get_next_light_sync_time():
    """Retorna la próxima hora de sincronización ligera."""
    global _next_light_sync_time
    return _next_light_sync_time


def _calculate_next_light_sync():
    """Calcula la próxima hora de sync (cada 2 horas)."""
    now = datetime.now()
    # Próxima ejecución: siguiente múltiplo de 2 horas
    hour = now.hour
    minute = now.minute

    next_hour = ((hour // 2) + 1) * 2
    if next_hour >= 24:
        next_hour = 0

    return now.replace(hour=next_hour, minute=0, second=0, microsecond=0)


async def _light_sync_loop():
    """Loop que ejecuta sincronización ligera cada 2 horas."""
    global _next_light_sync_time

    _add_log("=== Light Sync Loop Iniciado (cada 2 horas) ===")

    cfg = load_config()
    if cfg.api_ticket:
        _add_log("Ejecutando light-sync inicial...")
        await _run_light_sync_once()

    while not _light_sync_stop_event.is_set():
        cfg = load_config()
        if not cfg.api_ticket:
            await asyncio.sleep(60)
            continue

        # Calcular próxima ejecución
        _next_light_sync_time = _calculate_next_light_sync()
        _add_log(f"Próximo light-sync a las {_next_light_sync_time.strftime('%H:%M')}")

        # Esperar hasta la próxima ejecución
        while not _light_sync_stop_event.is_set():
            now = datetime.now()
            if now >= _next_light_sync_time:
                break
            await asyncio.sleep(30)

        if not _light_sync_stop_event.is_set():
            await _run_light_sync_once()


async def _run_light_sync_once():
    """Ejecuta una sincronización ligera (solo estados, últimos 30 días)."""
    cfg = load_config()
    if not cfg.api_ticket:
        return

    _add_log("🔄 Light-sync: Actualizando estados de OCs (últimos 30 días)...")

    fecha_hasta = datetime.now()
    fecha_desde = fecha_hasta - timedelta(days=30)

    q = queue.Queue()

    def _worker():
        try:
            run_sync_light(
                ticket=cfg.api_ticket,
                codigo_empresa=cfg.codigo_empresa,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                progress_queue=q,
            )
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    threading.Thread(target=_worker, daemon=True).start()

    # Leer la cola
    while True:
        try:
            msg = q.get_nowait()
            tipo = msg.get("type")
            if tipo == "log":
                _add_log(msg.get("message", ""))
            elif tipo in ("done", "error"):
                _add_log(f"✓ Light-sync completado: {msg.get('message', '')}")
                break
        except queue.Empty:
            await asyncio.sleep(0.5)


def start_light_sync():
    """Inicia el loop de sincronización ligera."""
    global _light_sync_task
    if _light_sync_task and not _light_sync_task.done():
        logger.info("Light-sync ya estaba en ejecución; se reutiliza la tarea existente.")
        return
    _light_sync_stop_event.clear()
    _light_sync_task = asyncio.create_task(_light_sync_loop())


def stop_light_sync():
    """Detiene el loop de sincronización ligera."""
    global _light_sync_task
    _light_sync_stop_event.set()
    if _light_sync_task:
        _light_sync_task.cancel()
        _light_sync_task = None
