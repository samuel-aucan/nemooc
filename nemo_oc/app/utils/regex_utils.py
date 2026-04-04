"""
Utilidades de expresiones regulares para NemoOC.
Extrae codigo_mp desde EspecificacionComprador.
"""
import re
from typing import Optional

# Patrón: "(2230498) ENVOLTURA NEMO..." → captura "2230498"
_CODIGO_MP_RE = re.compile(r'^\s*\((\d+)\)')


def extraer_codigo_mp(especificacion: str) -> Optional[str]:
    """
    Extrae el código numérico de Mercado Público desde EspecificacionComprador.

    Ejemplos:
        "(2230498) ENVOLTURA NEMO..."  → "2230498"
        "(2229230) BOBINA..."          → "2229230"
        "SIN CODIGO"                   → None
    """
    if not especificacion:
        return None
    m = _CODIGO_MP_RE.match(especificacion)
    return m.group(1) if m else None
