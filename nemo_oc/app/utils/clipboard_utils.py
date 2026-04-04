"""
Formatea y copia al portapapeles la tabla SAP lista para pegar en SAP Business One.
Columnas: ItemCode | Descripción | Cantidad | Precio
Formato: TAB-separado, CRLF entre líneas, sin encabezados.
"""
import tkinter as tk
import logging
from typing import List
from app.models.linea_oc import LineaOC

logger = logging.getLogger(__name__)


def generar_texto_sap(lineas: List[LineaOC]) -> tuple[str, List[int]]:
    """
    Genera el texto tabulado para SAP desde líneas de detalle.

    Returns:
        (texto_clipboard, correlativos_excluidos)
        - texto_clipboard: texto TAB+CRLF listo para pegar en SAP
        - correlativos_excluidos: lista de correlativos sin homologación
    """
    filas = []
    excluidos = []

    for linea in lineas:
        if not linea.itemcode_sap:
            excluidos.append(linea.correlativo)
            continue

        itemcode = linea.itemcode_sap or ""
        descripcion = linea.descripcion_sap or linea.producto or ""
        cantidad = linea.cantidad_sap if linea.cantidad_sap is not None else linea.cantidad
        precio = linea.precio_sap if linea.precio_sap is not None else linea.precio_neto

        # Formatear cantidad como entero si es entero, decimal si no
        if cantidad == int(cantidad):
            cant_str = str(int(cantidad))
        else:
            cant_str = f"{cantidad:.4f}".rstrip('0').rstrip('.')

        precio_str = f"{precio:.2f}"

        fila = f"{itemcode}\t{descripcion}\t{cant_str}\t{precio_str}"
        filas.append(fila)

    texto = "\r\n".join(filas)
    return texto, excluidos


def copiar_al_portapapeles(texto: str, root: tk.Tk | None = None) -> bool:
    """
    Copia el texto al portapapeles del sistema.
    Retorna True si tuvo éxito.
    """
    try:
        if root is None:
            # Crear ventana temporal para acceder al portapapeles
            _root = tk.Tk()
            _root.withdraw()
            _root.clipboard_clear()
            _root.clipboard_append(texto)
            _root.update()
            _root.destroy()
        else:
            root.clipboard_clear()
            root.clipboard_append(texto)
            root.update()
        return True
    except Exception as e:
        logger.error(f"Error copiando al portapapeles: {e}")
        return False
