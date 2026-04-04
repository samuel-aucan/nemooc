"""Dataclass para ítem de homologación (catálogo CM)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class HomologacionItem:
    codigo_mp: str
    itemcode_sap: str
    descripcion_sap: Optional[str] = None
    factor_empaque: float = 1.0
    activo: bool = True
    origen_archivo: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class SapArticulo:
    itemcode_sap: str
    descripcion_sap: Optional[str] = None
    activo: bool = True
    origen_archivo: str = ""
    created_at: str = ""
    updated_at: str = ""
