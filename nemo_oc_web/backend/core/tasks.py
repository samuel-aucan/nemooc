import asyncio
import logging
import queue
import threading
from datetime import datetime, timedelta

from backend.core.paths import ensure_nemo_oc_in_path

ensure_nemo_oc_in_path()

from app.db import get_runtime_config, set_runtime_config
from app.config import get_logs_dir, load_config
from app.services.sync_privado_service import run_sync_privado
from app.services.sync_service import run_sync, run_sync_light
from backend.api.sync_routes import GLOBAL_SYNC_LOGS

logger = logging.getLogger(__name__)

PUBLIC_SYNC_INTERVAL_MINUTES = 5
MIN_PUBLIC_SYNC_INTERVAL_MINUTES = 5
MAX_PUBLIC_SYNC_INTERVAL_MINUTES = 60
PRIVATE_SYNC_DELAY_MINUTES = 7
LAST_MP_SYNC_CONFIG_KEY = "last_mp_sync_at"
STARTUP_SYNC_GRACE_SECONDS = 75

_auto_sync_task = None
_stop_event = asyncio.Event()
_private_sync_task = None
_private_sync_stop_event = asyncio.Event()
_light_sync_task = None
_light_sync_stop_event = asyncio.Event()
_sync_execution_lock = asyncio.Lock()
_next_auto_sync_time = None
_next_private_sync_time = None
_next_light_sync_time = None  # Almacena la próxima hora de sync ligero


def _add_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    GLOBAL_SYNC_LOGS.append({"time": ts, "message": msg})
    if len(GLOBAL_SYNC_LOGS) > 200:
        GLOBAL_SYNC_LOGS.pop(0)


def _load_last_mp_sync_time():
    raw_value = get_runtime_config(LAST_MP_SYNC_CONFIG_KEY, "")
    if not raw_value:
        return _load_last_mp_sync_time_from_logs()
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return _load_last_mp_sync_time_from_logs()


def _load_last_mp_sync_time_from_logs():
    candidate_names = ["nemonkey.log", "nemooc-web.log"]

    for candidate_name in candidate_names:
        log_path = get_logs_dir() / candidate_name
        if not log_path.exists():
            continue

        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        for line in reversed(lines):
            if "app.services.mp_api_service: API:" not in line:
                continue
            timestamp = line[:19].strip()
            try:
                parsed = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                set_runtime_config(LAST_MP_SYNC_CONFIG_KEY, parsed.isoformat())
                return parsed
            except ValueError:
                continue
    return None


_last_successful_sync_time = _load_last_mp_sync_time()


def _mark_mp_sync_success():
    global _last_successful_sync_time
    _last_successful_sync_time = datetime.now()
    set_runtime_config(LAST_MP_SYNC_CONFIG_KEY, _last_successful_sync_time.isoformat())


def record_mp_sync_success():
    """Registra la ultima actualizacion exitosa de Mercado Publico."""
    _mark_mp_sync_success()


def _get_public_sync_interval_minutes(cfg=None) -> int:
    cfg = cfg or load_config()
    try:
        interval = int(getattr(cfg, "auto_sync_interval", PUBLIC_SYNC_INTERVAL_MINUTES) or PUBLIC_SYNC_INTERVAL_MINUTES)
    except (TypeError, ValueError):
        interval = PUBLIC_SYNC_INTERVAL_MINUTES
    return max(MIN_PUBLIC_SYNC_INTERVAL_MINUTES, min(interval, MAX_PUBLIC_SYNC_INTERVAL_MINUTES))


