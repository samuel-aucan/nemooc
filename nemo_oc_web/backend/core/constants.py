"""
Constantes, enums y tipos para evitar strings mágicos en todo el código.
"""
from enum import Enum

# MIME types permitidos para uploads de catálogos
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls (legacy)
}

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}

# Estados internos de OCs
class EstadoInterno(str, Enum):
    NUEVA = "Nueva"
    PROCESADA = "Procesada"
    INGRESADA = "Ingresada"
    PAGADA = "Pagada"
    CANCELADA = "Cancelada"


# Estados de homologación
class EstadoHomologacion(str, Enum):
    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    COMPLETA = "completa"


# Estados MP (Mercado Público)
class EstadoMP(str, Enum):
    ENVIADA = "Enviada a proveedor"
    ACEPTADA = "Aceptada"
    RECIBIDA = "Recibida"
    CANCELADA = "Cancelada"


# Tipos de OC
class TipoOC(str, Enum):
    CM = "CM"
    SE = "SE"


# Colores de tema
class ColorTheme(str, Enum):
    BLUE = "blue"
    GREEN = "emerald"
    PURPLE = "violet"
    PINK = "rose"
    AMBER = "amber"
    CYAN = "cyan"


def validate_mime_type(filename: str, mime_type: str) -> bool:
    """Valida MIME type y extensión de archivo subido."""
    import pathlib
    ext = pathlib.Path(filename).suffix.lower()
    return mime_type in ALLOWED_MIME_TYPES and ext in ALLOWED_EXTENSIONS
