from dataclasses import dataclass


@dataclass
class CarteraCliente:
    cod_cliente: str        # PK: CN3517865
    rut: str = ""
    razon: str = ""
    comuna: str = ""
    region_cod: str = ""
    vendedor: str = ""
    industria: str = ""
    sector: str = ""
    cartera: str = ""       # "ATEL"
    region_nombre: str = "" # "Región Metropolitana..."
    origen_archivo: str = ""
    created_at: str = ""
    updated_at: str = ""
