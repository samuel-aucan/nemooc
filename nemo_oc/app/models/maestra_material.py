"""Modelo de material de la Maestra SAP."""
from dataclasses import dataclass


@dataclass
class MaestraMaterial:
    itemcode_sap: str
    descripcion: str = ""
    codigo_historico: str = ""
    grupo: str = ""
    categoria: str = ""
    cant_display: float = 0.0
    cant_caja_master: float = 0.0
    origen_archivo: str = ""
    created_at: str = ""
    updated_at: str = ""