def _resolve_initial_public_sync_time(now: datetime, interval_minutes: int) -> datetime:
    interval = timedelta(minutes=interval_minutes)
    last_sync = get_last_successful_sync_time()

    if last_sync is None:
        target = now + timedelta(seconds=STARTUP_SYNC_GRACE_SECONDS)
        _add_log(
            f"Sync inicial MP diferido {STARTUP_SYNC_GRACE_SECONDS}s para priorizar el arranque."
        )
        return target

    due_at = last_sync + interval
    if due_at > now:
        _add_log(
            f"Sync inicial MP omitido: ultima actualizacion a las {last_sync.strftime('%H:%M')}. "
            f"Proximo ciclo a las {due_at.strftime('%H:%M')}."
        )
        return due_at

    elapsed_minutes = max(1, int((now - last_sync).total_seconds() // 60))
    target = now + timedelta(seconds=STARTUP_SYNC_GRACE_SECONDS)
    _add_log(
        f"Sync inicial MP diferido {STARTUP_SYNC_GRACE_SECONDS}s para priorizar el arranque "
        f"(ultima actualizacion hace {elapsed_minutes} min)."
    )
    return target


async def _auto_sync_loop():
    global _next_auto_sync_time

    _add_log("=== Auto-Sync Loop Iniciado ===")
    initial_cycle_pending = True

    while not _stop_event.is_set():
        cfg = load_config()
        interval = _get_public_sync_interval_minutes(cfg)
        
        if not cfg.auto_sync or not cfg.api_ticket:
            _next_auto_sync_time = None
            initial_cycle_pending = True
            await asyncio.sleep(60)
            continue

        now = datetime.now()
        if initial_cycle_pending:
            _next_auto_sync_time = _resolve_initial_public_sync_time(now, interval)
            initial_cycle_pending = False
            _add_log(f"Próximo auto-sync MP a las {_next_auto_sync_time.strftime('%H:%M')}")
        elif _next_auto_sync_time is None or _next_auto_sync_time <= now:
            _next_auto_sync_time = now + timedelta(minutes=interval)
            _add_log(f"Próximo auto-sync MP a las {_next_auto_sync_time.strftime('%H:%M')}")

        while not _stop_event.is_set():
            if datetime.now() >= _next_auto_sync_time:
                break
            await asyncio.sleep(5)

        if not _stop_event.is_set():
            if _last_successful_sync_time is None:
                _add_log("Ejecutando sync inicial MP diferido.")
                await _run_sync_once("startup_deferred")
            else:
                _add_log(f"Ejecutando sync periódico (cada {interval} min).")
                await _run_sync_once("periodic")
            _next_auto_sync_time = None


async def _run_sync_once(trigger_type: str):
    async with _sync_execution_lock:
        cfg = load_config()
        if not cfg.api_ticket:
            return

        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta.replace(hour=0, minute=0, second=0, microsecond=0)
        _add_log(
            "Auto-sync MP: buscando OCs del dia actual "
            f"({fecha_desde.strftime('%Y-%m-%d %H:%M')} - {fecha_hasta.strftime('%H:%M')})."
        )

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
                    if tipo == "done":
                        _mark_mp_sync_success()
                    break
            except queue.Empty:
                await asyncio.sleep(0.5)


def _private_sync_enabled(cfg) -> bool:
    return bool(
        cfg.smtp_user
        and cfg.smtp_password
        and cfg.imap_server
        and cfg.imap_port
    )

async def _private_sync_loop():
    global _next_private_sync_time

    _add_log("=== Auto-Sync Privado Loop Iniciado ===")
    last_mp_target_handled = None

    while not _private_sync_stop_event.is_set():
        cfg = load_config()
        interval = _get_public_sync_interval_minutes(cfg)

        if not cfg.auto_sync or not _private_sync_enabled(cfg):
            _next_private_sync_time = None
            last_mp_target_handled = None
            await asyncio.sleep(60)
            continue

        mp_target = _next_auto_sync_time
        if mp_target is None:
            _next_private_sync_time = None
            await asyncio.sleep(10)
            continue

        if last_mp_target_handled == mp_target:
            await asyncio.sleep(5)
            continue

        _next_private_sync_time = mp_target + timedelta(minutes=PRIVATE_SYNC_DELAY_MINUTES)

        if _next_private_sync_time > datetime.now():
            _add_log(
                f"Proximo auto-sync privado a las {_next_private_sync_time.strftime('%H:%M')} "
                f"({PRIVATE_SYNC_DELAY_MINUTES} min despues de MP)"
            )

        while not _private_sync_stop_event.is_set():
            if _next_auto_sync_time != mp_target:
                break
            if datetime.now() >= _next_private_sync_time:
                last_mp_target_handled = mp_target
                _add_log("Ejecutando auto-sync privado posterior al ciclo de MP.")
                await _run_private_sync_once("post_mp")
                break
            await asyncio.sleep(5)


async def _run_private_sync_once(trigger_type: str):
    async with _sync_execution_lock:
        cfg = load_config()
        if not _private_sync_enabled(cfg):
            return

        q = queue.Queue()

        def _worker():
            try:
                run_sync_privado(
                    smtp_user=cfg.smtp_user,
                    smtp_password=cfg.smtp_password,
                    imap_server=cfg.imap_server,
                    imap_port=cfg.imap_port,
                    imap_folder=cfg.imap_folder,
                    filter_from=cfg.imap_filter_from,
                    progress_queue=q,
                )
            except Exception as e:
                q.put({"type": "error", "message": str(e)})

        threading.Thread(target=_worker, daemon=True).start()

        while True:
            try:
                msg = q.get_nowait()
                tipo = msg.get("type")
                if tipo == "log":
                    _add_log(msg.get("message", ""))
                elif tipo in ("done", "error"):
                    _add_log(f"Auto-sync privado finalizado: {msg.get('message', '')}")
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
    global _auto_sync_task, _next_auto_sync_time
    _stop_event.set()
    _next_auto_sync_time = None
    if _auto_sync_task:
        _auto_sync_task.cancel()
        _auto_sync_task = None


def start_private_sync():
    """Inicia el loop de sincronizacion automatica de OCs privadas."""
    global _private_sync_task
    if _private_sync_task and not _private_sync_task.done():
        logger.info("Auto-sync privado ya estaba en ejecucion; se reutiliza la tarea existente.")
        return
    _private_sync_stop_event.clear()
    _private_sync_task = asyncio.create_task(_private_sync_loop())


def stop_private_sync():
    """Detiene el loop de sincronizacion automatica de OCs privadas."""
    global _private_sync_task, _next_private_sync_time
    _private_sync_stop_event.set()
    _next_private_sync_time = None
    if _private_sync_task:
        _private_sync_task.cancel()
        _private_sync_task = None


# ── Sincronización Ligera (cada 2 horas, solo estados) ──────────────────────

def get_next_light_sync_time():
    """Retorna la próxima hora de sincronización ligera."""
    global _next_light_sync_time
    return _next_light_sync_time


def get_last_successful_sync_time():
    """Retorna la hora de la ultima sincronizacion exitosa."""
    global _last_successful_sync_time
    return _last_successful_sync_time


def get_next_scheduled_sync_time():
    """Retorna la proxima sincronizacion programada entre MP, privadas y light-sync."""
    now = datetime.now()
    candidates = [
        sync_time
        for sync_time in (_next_private_sync_time, _next_auto_sync_time, _next_light_sync_time)
        if sync_time and sync_time > now
    ]
    return min(candidates) if candidates else None


def _calculate_next_light_sync():
    """Calcula la próxima hora de sync (cada 2 horas)."""
    now = datetime.now()
    # Próxima ejecución: siguiente múltiplo de 2 horas
    hour = now.hour

    next_hour = ((hour // 2) + 1) * 2
    next_base = now
    if next_hour >= 24:
        next_hour = 0
        next_base = now + timedelta(days=1)

    return next_base.replace(hour=next_hour, minute=0, second=0, microsecond=0)


async def _light_sync_loop():
    """Loop que ejecuta sincronización ligera cada 2 horas."""
    global _next_light_sync_time

    _add_log("=== Light Sync Loop Iniciado (cada 2 horas) ===")

    cfg = load_config()
    if cfg.api_ticket and not cfg.auto_sync:
        _add_log("Ejecutando light-sync inicial...")
        await _run_light_sync_once_tracked()
    elif cfg.api_ticket and cfg.auto_sync:
        _add_log("Light-sync inicial omitido: el auto-sync completo ya cubre el arranque.")

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
            await _run_light_sync_once_tracked()


async def _run_light_sync_once():
    """Ejecuta una sincronización ligera (solo estados, últimos 30 días)."""
    async with _sync_execution_lock:
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


async def _run_light_sync_once_tracked():
    """Ejecuta un light-sync y registra la hora al terminar exitosamente."""
    async with _sync_execution_lock:
        cfg = load_config()
        if not cfg.api_ticket:
            return

        _add_log("Light-sync: Actualizando estados de OCs (ultimos 30 dias)...")

        fecha_hasta = datetime.now()
        fecha_desde = fecha_hasta - timedelta(days=30)

        q = queue.Queue()
        completed_ok = False

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

        while True:
            try:
                msg = q.get_nowait()
                tipo = msg.get("type")
                if tipo == "log":
                    _add_log(msg.get("message", ""))
                elif tipo in ("done", "error"):
                    _add_log(f"Light-sync completado: {msg.get('message', '')}")
                    completed_ok = tipo == "done"
                    break
            except queue.Empty:
                await asyncio.sleep(0.5)

        if completed_ok:
            _mark_mp_sync_success()


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
