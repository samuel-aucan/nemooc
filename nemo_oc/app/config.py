"""
Configuración portable de la aplicación NemoOC.
get_base_dir() resuelve correctamente tanto en desarrollo como empaquetado con PyInstaller.
"""

import os
import sys
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    """
    Retorna el directorio raíz de la aplicación.
    - Si existe NEMOOC_BASE_DIR: usa esa ruta explicitamente
    - En PyInstaller frozen: directorio donde está el .exe
    - En desarrollo: directorio raíz del proyecto (nemo_oc/)
    """
    env_base_dir = os.getenv("NEMOOC_BASE_DIR", "").strip()
    if env_base_dir:
        return Path(env_base_dir).expanduser()
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
DEFAULT_SETTINGS_FILE = get_config_dir() / "default_settings.json"


class AppConfigSchema(BaseModel):
    """Validación con Pydantic para configuración."""
    auth_enabled: bool = False
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
    auto_sync_interval: int = 5
    last_sync: str = ""
    log_level: str = "INFO"
    smtp_host: str = "smtp.office365.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_enabled: bool = False
    notification_cc_email: str = "samuel.belmar@nemochile.cl"
    redsalud_homo_path: str = ""
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    imap_folder: str = "INBOX"
    imap_filter_from: str = "ordenesdecompra@nemochile.cl"
    licitaciones_path: str = ""
    sap_columns: list[str] = ["itemcode", "vta", "cantidad_sap", "precio_sap"]
    sap_global_columns: list[str] = ["itemcode", "vta", "cantidad_sap", "precio_sap"]
    oc_list_columns: list[str] = ["codigo_oc", "tipo_oc", "estado_mp", "estado_interno", "fecha_envio", "nombre_organismo", "cliente_sap_sugerido", "cartera", "vendedor", "total", "cantidad_lineas"]

    @field_validator("smtp_port", "imap_port", "auto_sync_days", "auto_sync_interval")
    @classmethod
    def validate_numbers(cls, v: int, info) -> int:
        if info.field_name in ("smtp_port", "imap_port"):
            if not (1 <= v <= 65535):
                raise ValueError(f"{info.field_name} debe estar entre 1 y 65535")
        return v

    model_config = {"extra": "ignore"}


@dataclass
class AppConfig:
    auth_enabled: bool = False
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
    auto_sync_interval: int = 5
    last_sync: str = ""
    log_level: str = "INFO"
    smtp_host: str = "smtp.office365.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_enabled: bool = False
    notification_cc_email: str = "samuel.belmar@nemochile.cl"
    redsalud_homo_path: str = ""
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    imap_folder: str = "INBOX"
    imap_filter_from: str = "ordenesdecompra@nemochile.cl"
    licitaciones_path: str = ""
    sap_columns: list[str] = field(default_factory=lambda: ["itemcode", "vta", "cantidad_sap", "precio_sap"])
    sap_global_columns: list[str] = field(default_factory=lambda: ["itemcode", "vta", "cantidad_sap", "precio_sap"])
    oc_list_columns: list[str] = field(default_factory=lambda: [
        "codigo_oc",
        "vta",
        "tipo_oc",
        "estado_mp",
        "estado_interno",
        "fecha_envio",
        "nombre_organismo",
        "cliente_sap_sugerido",
        "cartera",
        "vendedor",
        "total",
        "cantidad_lineas",
    ])


def _config_from_dict(data: dict) -> AppConfig:
    cfg = AppConfig()
    for k, v in data.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    return cfg


def _load_config_file(path: Path) -> AppConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    # Validar con Pydantic antes de convertir a AppConfig
    try:
        AppConfigSchema(**data)
    except Exception as e:
        logger.warning(f"Validación de configuración: {e}")
    return _config_from_dict(data)


def _resolve_portable_catalog_path(saved_path: str, default_path: Path) -> str:
    raw_path = (saved_path or "").strip()
    default_path = default_path.resolve()

    if raw_path:
        candidate = Path(raw_path).expanduser()
        if candidate.exists():
            return str(candidate)

        relative_candidate = (get_base_dir() / raw_path).resolve()
        if relative_candidate.exists():
            return str(relative_candidate)

        if candidate.name and candidate.name.casefold() == default_path.name.casefold() and default_path.exists():
            return str(default_path)

    if default_path.exists():
        return str(default_path)
    return raw_path


def _normalize_portable_catalog_paths(cfg: AppConfig) -> AppConfig:
    cfg.homologacion_path = _resolve_portable_catalog_path(cfg.homologacion_path, get_default_homo_path())
    cfg.maestra_path = _resolve_portable_catalog_path(cfg.maestra_path, get_default_maestra_path())
    cfg.cartera_path = _resolve_portable_catalog_path(cfg.cartera_path, get_default_cartera_path())
    cfg.correos_path = _resolve_portable_catalog_path(cfg.correos_path, get_default_correos_path())
    cfg.redsalud_homo_path = _resolve_portable_catalog_path(cfg.redsalud_homo_path, get_default_redsalud_homo_path())
    cfg.licitaciones_path = _resolve_portable_catalog_path(cfg.licitaciones_path, get_default_licitaciones_path())
    return cfg


def _apply_env_overrides(cfg: AppConfig) -> AppConfig:
    """
    Las variables de entorno tienen prioridad sobre settings.json para campos
    sensibles. Permite mantener los secretos FUERA del repositorio (que es
    público) y configurarlos solo en el entorno de despliegue (Railway).
    """
    env_map = {
        "NEMOOC_API_TICKET": "api_ticket",
        "NEMOOC_CODIGO_EMPRESA": "codigo_empresa",
        "NEMOOC_SMTP_USER": "smtp_user",
        "NEMOOC_SMTP_PASSWORD": "smtp_password",
        "NEMOOC_IMAP_SERVER": "imap_server",
    }
    for env_key, field_name in env_map.items():
        value = os.getenv(env_key)
        if value:  # solo si está definida y no vacía
            setattr(cfg, field_name, value)
    return cfg


def load_config() -> AppConfig:
    try:
        if SETTINGS_FILE.exists():
            return _apply_env_overrides(_normalize_portable_catalog_paths(_load_config_file(SETTINGS_FILE)))
        if DEFAULT_SETTINGS_FILE.exists():
            cfg = _normalize_portable_catalog_paths(_load_config_file(DEFAULT_SETTINGS_FILE))
            save_config(cfg)
            logger.info(f"Configuracion inicial creada desde plantilla: {DEFAULT_SETTINGS_FILE}")
            return _apply_env_overrides(cfg)
    except Exception as e:
        logger.warning(f"No se pudo cargar configuración: {e}")
    return _apply_env_overrides(_normalize_portable_catalog_paths(AppConfig()))


def save_config(cfg: AppConfig) -> None:
    try:
        SETTINGS_FILE.write_text(
            json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"No se pudo guardar configuración: {e}")
