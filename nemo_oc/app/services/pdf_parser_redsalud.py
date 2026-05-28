"""
Parser de PDFs de OCs privadas RedSalud.
Extrae cabecera y líneas de producto del formato SAP estándar de RedSalud.

Formato del PDF:
  ORDEN DE COMPRA
  SERV.MEDICO TABANCURA SPA       ← empresa emisora
  78.053.560-1                    ← RUT emisor
  ...
  N° ORDEN DE COMPRA: 4500614467
  FECHA OC: 03.02.2026
  N° CONTRATO MARCO: 4600002023
  DIRECCIÓN ENTREGA: ...
  CORREO CONTACTO: ...

  POS. CÓDIGO DESCRIPCIÓN REF.PROV CANT UMB FE.ENTREGA PRECIO UNIT. VALOR TOTAL MON.
  10 20000547CAMPO CLINICO 500 UN 03.02.2026 245 122.500 CLP
  ESTERIL 60 X 60 CM              ← descripción continua (líneas siguientes)

  NETO AFECTO 122.500 CLP
  ...
  TOTAL BRUTO 145.775 CLP
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Regex para campos de cabecera
_RE_NUM_OC     = re.compile(r'N[°º]\s*ORDEN DE COMPRA:\s*(\d+)', re.IGNORECASE)
_RE_FECHA      = re.compile(r'FECHA OC:\s*(\d{2}\.\d{2}\.\d{4})', re.IGNORECASE)
_RE_CONTRATO   = re.compile(r'N[°º]\s*CONTRATO MARCO:\s*(\d*)', re.IGNORECASE)
_RE_DIR_ENT    = re.compile(r'DIRECCI[OÓ]N ENTREGA:\s*(.+)', re.IGNORECASE)
_RE_CORREO     = re.compile(r'CORREO CONTACTO:\s*([\w.@-]+)', re.IGNORECASE)
_RE_CON_PAGO   = re.compile(r'CON\.\s*DE PAGO:\s*(.+?)(?:\s{2,}|$)', re.IGNORECASE)
_RE_TOTAL_BRUTO = re.compile(r'TOTAL BRUTO\s+([\d.]+)', re.IGNORECASE)
_RE_NETO       = re.compile(r'NETO AFECTO\s+([\d.]+)', re.IGNORECASE)
_RE_IVA        = re.compile(r'19%\s*IVA\s+([\d.]+)', re.IGNORECASE)

# Regex para una línea de producto: POS CÓDIGO(8d) DESC... CANT UMB DD.MM.YYYY PRECIO TOTAL CLP
# El código (8 dígitos) está pegado a la descripción, sin espacio.
_RE_LINEA = re.compile(
    r'^(\d+)\s+(\d{7,9})'        # POS + CÓDIGO (7-9 dígitos)
    r'(.*?)'                      # DESCRIPCIÓN inicial (lazy)
    r'\s+([\d.,]+)'               # CANT
    r'\s+(\w+)'                   # UMB
    r'\s+(\d{2}\.\d{2}\.\d{4})'  # FE.ENTREGA
    r'\s+([\d.]+)'                # PRECIO UNIT (formato CLP: puntos = miles)
    r'\s+([\d.]+)'                # VALOR TOTAL
    r'\s+CLP',
    re.IGNORECASE
)

# Marcadores de inicio/fin de la tabla de líneas
_RE_TABLE_HEADER = re.compile(r'POS\.?\s+C[OÓ]DIGO\s+DESCRIPCI[OÓ]N', re.IGNORECASE)
_RE_TABLE_END    = re.compile(r'NETO AFECTO|NETO EXENTO', re.IGNORECASE)
# Marcador de línea de continuación (no es un producto nuevo)
_RE_PROD_START   = re.compile(r'^\d+\s+\d{7,9}')


def _parse_clp(value_str: str) -> float:
    """Convierte string CLP (puntos como miles) a float. '122.500' → 122500.0"""
    return _parse_number(value_str)


def _parse_number(value_str: str) -> float:
    """
    Convierte números con separadores locales a float.
    Soporta cantidades como '2.000' y montos como '1.234,56'.
    """
    raw = (value_str or "").strip()
    if not raw:
        return 0.0

    if "," in raw and "." in raw:
        normalized = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        _, tail = raw.rsplit(",", 1)
        normalized = raw.replace(",", ".") if len(tail) <= 2 else raw.replace(",", "")
    elif "." in raw:
        _, tail = raw.rsplit(".", 1)
        normalized = raw if len(tail) <= 2 else raw.replace(".", "")
    else:
        normalized = raw

    return float(normalized)


def _fecha_iso(fecha_str: str) -> str:
    """Convierte 'DD.MM.YYYY' a 'YYYY-MM-DD'."""
    try:
        d, m, y = fecha_str.split(".")
        return f"{y}-{m}-{d}"
    except Exception:
        return fecha_str


def parse_pdf(pdf_path: str) -> Tuple[Dict, List[Dict]]:
    """
    Parsea un PDF de OC RedSalud.
    Retorna (cabecera_dict, lista_de_lineas_dict).
    Lanza Exception si el archivo no puede leerse o no es un PDF RedSalud.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber no está instalado. Ejecute: pip install pdfplumber")

    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    with pdfplumber.open(str(path_obj)) as pdf:
        # Solo necesitamos la primera página para la mayoría de los datos
        page1_text = pdf.pages[0].extract_text() or ""
        # La tabla puede extenderse a la segunda página en OCs largas
        full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    cabecera = _parse_cabecera(page1_text)
    lineas   = _parse_lineas(full_text)

    return cabecera, lineas


