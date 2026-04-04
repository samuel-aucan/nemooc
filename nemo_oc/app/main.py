"""
NemoOC — Punto de entrada principal.
Inicializa logger, base de datos, configuración y lanza la interfaz.
"""
import sys
import os
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en el path
# (necesario cuando se lanza como app/main.py en desarrollo)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.utils.logger import setup_logger
from app.config import load_config, get_data_dir, get_config_dir, get_logs_dir


def main():
    # 1. Crear directorios necesarios
    get_data_dir()
    get_config_dir()
    get_logs_dir()

    # 2. Cargar configuración
    config = load_config()

    # 3. Iniciar logger
    setup_logger(config.log_level)

    import logging
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("NemoOC iniciando...")

    # 4. Inicializar base de datos
    try:
        from app.db import initialize_db
        initialize_db()
    except Exception as e:
        import tkinter.messagebox as mb
        mb.showerror("Error de base de datos",
                     f"No se pudo inicializar la base de datos:\n{e}\n\n"
                     "Verifique que tenga permisos de escritura en la carpeta de la aplicación.")
        sys.exit(1)

    # 5. Pre-cargar catálogo de homologación
    try:
        from app.services.homologacion_service import get_homologacion_service
        from app.config import get_default_homo_path, get_default_maestra_path
        from app.repositories.homologacion_repo import count_homologacion

        svc = get_homologacion_service()
        stats = count_homologacion()

        # Auto-importar desde catalogs/ si la BD está vacía
        if stats["cm"] == 0:
            homo_path = Path(config.homologacion_path) if config.homologacion_path else get_default_homo_path()
            if homo_path.exists():
                logger.info(f"BD vacía — importando homologación desde {homo_path.name}...")
                count, _ = svc.cargar_homologacion_excel(str(homo_path))
                config.homologacion_path = str(homo_path)
                logger.info(f"Homologación auto-importada: {count} registros.")

        if stats["sap"] == 0:
            maestra_path = Path(config.maestra_path) if config.maestra_path else get_default_maestra_path()
            if maestra_path.exists():
                logger.info(f"BD vacía — importando Maestra SAP desde {maestra_path.name}...")
                count, _ = svc.cargar_maestra_sap(str(maestra_path))
                config.maestra_path = str(maestra_path)
                logger.info(f"Maestra SAP auto-importada: {count} registros.")

        svc.reload()
        logger.info("Catálogo de homologación listo.")
    except Exception as e:
        logger.warning(f"No se pudo pre-cargar homologación: {e}")

    # 5b. Pre-cargar cartera de clientes
    try:
        from app.services.cartera_service import get_cartera_service
        from app.config import get_default_cartera_path
        from app.repositories.cartera_repo import count_cartera

        cartera_svc = get_cartera_service()
        if count_cartera() == 0:
            cartera_path = Path(config.cartera_path) if config.cartera_path else get_default_cartera_path()
            if cartera_path.exists():
                logger.info(f"BD vacía — importando cartera desde {cartera_path.name}...")
                cnt, _ = cartera_svc.cargar_cartera_excel(str(cartera_path))
                config.cartera_path = str(cartera_path)
                logger.info(f"Cartera auto-importada: {cnt} registros.")
        cartera_svc.reload()
        logger.info(f"Cartera lista: {cartera_svc.get_count()} clientes.")
    except Exception as e:
        logger.warning(f"No se pudo pre-cargar cartera: {e}")

    # 5c. Pre-cargar servicio de email
    try:
        from app.services.email_service import get_email_service
        from app.config import get_default_correos_path
        _correos_path = config.correos_path or str(get_default_correos_path())
        if Path(_correos_path).exists():
            ok, msg = get_email_service().cargar_correos(_correos_path)
            logger.info(f"EmailService: {msg}")
        else:
            logger.info("EmailService: CORREOS.xlsx no encontrado — notificaciones inactivas")
    except Exception as e:
        logger.warning(f"No se pudo pre-cargar EmailService: {e}")

    # 5d. Pre-cargar homologación RedSalud
    try:
        from app.services.redsalud_homo_service import get_redsalud_homo_service
        from app.config import get_default_redsalud_homo_path

        rs_svc = get_redsalud_homo_service()
        if rs_svc.count() == 0:
            rs_path = Path(config.redsalud_homo_path) if config.redsalud_homo_path else get_default_redsalud_homo_path()
            if rs_path.exists():
                logger.info(f"BD vacía — importando homologación RedSalud desde {rs_path.name}...")
                cnt, _ = rs_svc.cargar_excel(str(rs_path))
                config.redsalud_homo_path = str(rs_path)
                logger.info(f"Homo RedSalud auto-importada: {cnt} registros.")
        rs_svc.reload()
        logger.info(f"Homo RedSalud lista: {rs_svc.count()} productos.")
    except Exception as e:
        logger.warning(f"No se pudo pre-cargar homo RedSalud: {e}")

    # 5e. Pre-cargar Maestra de Materiales (completa, con codigo historico)
    try:
        from app.services.maestra_service import get_maestra_service
        from app.config import get_default_maestra_path

        maestra_svc = get_maestra_service()
        if maestra_svc.count() == 0:
            maestra_path = Path(config.maestra_path) if config.maestra_path else get_default_maestra_path()
            if maestra_path.exists():
                logger.info(f"BD vacía — importando Maestra Materiales desde {maestra_path.name}...")
                cnt, _ = maestra_svc.cargar_excel(str(maestra_path))
                logger.info(f"Maestra Materiales auto-importada: {cnt} registros.")
        maestra_svc.reload()
        logger.info(f"Maestra Materiales lista: {maestra_svc.count()} materiales.")
    except Exception as e:
        logger.warning(f"No se pudo pre-cargar Maestra Materiales: {e}")

    # 5f. Pre-cargar licitaciones referencia
    try:
        from app.services.licitaciones_service import get_licitaciones_service
        from app.config import get_default_licitaciones_path

        lic_svc = get_licitaciones_service()
        if lic_svc.count() == 0:
            lic_path = Path(config.licitaciones_path) if config.licitaciones_path else get_default_licitaciones_path()
            if lic_path.exists():
                logger.info(f"BD vacía — importando Licitaciones desde {lic_path.name}...")
                cnt, _ = lic_svc.importar_licsccc(str(lic_path))
                logger.info(f"Licitaciones auto-importadas: {cnt} referencias.")
        lic_svc.reload()
        logger.info(f"Licitaciones listas: {lic_svc.count()} referencias.")
    except Exception as e:
        logger.warning(f"No se pudo pre-cargar licitaciones: {e}")

    # 6. Lanzar interfaz
    try:
        from app.ui.app_window import AppWindow
        app = AppWindow(config)
        app.mainloop()
    except Exception as e:
        logger.exception(f"Error fatal en la UI: {e}")
        raise


if __name__ == "__main__":
    main()
