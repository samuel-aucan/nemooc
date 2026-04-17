"""Bootstrap minimo para la nueva interfaz Qt de NemoOC."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import sys


_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.config import AppConfig, get_config_dir, get_data_dir, get_logs_dir, load_config
from app.db import initialize_db
from app.utils.logger import setup_logger


logger = logging.getLogger(__name__)


@dataclass
class SessionUser:
    """Sesion activa del usuario autenticado en la preview Qt."""

    user_id: int
    username: str
    display_name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role.strip().lower() == "admin"


@dataclass
class QtAppContext:
    """Contexto compartido por la nueva shell Qt."""

    config: AppConfig
    app_name: str = "NemoOC"
    app_subtitle: str = "Desktop Qt Preview"
    window_title: str = "NemoOC - Desktop Qt Preview"
    baseline_git: str = "2e22689"
    current_user: SessionUser | None = None


def bootstrap_qt_context() -> QtAppContext:
    """Inicializa directorios, configuracion, logger y base para la shell Qt."""
    get_data_dir()
    get_config_dir()
    get_logs_dir()

    config = load_config()
    setup_logger(config.log_level)

    logger.info("=" * 50)
    logger.info("NemoOC Qt preview iniciando...")

    initialize_db()

    return QtAppContext(config=config)
