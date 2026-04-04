"""Repositorio para la tabla maestra_materiales."""
from typing import Optional, List
from app.db import get_connection


def count_maestra() -> int:
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM maestra_materiales").fetchone()[0]
    finally:
        conn.close()


def lookup_by_old_code(old_code: str) -> Optional[str]:
    """Busca itemcode_sap por codigo historico."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT itemcode_sap FROM maestra_materiales WHERE codigo_historico = ?",
            (old_code,)
        ).fetchone()
        return row["itemcode_sap"] if row else None
    finally:
        conn.close()


def lookup_by_itemcode(itemcode: str) -> Optional[dict]:
    """Busca material por itemcode_sap directo."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM maestra_materiales WHERE itemcode_sap = ?",
            (itemcode,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def search_maestra(query: str, limit: int = 15) -> list[dict]:
    """Busca material por coincidencia parcial en itemcode o descripcion."""
    conn = get_connection()
    try:
        q = f"%{query}%"
        rows = conn.execute(
            "SELECT itemcode_sap, descripcion AS descripcion_sap FROM maestra_materiales "
            "WHERE itemcode_sap LIKE ? OR descripcion LIKE ? "
            "LIMIT ?", (q, q, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def search_by_keywords(tokens: List[str], limit: int = 15) -> List[dict]:
    """Busca material por coincidencia parcial de multiples tokens en la descripcion."""
    if not tokens:
        return []

    conn = get_connection()
    try:
        where_or = " OR ".join("descripcion LIKE ?" for _ in tokens)
        params = [f"%{t}%" for t in tokens]

        sql = f"""
            SELECT itemcode_sap, descripcion AS descripcion_sap
            FROM maestra_materiales
            WHERE {where_or}
            LIMIT ?
        """
        rows = conn.execute(sql, params + [limit]).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
