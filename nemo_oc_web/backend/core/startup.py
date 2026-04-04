"""
Inicialización del backend web: replica la secuencia de main.py de la app desktop.
"""
import logging
import sys
import os
from pathlib import Path

# Asegurar que nemo_oc/ esté en sys.path para importar app.*
_nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))

logger = logging.getLogger(__name__)


def initialize():
    """Inicializa DB y pre-carga todos los catálogos."""
    from app.config import (
        load_config, get_data_dir, get_config_dir, get_logs_dir,
        get_default_homo_path, get_default_maestra_path, get_default_cartera_path,
        get_default_correos_path, get_default_redsalud_homo_path, get_default_licitaciones_path,
    )
    from app.utils.logger import setup_logger

    get_data_dir()
    get_config_dir()
    get_logs_dir()

    config = load_config()
    setup_logger(config.log_level)

    logger.info("=" * 50)
    logger.info("NemoOC Web iniciando...")

    # Base de datos
    from app.db import initialize_db
    initialize_db()

    # Homologación CM
    try:
        from app.services.homologacion_service import get_homologacion_service
        from app.repositories.homologacion_repo import count_homologacion
        svc = get_homologacion_service()
        stats = count_homologacion()
        if stats["cm"] == 0:
            p = Path(config.homologacion_path) if config.homologacion_path else get_default_homo_path()
            if p.exists():
                cnt, _ = svc.cargar_homologacion_excel(str(p))
                logger.info(f"Homologación auto-importada: {cnt} registros.")
        if stats["sap"] == 0:
            p = Path(config.maestra_path) if config.maestra_path else get_default_maestra_path()
            if p.exists():
                cnt, _ = svc.cargar_maestra_sap(str(p))
                logger.info(f"Maestra SAP auto-importada: {cnt} registros.")
        svc.reload()
        logger.info("Homologación lista.")
    except Exception as e:
        logger.warning(f"Homologación: {e}")

    # Cartera
    try:
        from app.services.cartera_service import get_cartera_service
        from app.repositories.cartera_repo import count_cartera
        svc = get_cartera_service()
        if count_cartera() == 0:
            p = Path(config.cartera_path) if config.cartera_path else get_default_cartera_path()
            if p.exists():
                cnt, _ = svc.cargar_cartera_excel(str(p))
                logger.info(f"Cartera auto-importada: {cnt} registros.")
        svc.reload()
        logger.info(f"Cartera lista: {svc.get_count()} clientes.")
    except Exception as e:
        logger.warning(f"Cartera: {e}")

    # Email
    try:
        from app.services.email_service import get_email_service
        p = config.correos_path or str(get_default_correos_path())
        if Path(p).exists():
            ok, msg = get_email_service().cargar_correos(p)
            logger.info(f"EmailService: {msg}")
    except Exception as e:
        logger.warning(f"Email: {e}")

    # RedSalud
    try:
        from app.services.redsalud_homo_service import get_redsalud_homo_service
        svc = get_redsalud_homo_service()
        if svc.count() == 0:
            p = Path(config.redsalud_homo_path) if config.redsalud_homo_path else get_default_redsalud_homo_path()
            if p.exists():
                cnt, _ = svc.cargar_excel(str(p))
                logger.info(f"Homo RedSalud auto-importada: {cnt} registros.")
        svc.reload()
        logger.info(f"RedSalud lista: {svc.count()} productos.")
    except Exception as e:
        logger.warning(f"RedSalud: {e}")

    # Maestra Materiales
    try:
        from app.services.maestra_service import get_maestra_service
        svc = get_maestra_service()
        if svc.count() == 0:
            p = Path(config.maestra_path) if config.maestra_path else get_default_maestra_path()
            if p.exists():
                cnt, _ = svc.cargar_excel(str(p))
                logger.info(f"Maestra Materiales auto-importada: {cnt} registros.")
        svc.reload()
        logger.info(f"Maestra lista: {svc.count()} materiales.")
    except Exception as e:
        logger.warning(f"Maestra: {e}")

    # Licitaciones
    try:
        from app.services.licitaciones_service import get_licitaciones_service
        svc = get_licitaciones_service()
        if svc.count() == 0:
            p = Path(config.licitaciones_path) if config.licitaciones_path else get_default_licitaciones_path()
            if p.exists():
                cnt, _ = svc.importar_lic(str(p))
                logger.info(f"Licitaciones auto-importadas: {cnt} referencias.")
        svc.reload()
        logger.info(f"Licitaciones listas: {svc.count()} referencias.")
    except Exception as e:
        logger.warning(f"Licitaciones: {e}")

    logger.info("NemoOC Web listo.")
