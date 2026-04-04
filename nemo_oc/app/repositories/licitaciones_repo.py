"""
Repositorio para la tabla licitaciones_ref.

DISEÑO INTENCIONAL:
  get_candidates() hace una búsqueda AMPLIA (OR LIKE, orientada a recall).
  El scoring de similitud real (Jaccard ponderado) ocurre en licitaciones_service.py.
  Separar recuperación de scoring evita que el SQL descarte candidatos buenos.
"""
from typing import List
from typing import List, Optional
from app.db import get_connection


def count_licitaciones() -> int:
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM licitaciones_ref").fetchone()[0]
    finally:
        conn.close()


def get_exact_candidates(desc_norm: str, rut: str) -> List[dict]:
    """
    Fase 1: Busca un match exacto ('descripcion_norm' idéntico) para un RUT específico.
    """
    if not desc_norm or not rut:
        return []

    conn = get_connection()
    try:
        sql = """
            SELECT itemcode_sap, descripcion_nemo, descripcion_comprador,
                   frecuencia, producto_code_old, descripcion_norm
            FROM licitaciones_ref
            WHERE descripcion_norm = ? AND rut_comprador = ?
              AND itemcode_sap IS NOT NULL AND itemcode_sap != ''
            ORDER BY frecuencia DESC
            LIMIT 5
        """
        rows = conn.execute(sql, (desc_norm, rut)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_candidates(tokens: List[str], limit: int = 80, rut: Optional[str] = None) -> List[dict]:
    """
    Trae hasta `limit` candidatos desde licitaciones_ref usando OR LIKE.

    Por qué OR y no AND:
      - AND es muy restrictivo: si la OC dice "guante nitrilo talla s" y el
        histórico dice "guante nitrilo s/t" el AND falla aunque son lo mismo.
      - OR con muchos candidatos + Jaccard en Python da mejores resultados.

    Por qué LIKE y no word boundary en SQL:
      - SQLite no soporta regex ni word boundaries nativamente sin extensiones.
      - Los false positives de substring se filtran en Python con Jaccard.
    """
    if not tokens:
        return []

    conn = get_connection()
    try:
        where_or = " OR ".join("descripcion_norm LIKE ?" for _ in tokens)
        params = [f"%{t}%" for t in tokens]

        # Fase 2: restrict by RUT
        rut_clause = ""
        if rut:
            rut_clause = "AND rut_comprador = ?"
            params.append(rut)

        sql = f"""
            SELECT itemcode_sap, descripcion_nemo, descripcion_comprador,
                   frecuencia, producto_code_old, descripcion_norm
            FROM licitaciones_ref
            WHERE ({where_or})
              {rut_clause}
              AND itemcode_sap IS NOT NULL AND itemcode_sap != ''
            ORDER BY frecuencia DESC
            LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
