"""
NEMONKEY - Backend FastAPI.
Corre en puerto 8000. El frontend React (puerto 5173) hace proxy de /api.
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Asegurar que nemo_oc/ esté en sys.path
if getattr(sys, 'frozen', False):
    _nemo_oc_dir = Path(sys._MEIPASS) / "nemo_oc"
else:
    _nemo_oc_dir = Path(__file__).parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))

from backend.core.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
    get_session_secret,
    require_auth,
    should_secure_cookies,
)
from backend.api.auth_routes import router as auth_router
from backend.core.startup import initialize
from backend.api.oc_routes import router as oc_router
from backend.api.sync_routes import router as sync_router
from backend.api.config_routes import router as config_router
from backend.api.catalog_routes import router as catalog_router
from backend.api.holdings_routes import router as holdings_router
from backend.api.gd_routes import router as gd_router
from backend.api.poc_sse import router as poc_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa DB y catálogos al arrancar, e inicia auto-sync y light-sync."""
    initialize()
    from backend.core.tasks import (
        start_auto_sync,
        stop_auto_sync,
        start_private_sync,
        stop_private_sync,
        start_light_sync,
        stop_light_sync,
    )
    from app.services.notification_scheduler_service import (
        start_notification_scheduler,
        stop_notification_scheduler,
    )
    start_auto_sync()
    start_private_sync()
    start_light_sync()
    start_notification_scheduler()
    yield
    stop_auto_sync()
    stop_private_sync()
    stop_light_sync()
    stop_notification_scheduler()


app = FastAPI(
    title="NEMONKEY API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret(),
    session_cookie=SESSION_COOKIE_NAME,
    same_site="lax",
    https_only=should_secure_cookies(),
    max_age=SESSION_MAX_AGE,
)


# CORS: en producción setear CORS_ORIGINS="https://tu-app.vercel.app,https://otro.com"
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"]
_extra = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
_all_origins = _default_origins + _extra

app.add_middleware(
    CORSMiddleware,
    allow_origins=_all_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(oc_router, dependencies=[Depends(require_auth)])
app.include_router(sync_router, dependencies=[Depends(require_auth)])
app.include_router(config_router, dependencies=[Depends(require_auth)])
app.include_router(catalog_router, dependencies=[Depends(require_auth)])
app.include_router(holdings_router, dependencies=[Depends(require_auth)])
app.include_router(gd_router, dependencies=[Depends(require_auth)])
app.include_router(poc_router)  # POC-C: sin auth para facilitar el test


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "app": "NEMONKEY"}


@app.get("/api/v1/debug/ocs")
def debug_ocs():
    """Endpoint temporal de diagnóstico — eliminar después."""
    import traceback
    try:
        from backend.core.repo_selector import oc_repo as _repo
        ocs, total = _repo.get_all_ocs()
        return {"ok": True, "count": total, "first": ocs[0].codigo_oc if ocs else None}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


@app.get("/api/v1/debug/ocs-full")
def debug_ocs_full():
    """Simula list_ocs completo sin auth para diagnosticar 500."""
    import traceback
    try:
        from backend.core.repo_selector import oc_repo as _repo
        from backend.api.oc_routes import _enrich_oc, OrdenCompraOut
        ocs, _ = _repo.get_all_ocs()
        step = "get_all_ocs OK"
        holdings_map = _repo.get_holdings_map()
        step = "get_holdings_map OK"
        enriched = []
        for i, oc in enumerate(ocs[:5]):
            try:
                enriched.append(OrdenCompraOut(**_enrich_oc(oc, holdings_map)).dict())
            except Exception as e:
                return {"ok": False, "step": f"enrich OC #{i} {oc.codigo_oc}", "error": str(e), "traceback": traceback.format_exc()}
        return {"ok": True, "step": step, "count": len(ocs), "sample": enriched}
    except Exception as e:
        return {"ok": False, "step": step if 'step' in dir() else "unknown", "error": str(e), "traceback": traceback.format_exc()}


# ── Servir frontend React (solo en .exe; en dev Vite lo sirve) ───────────────
def _fe_dist() -> Optional[Path]:
    if getattr(sys, 'frozen', False):
        p = Path(sys._MEIPASS) / "frontend_dist"
        return p if p.exists() else None
    return None


_fe = _fe_dist()
if _fe:
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse as _FR

    _NO_CACHE_HEADERS = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    class _NoCacheStaticFiles(StaticFiles):
        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            if getattr(response, "status_code", 200) == 200:
                for header, value in _NO_CACHE_HEADERS.items():
                    response.headers[header] = value
            return response

    _assets = _fe / "assets"
    if _assets.exists():
        app.mount("/assets", _NoCacheStaticFiles(directory=str(_assets)), name="fe_assets")

    @app.get("/{full_path:path}")
    async def _spa(full_path: str):
        target = _fe / full_path
        if target.exists() and target.is_file():
            return _FR(str(target), headers=_NO_CACHE_HEADERS)
        return _FR(str(_fe / "index.html"), headers=_NO_CACHE_HEADERS)
