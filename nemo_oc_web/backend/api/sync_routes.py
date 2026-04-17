"""
Endpoints de sincronización con Mercado Público y Gmail.
Usa SSE (Server-Sent Events) para transmitir progreso en tiempo real.
"""
import asyncio
import json
import os
import queue
import sys
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

_nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))

from app.config import load_config

from .schemas import SyncMpIn, SyncGmailIn, SyncStartOut, ArtikosSyncIn, ArtikosSyncOut

router = APIRouter(prefix="/api/sync", tags=["sync"])

# Almacena queues activas: sync_id → queue.Queue
_active: Dict[str, queue.Queue] = {}

# Log global para la memoria de auto-sync y manual sync
GLOBAL_SYNC_LOGS = []

def _add_global_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    GLOBAL_SYNC_LOGS.append({"time": ts, "message": msg})
    if len(GLOBAL_SYNC_LOGS) > 300:
        GLOBAL_SYNC_LOGS.pop(0)

@router.get("/logs")
def get_global_logs():
    return {"logs": GLOBAL_SYNC_LOGS}

@router.get("/status")
def get_sync_status():
    # Retorna si hay alguna sincronización activa (útil para el frontend)
    from backend.core.tasks import get_next_light_sync_time

    running = len(_active) > 0
    next_light_sync = get_next_light_sync_time()
    next_light_sync_str = next_light_sync.isoformat() if next_light_sync else None

    return {
        "running": running,
        "active_tasks": list(_active.keys()),
        "next_light_sync": next_light_sync_str,
    }


# ── Mercado Público ──────────────────────────────────────────────────────────
MAX_SYNC_DAYS = int(os.getenv("NEMOOC_SYNC_MAX_DAYS", "90"))