def _parse_cabecera(text: str) -> Dict:
    """Extrae los campos de la cabecera del PDF."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Empresa y RUT vienen en las líneas 2 y 3 (después de "ORDEN DE COMPRA")
    empresa = ""
    rut_empresa = ""
    for i, line in enumerate(lines):
        if "ORDEN DE COMPRA" in line.upper() and i == 0:
            empresa   = lines[i + 1] if len(lines) > i + 1 else ""
            rut_empresa = lines[i + 2] if len(lines) > i + 2 else ""
            break

    def _re_group(pattern, default=""):
        m = pattern.search(text)
        return m.group(1).strip() if m else default

    num_oc       = _re_group(_RE_NUM_OC)
    fecha_raw    = _re_group(_RE_FECHA)
    contrato     = _re_group(_RE_CONTRATO)
    dir_entrega  = _re_group(_RE_DIR_ENT)
    correo       = _re_group(_RE_CORREO)
    con_pago     = _re_group(_RE_CON_PAGO)
    total_bruto  = _parse_clp(_re_group(_RE_TOTAL_BRUTO, "0"))
    neto_afecto  = _parse_clp(_re_group(_RE_NETO, "0"))
    iva          = _parse_clp(_re_group(_RE_IVA, "0"))
    fecha_iso    = _fecha_iso(fecha_raw) if fecha_raw else ""

    return {
        "empresa":        empresa,
        "rut_empresa":    rut_empresa,
        "numero_oc":      num_oc,
        "fecha_oc":       fecha_iso,
        "contrato_marco": contrato,
        "dir_entrega":    dir_entrega,
        "correo_contacto": correo,
        "condicion_pago": con_pago,
        "total_bruto":    total_bruto,
        "neto_afecto":    neto_afecto,
        "iva":            iva,
    }


def _parse_lineas(text: str) -> List[Dict]:
    """Extrae las líneas de producto de la tabla."""
    lines = text.split("\n")

    # Encontrar inicio y fin de la tabla
    start_idx = None
    end_idx   = None
    for i, line in enumerate(lines):
        if start_idx is None and _RE_TABLE_HEADER.search(line):
            start_idx = i + 1  # línea siguiente al encabezado
        elif start_idx is not None and _RE_TABLE_END.search(line):
            end_idx = i
            break

    if start_idx is None:
        logger.warning("No se encontró tabla de productos en el PDF")
        return []

    table_lines = lines[start_idx:end_idx]

    # Agrupar líneas de producto (una línea puede tener descripción en líneas siguientes)
    products_raw = []
    current = None

    for line in table_lines:
        if _RE_PROD_START.match(line.strip()):
            if current is not None:
                products_raw.append(current)
            current = line.strip()
        elif current is not None and line.strip():
            # Línea de continuación de descripción
            current += " " + line.strip()

    if current is not None:
        products_raw.append(current)

    # Parsear cada grupo
    result = []
    for raw in products_raw:
        m = _RE_LINEA.search(raw)
        if not m:
            logger.debug(f"Línea de producto no parseada: {raw[:80]}")
            continue

        pos         = int(m.group(1))
        codigo      = m.group(2).strip()
        desc_inline = m.group(3).strip()
        cant        = _parse_number(m.group(4))
        umb         = m.group(5).strip()
        fecha_ent   = _fecha_iso(m.group(6))
        precio_unit = _parse_clp(m.group(7))
        valor_total = _parse_clp(m.group(8))

        # Descripción: la parte inline + lo que quedó después de CLP (continuaciones)
        after_match = raw[m.end():].strip()
        descripcion = " ".join(filter(None, [desc_inline, after_match])).strip()

        result.append({
            "pos":        pos,
            "codigo":     codigo,
            "descripcion": descripcion,
            "cantidad":   cant,
            "unidad":     umb,
            "fecha_entrega": fecha_ent,
            "precio_unit": precio_unit,
            "valor_total": valor_total,
        })

    return result
