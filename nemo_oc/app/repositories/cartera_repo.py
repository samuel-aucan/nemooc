from app.db import get_connection


def count_cartera() -> int:
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM cartera_clientes").fetchone()[0]
    finally:
        conn.close()
