"""
Repositorio de homologación — interfaz de consulta sobre la BD.
Delegará la lógica de carga al HomologacionService.
"""
from app.db import get_connection
from app.models.homologacion import HomologacionItem
from typing import List, Optional


def get_all_homologacion() -> List[HomologacionItem]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM homologacion_productos ORDER BY codigo_mp"
        ).fetchall()
        return [
            HomologacionItem(
                codigo_mp=str(r["codigo_mp"]),
                itemcode_sap=r["itemcode_sap"],
                descripcion_sap=r["descripcion_sap"],
                factor_empaque=r["factor_empaque"] or 1.0,
                activo=bool(r["activo"]),
                origen_archivo=r["origen_archivo"] or "",
            )
            for r in rows
        ]
    finally:
        conn.close()


def count_homologacion() -> dict:
    conn = get_connection()
    try:
        cm = conn.execute("SELECT COUNT(*) FROM homologacion_productos").fetchone()[0]
        sap = conn.execute("SELECT COUNT(*) FROM sap_articulos WHERE activo=1").fetchone()[0]
        cruzados = conn.execute("""
            SELECT COUNT(*) FROM homologacion_productos h
            INNER JOIN sap_articulos s ON h.itemcode_sap = s.itemcode_sap
        """).fetchone()[0]
        return {"cm": cm, "sap": sap, "cruzados": cruzados}
    finally:
        conn.close()
