"""
Servicio de homologación para OCs privadas RedSalud.
Lee HOMO RED SALUD.xlsx y mapea código cliente → ItemCode SAP Nemo.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.db import get_connection

logger = logging.getLogger(__name__)

# Columnas de HOMO RED SALUD.xlsx (índice base 0)
COL_CODIGO_MATERIAL = 0   # A: Código Material (código RedSalud, ej: 20000547)
COL_DESCRIPCION_SAP = 1   # B: Descripción SAP
COL_CODIGO_NEMO = 2        # C: Codigo NEMO (ItemCode SAP Nemo)
COL_PRECIO = 3             # D: PRECIO


@dataclass
class RedSaludItem:
    codigo_cliente: str
    descripcion: str = ""
    itemcode_sap: str = ""
    precio_ref: float = 0.0


class RedSaludHomoService:
    """Gestiona la carga y búsqueda del catálogo de homologación RedSalud."""

    def __init__(self):
        self._cache: Dict[str, RedSaludItem] = {}
        self._loaded = False

    def cargar_excel(self, path: str) -> Tuple[int, List[str]]:
        """Lee HOMO RED SALUD.xlsx y persiste en SQLite + memoria."""
        try:
            import openpyxl
        except ImportError:
            return 0, ["openpyxl no está instalado."]

        path_obj = Path(path)
        if not path_obj.exists():
            return 0, [f"Archivo no encontrado: {path}"]

        items: List[RedSaludItem] = []
        errores: List[str] = []
        now = datetime.now().isoformat()

        try:
            wb = openpyxl.load_workbook(str(path_obj), data_only=True, read_only=True)
            ws = wb.active

            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if not row or len(row) < 3:
                    continue
                raw_cod = row[COL_CODIGO_MATERIAL]
                raw_desc = row[COL_DESCRIPCION_SAP]
                raw_nemo = row[COL_CODIGO_NEMO]
                raw_precio = row[COL_PRECIO] if len(row) > COL_PRECIO else None

                if raw_cod is None or raw_nemo is None:
                    continue

                codigo = str(raw_cod).strip()
                itemcode = str(raw_nemo).strip()
                if not codigo or not itemcode:
                    continue

                try:
                    precio = float(raw_precio) if raw_precio is not None else 0.0
                except (ValueError, TypeError):
                    precio = 0.0

                items.append(RedSaludItem(
                    codigo_cliente=codigo,
                    descripcion=str(raw_desc).strip() if raw_desc else "",
                    itemcode_sap=itemcode,
                    precio_ref=precio,
                ))

            wb.close()
        except Exception as e:
            return 0, [f"Error leyendo Excel: {e}"]

        if not items:
            return 0, ["No se encontraron registros válidos en el archivo."]

        count = self._guardar(items, path_obj.name, now)
        self._reload_cache()
        logger.info(f"HomologaciónRedSalud cargada: {count} registros desde {path_obj.name}")
        return count, errores

    def lookup(self, codigo_cliente: str) -> Optional[RedSaludItem]:
        """Busca por código cliente RedSalud. Retorna None si no existe."""
        if not self._loaded:
            self._reload_cache()
        return self._cache.get(str(codigo_cliente).strip())

    def count(self) -> int:
        if not self._loaded:
            self._reload_cache()
        return len(self._cache)

    def reload(self):
        self._reload_cache()

    # ------------------------------------------------------------------

    def _guardar(self, items: List[RedSaludItem], origen: str, now: str) -> int:
        conn = get_connection()
        count = 0
        try:
            for item in items:
                conn.execute("""
                    INSERT INTO homologacion_redsalud
                        (codigo_cliente, descripcion, itemcode_sap, precio_ref,
                         origen_archivo, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(codigo_cliente) DO UPDATE SET
                        descripcion    = excluded.descripcion,
                        itemcode_sap   = excluded.itemcode_sap,
                        precio_ref     = excluded.precio_ref,
                        origen_archivo = excluded.origen_archivo,
                        updated_at     = excluded.updated_at
                """, (item.codigo_cliente, item.descripcion, item.itemcode_sap,
                      item.precio_ref, origen, now, now))
                count += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error guardando homologación RedSalud: {e}")
            raise
        finally:
            conn.close()
        return count

    def _reload_cache(self):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT codigo_cliente, descripcion, itemcode_sap, precio_ref "
                "FROM homologacion_redsalud"
            ).fetchall()
            self._cache = {
                r["codigo_cliente"]: RedSaludItem(
                    codigo_cliente=r["codigo_cliente"],
                    descripcion=r["descripcion"] or "",
                    itemcode_sap=r["itemcode_sap"] or "",
                    precio_ref=r["precio_ref"] or 0.0,
                )
                for r in rows
            }
            self._loaded = True
        finally:
            conn.close()


_service: Optional[RedSaludHomoService] = None


def get_redsalud_homo_service() -> RedSaludHomoService:
    global _service
    if _service is None:
        _service = RedSaludHomoService()
    return _service
