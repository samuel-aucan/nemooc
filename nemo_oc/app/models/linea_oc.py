"""Dataclass para línea de detalle de Orden de Compra."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class LineaOC:
    codigo_oc: str
    correlativo: int
    codigo_categoria: int = 0
    categoria: str = ""
    codigo_producto_api: str = ""
    codigo_mp: Optional[str] = None
    producto: str = ""
    especificacion_comprador: str = ""
    especificacion_proveedor: str = ""
    cantidad: float = 0.0
    unidad: str = ""
    moneda: str = "CLP"
    precio_neto: float = 0.0
    total_cargos: float = 0.0
    total_descuentos: float = 0.0
    total_impuestos: float = 0.0
    total: float = 0.0
    factor_empaque: float = 1.0
    cantidad_sap: Optional[float] = None
    precio_sap: Optional[float] = None
    sap_mode: Optional[str] = None
    sap_mode_origen: Optional[str] = None
    sap_values_origen: Optional[str] = None
    sap_values_updated_at: str = ""
    sap_values_updated_by_user_id: Optional[int] = None
    sap_values_updated_by_username: str = ""
    itemcode_sap: Optional[str] = None
    descripcion_sap: Optional[str] = None
    estado_homologacion: str = "pendiente"
    sap_mode_sugerido: Optional[str] = None
    sap_mode_historial_total: int = 0
    sap_mode_historial_display: int = 0
    sap_mode_historial_unitario: int = 0
    created_at: str = ""
    updated_at: str = ""
