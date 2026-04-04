"""Modelos para referencias de licitaciones y sugerencias de productos."""
from dataclasses import dataclass


@dataclass
class LicitacionRef:
    descripcion_comprador: str
    descripcion_norm: str
    producto_code_old: str = ""
    itemcode_sap: str = ""
    descripcion_nemo: str = ""
    frecuencia: int = 1
    origen_archivo: str = ""
    rut_comprador: str = ""


@dataclass
class SugerenciaProducto:
    itemcode_sap: str
    descripcion_sap: str
    descripcion_match: str  # descripcion del comprador que matcheo
    frecuencia: int = 1
    score: float = 0.0  # similitud 0.0-1.0: fracción de tokens que coinciden
