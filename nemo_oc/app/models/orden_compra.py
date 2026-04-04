"""Dataclass para cabecera de Orden de Compra."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OrdenCompra:
    codigo_oc: str
    nombre_oc: str = ""
    codigo_estado_mp: int = 0
    estado_mp: str = ""
    codigo_tipo: str = ""
    tipo_oc: str = ""
    fecha_creacion: str = ""
    fecha_envio: str = ""
    fecha_aceptacion: str = ""
    fecha_cancelacion: str = ""
    fecha_ultima_modificacion: str = ""
    total_neto: float = 0.0
    impuestos: float = 0.0
    total: float = 0.0
    porcentaje_iva: float = 0.0
    descuentos: float = 0.0
    cargos: float = 0.0
    moneda: str = "CLP"
    codigo_organismo: str = ""
    nombre_organismo: str = ""
    rut_unidad: str = ""
    codigo_unidad: str = ""
    nombre_unidad: str = ""
    direccion_unidad: str = ""
    comuna_unidad: str = ""
    region_unidad: str = ""
    codigo_proveedor: str = ""
    nombre_proveedor: str = ""
    rut_proveedor: str = ""
    cliente_sap_sugerido: str = ""
    cantidad_lineas: int = 0
    estado_interno: str = "Nueva"
    fecha_ingreso: Optional[str] = None
    notas: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
