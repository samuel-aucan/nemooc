"""
CRUD administrativo para holdings, RUTs y reglas de deteccion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.db import get_connection
from app.utils.rut_utils import normalize_rut


@dataclass
class HoldingRutAdmin:
    rut_norm: str
    rut_display: str = ""
    nombre_sucursal: str = ""


@dataclass
class HoldingRuleAdmin:
    id: int
    rule_type: str
    rule_value: str
    prioridad: int = 100
    activo: bool = True
    notas: str = ""


@dataclass
class HoldingAdmin:
    id: str
    nombre: str
    prefijo: str
    parser_type: str
    homo_file: str = ""
    activo: bool = True
    catalog_count: int = 0
    ruts: list[HoldingRutAdmin] = field(default_factory=list)
    rules: list[HoldingRuleAdmin] = field(default_factory=list)


def list_holdings_admin() -> list[HoldingAdmin]:
    conn = get_connection()
    try:
        holding_rows = conn.execute(
            """
            SELECT
                h.id,
                h.nombre,
                h.prefijo,
                h.parser_type,
                h.homo_file,
                h.activo,
                COUNT(p.codigo_cliente) AS catalog_count
            FROM holdings h
            LEFT JOIN homologacion_privados p
                ON p.holding_id = h.id
            GROUP BY h.id, h.nombre, h.prefijo, h.parser_type, h.homo_file, h.activo
            ORDER BY h.nombre
            """
        ).fetchall()

        rut_rows = conn.execute(
            "SELECT holding_id, rut_norm, rut_display, nombre_sucursal FROM holding_ruts ORDER BY holding_id, rut_norm"
        ).fetchall()
        rule_rows = conn.execute(
            """
            SELECT id, holding_id, rule_type, rule_value, prioridad, activo, notas
            FROM holding_match_rules
            ORDER BY holding_id, prioridad, id
            """
        ).fetchall()

        rut_map: dict[str, list[HoldingRutAdmin]] = {}
        for row in rut_rows:
            rut_map.setdefault(row["holding_id"], []).append(
                HoldingRutAdmin(
                    rut_norm=row["rut_norm"],
                    rut_display=row["rut_display"] or "",
                    nombre_sucursal=row["nombre_sucursal"] or "",
                )
            )

        rule_map: dict[str, list[HoldingRuleAdmin]] = {}
        for row in rule_rows:
            rule_map.setdefault(row["holding_id"], []).append(
                HoldingRuleAdmin(
                    id=row["id"],
                    rule_type=row["rule_type"],
                    rule_value=row["rule_value"],
                    prioridad=row["prioridad"] or 100,
                    activo=bool(row["activo"]),
                    notas=row["notas"] or "",
                )
            )

        return [
            HoldingAdmin(
                id=row["id"],
                nombre=row["nombre"],
                prefijo=row["prefijo"],
                parser_type=row["parser_type"],
                homo_file=row["homo_file"] or "",
                activo=bool(row["activo"]),
                catalog_count=row["catalog_count"] or 0,
                ruts=rut_map.get(row["id"], []),
                rules=rule_map.get(row["id"], []),
            )
            for row in holding_rows
        ]
    finally:
        conn.close()


def create_holding(
    holding_id: str,
    nombre: str,
    prefijo: str,
    parser_type: str,
    homo_file: str = "",
    activo: bool = True,
) -> None:
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO holdings (id, nombre, prefijo, parser_type, homo_file, activo, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (holding_id.strip().lower(), nombre.strip(), prefijo.strip().upper(), parser_type.strip().lower(), homo_file.strip(), 1 if activo else 0, now, now),
        )
        conn.commit()
    finally:
        conn.close()


def update_holding(
    holding_id: str,
    nombre: str,
    prefijo: str,
    parser_type: str,
    homo_file: str = "",
    activo: bool = True,
) -> None:
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE holdings
            SET nombre = ?, prefijo = ?, parser_type = ?, homo_file = ?, activo = ?, updated_at = ?
            WHERE id = ?
            """,
            (nombre.strip(), prefijo.strip().upper(), parser_type.strip().lower(), homo_file.strip(), 1 if activo else 0, now, holding_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Holding no existe: {holding_id}")
        conn.commit()
    finally:
        conn.close()


def upsert_holding_rut(holding_id: str, rut_value: str, rut_display: str = "", nombre_sucursal: str = "") -> str:
    rut_norm = normalize_rut(rut_value)
    if not rut_norm:
        raise ValueError("RUT invalido")

    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO holding_ruts (rut_norm, holding_id, rut_display, nombre_sucursal)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(rut_norm) DO UPDATE SET
                holding_id = excluded.holding_id,
                rut_display = excluded.rut_display,
                nombre_sucursal = excluded.nombre_sucursal
            """,
            (rut_norm, holding_id, rut_display.strip() or rut_value.strip(), nombre_sucursal.strip()),
        )
        conn.execute("UPDATE holdings SET updated_at = ? WHERE id = ?", (now, holding_id))
        conn.commit()
        return rut_norm
    finally:
        conn.close()


def delete_holding_rut(holding_id: str, rut_norm: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM holding_ruts WHERE holding_id = ? AND rut_norm = ?", (holding_id, rut_norm))
        conn.commit()
    finally:
        conn.close()


def create_holding_rule(
    holding_id: str,
    rule_type: str,
    rule_value: str,
    prioridad: int = 100,
    activo: bool = True,
    notas: str = "",
) -> int:
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO holding_match_rules
                (holding_id, rule_type, rule_value, prioridad, activo, notas, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (holding_id, rule_type.strip(), rule_value.strip(), prioridad, 1 if activo else 0, notas.strip(), now, now),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def update_holding_rule(
    rule_id: int,
    holding_id: str,
    rule_type: str,
    rule_value: str,
    prioridad: int = 100,
    activo: bool = True,
    notas: str = "",
) -> None:
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE holding_match_rules
            SET holding_id = ?, rule_type = ?, rule_value = ?, prioridad = ?, activo = ?, notas = ?, updated_at = ?
            WHERE id = ?
            """,
            (holding_id, rule_type.strip(), rule_value.strip(), prioridad, 1 if activo else 0, notas.strip(), now, rule_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Regla no existe: {rule_id}")
        conn.commit()
    finally:
        conn.close()


def delete_holding_rule(holding_id: str, rule_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM holding_match_rules WHERE holding_id = ? AND id = ?", (holding_id, rule_id))
        conn.commit()
    finally:
        conn.close()