@router.post("/mercado-publico", response_model=SyncStartOut)
def start_sync_mp(body: SyncMpIn):
    from app.services.sync_service import run_sync

    cfg = load_config()
    if not cfg.api_ticket:
        raise HTTPException(400, detail="API ticket no configurado")

    try:
        fecha_desde = datetime.strptime(body.fecha_desde, "%Y-%m-%d")
        fecha_hasta = datetime.strptime(body.fecha_hasta, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

    # Validar que el rango no exceda el máximo de días (protección contra DoS)
    days_range = (fecha_hasta - fecha_desde).days
    if days_range > MAX_SYNC_DAYS:
        raise HTTPException(
            400,
            detail=f"El rango de fechas no puede exceder {MAX_SYNC_DAYS} días. "
                   f"Solicitaste {days_range} días.",
        )

    sync_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    _active[sync_id] = q

    def _worker():
        try:
            run_sync(
                ticket=cfg.api_ticket,
                codigo_empresa=cfg.codigo_empresa,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                progress_queue=q,
                solo_cm=body.solo_cm,
            )
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    threading.Thread(target=_worker, daemon=True).start()
    return SyncStartOut(sync_id=sync_id)


@router.get("/mercado-publico/{sync_id}/progress")
async def sync_mp_progress(sync_id: str):
    q = _active.get(sync_id)
    if q is None:
        raise HTTPException(404, detail="Sync no encontrado")

    async def generator():
        try:
            while True:
                try:
                    msg = q.get_nowait()
                    if msg["type"] in ("log", "error", "done"):
                        _add_global_log(msg.get("message", "---"))
                    yield {"event": msg["type"], "data": json.dumps(msg)}
                    if msg["type"] in ("done", "error"):
                        _active.pop(sync_id, None)
                        break
                except queue.Empty:
                    # heartbeat para mantener la conexión viva
                    yield {"event": "heartbeat", "data": ""}
                    await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            _active.pop(sync_id, None)

    return EventSourceResponse(generator())


@router.post("/mp-estados-ligero", response_model=SyncStartOut)
def start_sync_mp_light(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    """
    Sincronización ligera: solo actualiza estado_mp de OCs existentes.
    Por defecto cubre los últimos 30 días; acepta rango personalizado.
    """
    from app.services.sync_service import start_sync_light_thread
    from datetime import timedelta

    cfg = load_config()
    if not cfg.api_ticket:
        raise HTTPException(400, detail="API ticket no configurado")

    sync_id = str(uuid.uuid4())

    _fecha_hasta = datetime.now()
    _fecha_desde = _fecha_hasta - timedelta(days=30)

    if fecha_hasta:
        try:
            _fecha_hasta = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, detail="fecha_hasta inválida. Use YYYY-MM-DD")
    if fecha_desde:
        try:
            _fecha_desde = datetime.strptime(fecha_desde, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, detail="fecha_desde inválida. Use YYYY-MM-DD")

    q = start_sync_light_thread(
        ticket=cfg.api_ticket,
        codigo_empresa=cfg.codigo_empresa,
        fecha_desde=_fecha_desde,
        fecha_hasta=_fecha_hasta,
    )
    _active[sync_id] = q
    return SyncStartOut(sync_id=sync_id)


@router.get("/mp-estados-ligero/{sync_id}/progress")
async def sync_mp_light_progress(sync_id: str):
    """SSE stream para la sincronización ligera."""
    q = _active.get(sync_id)
    if q is None:
        raise HTTPException(404, detail="Sync no encontrado")

    async def generator():
        try:
            while True:
                try:
                    msg = q.get_nowait()
                    if msg["type"] in ("log", "error", "done"):
                        _add_global_log(msg.get("message", "---"))
                    yield {"event": msg["type"], "data": json.dumps(msg)}
                    if msg["type"] in ("done", "error"):
                        _active.pop(sync_id, None)
                        break
                except queue.Empty:
                    yield {"event": "heartbeat", "data": ""}
                    await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            _active.pop(sync_id, None)

    return EventSourceResponse(generator())


@router.post("/test-api")
def test_api():
    from app.services.mp_api_service import MercadoPublicoAPI
    cfg = load_config()
    if not cfg.api_ticket:
        return {"ok": False, "message": "API ticket no configurado"}

    try:
        api = MercadoPublicoAPI(ticket=cfg.api_ticket, codigo_empresa=cfg.codigo_empresa)
        ok, msg = api.probar_conexion_rapida()
        return {"ok": ok, "message": msg}
    except Exception as e:
        return {"ok": False, "message": f"Error interno probando API: {e}"}


# ── Gmail / OCs Privadas ─────────────────────────────────────────────────────

@router.post("/gmail", response_model=SyncStartOut)
def start_sync_gmail(body: SyncGmailIn):
    from app.services.sync_privado_service import run_sync_privado

    cfg = load_config()
    if not cfg.smtp_user or not cfg.smtp_password:
        raise HTTPException(400, detail="Credenciales Gmail no configuradas")

    sync_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    _active[sync_id] = q

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
    return SyncStartOut(sync_id=sync_id)


@router.get("/gmail/{sync_id}/progress")
async def sync_gmail_progress(sync_id: str):
    q = _active.get(sync_id)
    if q is None:
        raise HTTPException(404, detail="Sync no encontrado")

    async def generator():
        try:
            while True:
                try:
                    msg = q.get_nowait()
                    if msg["type"] in ("log", "error", "done"):
                        _add_global_log(msg.get("message", "---"))
                    yield {"event": msg["type"], "data": json.dumps(msg)}
                    if msg["type"] in ("done", "error"):
                        _active.pop(sync_id, None)
                        break
                except queue.Empty:
                    yield {"event": "heartbeat", "data": ""}
                    await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            _active.pop(sync_id, None)

    return EventSourceResponse(generator())


# ── Artikos (scraping portal web) ────────────────────────────────────────────

@router.post("/artikos", response_model=ArtikosSyncOut)
def importar_artikos(body: ArtikosSyncIn):
    from app.services.artikos_scraper import scrape_oc
    from app.repositories import oc_repository

    if not body.url or "artikos" not in body.url.lower():
        raise HTTPException(400, detail="URL no válida. Debe ser un link del portal Artikos.")

    try:
        oc, lineas = scrape_oc(body.url)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(502, detail=f"Error accediendo al portal Artikos: {e}")

    existentes = oc_repository.get_existing_codes()
    if oc.codigo_oc in existentes:
        return ArtikosSyncOut(
            ok=True,
            codigo_oc=oc.codigo_oc,
            nombre_organismo=oc.nombre_organismo,
            cantidad_lineas=oc.cantidad_lineas,
            message="OC ya existe en la base de datos",
        )

    oc_repository.save_oc(oc, lineas)
    _add_global_log(f"OC Artikos importada: {oc.codigo_oc} — {oc.nombre_organismo}")

    return ArtikosSyncOut(
        ok=True,
        codigo_oc=oc.codigo_oc,
        nombre_organismo=oc.nombre_organismo,
        cantidad_lineas=len(lineas),
        message=f"OC {oc.codigo_oc} importada correctamente ({len(lineas)} líneas)",
    )
