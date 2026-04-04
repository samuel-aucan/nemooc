"""Configuración del logger rotativo para NemoOC."""
import logging
from logging.handlers import RotatingFileHandler
from app.config import get_logs_dir


def setup_logger(level: str = "INFO") -> None:
    log_file = get_logs_dir() / "app.log"
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Evitar duplicar handlers si se llama más de una vez
    if root.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Archivo rotativo: 1MB × 3 archivos
    fh = RotatingFileHandler(
        str(log_file), maxBytes=1_048_576, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Consola (útil en modo desarrollo)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)
