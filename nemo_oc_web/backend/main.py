"""
NemoOC Web — Backend FastAPI.
Corre en puerto 8000. El frontend React (puerto 5173) hace proxy de /api.
"""
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa DB y catálogos al arrancar, e inicia auto-sync y light-sync."""
    initialize()
    from backend.core.tasks import start_auto_sync, stop_auto_sync, start_light_sync, stop_light_sync
    start_auto_sync()
    start_light_sync()
    yield
    stop_auto_sync()
    stop_light_sync()


app = FastAPI(
    title="NemoOC API",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"],
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


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "NemoOC Web"}


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

    _assets = _fe / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="fe_assets")

    @app.get("/{full_path:path}")
    async def _spa(full_path: str):
        target = _fe / full_path
        if target.exists() and target.is_file():
            return _FR(str(target))
        return _FR(str(_fe / "index.html"))
