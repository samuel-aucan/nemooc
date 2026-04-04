"""
Utilidades para manejo de RUT chileno.
Regla: "61.606.402-9" → "CN61606402"
  - quitar puntos
  - quitar guión y dígito verificador
  - anteponer "CN"
"""
import re


def normalize_rut(rut: str) -> str:
    """
    Normaliza un RUT para comparaciones: elimina puntos y guión, conserva dígito verificador.
    Ejemplos:
        "92.051.000-0"  → "920510000"
        "78.053.560-1"  → "780535601"
        "92051000-0"    → "920510000"
    Usado para lookup en la tabla holding_ruts.
    """
    if not rut:
        return ""
    return re.sub(r'[.\-\s]', '', rut.strip()).upper()


def normalize_rut_body(rut: str) -> str:
    """
    Retorna el cuerpo numerico del RUT, sin puntos, guion ni digito verificador.
    Tolera formatos como:
        "92.051.000-0" -> "92051000"
        "92051000-0"   -> "92051000"
        "920510000"    -> "92051000"
        "76.481.620-K" -> "76481620"
        "76481620K"    -> "76481620"
    """
    if not rut:
        return ""

    raw = str(rut).strip().upper()
    clean = normalize_rut(raw)
    if not clean:
        return ""

    has_explicit_dv = ("-" in raw) or clean.endswith("K") or len(clean) >= 9
    body = clean[:-1] if has_explicit_dv else clean
    return re.sub(r"\D", "", body)


def rut_to_cliente_sap(rut: str) -> str:
    """
    Convierte un RUT chileno al código de socio de negocio SAP.
    Ejemplos:
        "61.606.402-9"  → "CN61606402"
        "76.215.260-6"  → "CN76215260"
        "12345678-K"    → "CN12345678"
    """
    if not rut:
        return ""
    # Quitar puntos y espacios
    clean = re.sub(r'[.\s]', '', rut.strip())
    # Quitar guión y todo lo que sigue (dígito verificador)
    clean = clean.split('-')[0]
    # Solo dígitos
    clean = re.sub(r'\D', '', clean)
    return f"CN{clean}" if clean else ""
