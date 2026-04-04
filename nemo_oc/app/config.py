"""
Configuración portable de la aplicación NemoOC.
get_base_dir() resuelve correctamente tanto en desarrollo como empaquetado con PyInstaller.
"""

import sys
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    """
    Retorna el directorio raíz de la aplicación.
    - En PyInstaller frozen: directorio donde está el .exe
    - En desarrollo: directorio raíz del proyecto (nemo_oc/)
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    p = get_base_dir() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_dir() -> Path:
    p = get_base_dir() / "config"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_logs_dir() -> Path:
    p = get_base_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_assets_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "assets"  # type: ignore
    return get_base_dir() / "assets"


def get_catalogs_dir() -> Path:
    p = get_base_dir() / "catalogs"
    p.mkdir(parents=True, exist_ok=True)
    return p


HOMOLOGACION_FILENAME = "HOMOLOGACION.xlsx"
MAESTRA_FILENAME = "MAESTRA DE MATERIALES (PBI).xlsx"
CARTERA_FILENAME = "CARTERA(PBI).xlsx"


def get_default_homo_path() -> Path:
    return get_catalogs_dir() / HOMOLOGACION_FILENAME


def get_default_maestra_path() -> Path:
    return get_catalogs_dir() / MAESTRA_FILENAME


def get_default_cartera_path() -> Path:
    return get_catalogs_dir() / CARTERA_FILENAME


CORREOS_FILENAME = "CORREOS.xlsx"
REDSALUD_HOMO_FILENAME = "HOMO RED SALUD.xlsx"


def get_default_correos_path() -> Path:
    return get_catalogs_dir() / CORREOS_FILENAME


def get_default_redsalud_homo_path() -> Path:
    return get_catalogs_dir() / REDSALUD_HOMO_FILENAME


LICITACIONES_FILENAME = "lic.xlsx"


def get_default_licitaciones_path() -> Path:
    return get_catalogs_dir() / LICITACIONES_FILENAME


SETTINGS_FILE = get_config_dir() / "settings.json"


@dataclass
class AppConfig:
    api_ticket: str = ""
    codigo_empresa: str = "227926"
    rut_proveedor: str = "76.215.260-6"
    homologacion_path: str = ""
    maestra_path: str = ""
    cartera_path: str = ""
    correos_path: str = ""
    theme: str = "dark"
    color_theme: str = "blue"
    auto_sync: bool = False
    auto_sync_days: int = 7
    auto_sync_interval: int = 15
    last_sync: str = ""
    log_level: str = "INFO"
    smtp_host: str = "smtp.office365.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_enabled: bool = False
    redsalud_homo_path: str = ""
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    imap_folder: str = "INBOX"
    imap_filter_subject: str = "ORDEN DE COMPRA"
    licitaciones_path: str = ""
    sap_columns: list[str] = field(default_factory=lambda: ["itemcode", "descripcion", "cantidad", "precio"])


def load_config() -> AppConfig:
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            cfg = AppConfig()
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            return cfg
    except Exception as e:
        logger.warning(f"No se pudo cargar configuración: {e}")
    return AppConfig()


def save_config(cfg: AppConfig) -> None:
    try:
        SETTINGS_FILE.write_text(
            json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"No se pudo guardar configuración: {e}")
