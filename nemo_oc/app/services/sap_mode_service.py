"""Logica para modo SAP unitario/display en lineas de OC."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Optional

from app.db import get_connection
from app.models.linea_oc import LineaOC
from app.repositories import maestra_repo

SAP_MODE_UNITARIO = "unitario"
SAP_MODE_DISPLAY = "display"
SAP_MODE_USUARIO = "usuario"
SAP_MODE_HISTORIAL = "historial"
SAP_MODE_DEFAULT = "default"
SAP_DISPLAY_TIPOS = {"SE", "AG", "CC", "TD"}
SAP_HISTORY_LIMIT = 30
SAP_HISTORY_MIN_SAMPLE = 5
SAP_HISTORY_CONFIDENCE = 0.65
SAP_PRICE_DECIMALS = 4
SAP_VALUES_AUTO = "auto"
SAP_VALUES_MANUAL = "manual"
SAP_VALUES_APRENDIZAJE = "aprendizaje"


def supports_display_mode(tipo_oc: str) -> bool:
    return (tipo_oc or "").upper() in SAP_DISPLAY_TIPOS


def get_display_factor(itemcode_sap: Optional[str], fallback_factor: float = 1.0) -> float:
    factor = float(fallback_factor or 1.0)
    if itemcode_sap:
        material = maestra_repo.lookup_by_itemcode(itemcode_sap)
        if material:
            try:
                display_factor = float(material.get("cant_display") or 0)
                master_factor = float(material.get("cant_caja_master") or 0)
                if display_factor > 1:
                    factor = display_factor
                elif master_factor > 1:
                    factor = master_factor
            except (TypeError, ValueError):
                pass
    return factor if factor > 1 else 1.0


def enrich_linea_for_api(linea: LineaOC, tipo_oc: str) -> LineaOC:
    try:
        factor = get_display_factor(linea.itemcode_sap, linea.factor_empaque)
    except Exception:
        factor = float(linea.factor_empaque or 1.0)
    applicable = supports_display_mode(tipo_oc) and bool(linea.itemcode_sap) and factor > 1

    if not applicable:
        linea.sap_mode_sugerido = None
        linea.sap_mode_historial_total = 0
        linea.sap_mode_historial_display = 0
        linea.sap_mode_historial_unitario = 0
        return linea

    linea.factor_empaque = factor
    inferred_mode = _normalize_mode(linea.sap_mode) or _infer_mode_from_values(
        cantidad=linea.cantidad,
        cantidad_sap=linea.cantidad_sap,
        precio_neto=linea.precio_neto,
        precio_sap=linea.precio_sap,
        total=linea.total,
        factor=factor,
    )
    linea.sap_mode = inferred_mode or SAP_MODE_UNITARIO

    try:
        history = get_recent_mode_stats(linea.itemcode_sap, factor, SAP_HISTORY_LIMIT)
    except Exception:
        history = {"display": 0, "unitario": 0, "total": 0}
    linea.sap_mode_historial_total = history["total"]
    linea.sap_mode_historial_display = history["display"]
    linea.sap_mode_historial_unitario = history["unitario"]
    linea.sap_mode_sugerido = _suggest_mode_from_history(history)
    return linea


def apply_auto_mode_to_line(linea: LineaOC, tipo_oc: str) -> LineaOC:
    factor = get_display_factor(linea.itemcode_sap, linea.factor_empaque)
    applicable = supports_display_mode(tipo_oc) and bool(linea.itemcode_sap) and factor > 1

    if not applicable:
        linea.factor_empaque = 1.0
        linea.cantidad_sap, linea.precio_sap = _calculate_sap_values(
            cantidad=linea.cantidad,
            precio_neto=linea.precio_neto,
            total=linea.total,
            factor=1.0,
            mode=SAP_MODE_UNITARIO,
        )
        linea.sap_mode = None
        linea.sap_mode_origen = None
        linea.sap_values_origen = SAP_VALUES_AUTO
        return linea

    history = get_recent_mode_stats(linea.itemcode_sap, factor, SAP_HISTORY_LIMIT)
    suggested_mode = _suggest_mode_from_history(history)
    mode_origin = SAP_MODE_HISTORIAL if suggested_mode else SAP_MODE_DEFAULT
    resolved_mode = suggested_mode or SAP_MODE_UNITARIO

    linea.factor_empaque = factor
    linea.cantidad_sap, linea.precio_sap = _calculate_sap_values(
        cantidad=linea.cantidad,
        precio_neto=linea.precio_neto,
        total=linea.total,
        factor=factor,
        mode=resolved_mode,
    )
    linea.sap_mode = resolved_mode
    linea.sap_mode_origen = mode_origin
    linea.sap_values_origen = SAP_VALUES_AUTO
    return linea


def assign_itemcode_with_mode(
    codigo_oc: str,
    correlativo: int,
    itemcode_sap: str,
    descripcion_sap: str = "",
    estado_homologacion: str = "manual",
) -> None:
    context = _get_line_context(codigo_oc, correlativo)
    if not context:
        return

    factor = get_display_factor(itemcode_sap, context["factor_empaque"] or 1.0)
    applicable = supports_display_mode(context["tipo_oc"]) and factor > 1
    mode = None
    mode_origin = None

    if applicable:
        history = get_recent_mode_stats(itemcode_sap, factor, SAP_HISTORY_LIMIT)
        suggested_mode = _suggest_mode_from_history(history)
        mode = suggested_mode or SAP_MODE_UNITARIO
        mode_origin = SAP_MODE_HISTORIAL if suggested_mode else SAP_MODE_DEFAULT

    cantidad_sap, precio_sap = _calculate_sap_values(
        cantidad=context["cantidad"] or 0.0,
        precio_neto=context["precio_neto"] or 0.0,
        total=context["total"] or 0.0,
        factor=factor if applicable else 1.0,
        mode=mode or SAP_MODE_UNITARIO,
    )

    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute(
            """
            UPDATE oc_detalle
            SET itemcode_sap = ?,
                descripcion_sap = ?,
                factor_empaque = ?,
                cantidad_sap = ?,
                precio_sap = ?,
                sap_mode = ?,
                sap_mode_origen = ?,
                sap_values_origen = ?,
                sap_values_updated_at = '',
                sap_values_updated_by_user_id = NULL,
                sap_values_updated_by_username = '',
                estado_homologacion = ?,
                updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
            """,
            (
                itemcode_sap,
                descripcion_sap or None,
                factor if applicable else 1.0,
                cantidad_sap,
                precio_sap,
                mode,
                mode_origin,
                SAP_VALUES_AUTO,
                estado_homologacion,
                now,
                codigo_oc,
                correlativo,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def clear_itemcode_with_mode(codigo_oc: str, correlativo: int) -> None:
    context = _get_line_context(codigo_oc, correlativo)
    if not context:
        return

    cantidad_sap, precio_sap = _calculate_sap_values(
        cantidad=context["cantidad"] or 0.0,
        precio_neto=context["precio_neto"] or 0.0,
        total=context["total"] or 0.0,
        factor=1.0,
        mode=SAP_MODE_UNITARIO,
    )

    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute(
            """
            UPDATE oc_detalle
            SET itemcode_sap = NULL,
                descripcion_sap = NULL,
                factor_empaque = 1,
                cantidad_sap = ?,
                precio_sap = ?,
                sap_mode = NULL,
                sap_mode_origen = NULL,
                sap_values_origen = ?,
                sap_values_updated_at = '',
                sap_values_updated_by_user_id = NULL,
                sap_values_updated_by_username = '',
                estado_homologacion = 'pendiente',
                updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
            """,
            (cantidad_sap, precio_sap, SAP_VALUES_AUTO, now, codigo_oc, correlativo),
        )
        conn.commit()
    finally:
        conn.close()


def update_line_mode(codigo_oc: str, correlativo: int, mode: str) -> None:
    normalized_mode = _normalize_mode(mode)
    if normalized_mode not in {SAP_MODE_UNITARIO, SAP_MODE_DISPLAY}:
        raise ValueError("Modo SAP invalido")

    context = _get_line_context(codigo_oc, correlativo)
    if not context:
        raise ValueError("Linea no encontrada")

    factor = get_display_factor(context["itemcode_sap"], context["factor_empaque"] or 1.0)
    applicable = supports_display_mode(context["tipo_oc"]) and bool(context["itemcode_sap"]) and factor > 1
    if not applicable:
        raise ValueError("La linea no admite modo display")

    cantidad_sap, precio_sap = _calculate_sap_values(
        cantidad=context["cantidad"] or 0.0,
        precio_neto=context["precio_neto"] or 0.0,
        total=context["total"] or 0.0,
        factor=factor,
        mode=normalized_mode,
    )

    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute(
            """
            UPDATE oc_detalle
            SET factor_empaque = ?,
                cantidad_sap = ?,
                precio_sap = ?,
                sap_mode = ?,
                sap_mode_origen = ?,
                sap_values_origen = ?,
                sap_values_updated_at = '',
                sap_values_updated_by_user_id = NULL,
                sap_values_updated_by_username = '',
                updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
            """,
            (factor, cantidad_sap, precio_sap, normalized_mode, SAP_MODE_USUARIO, SAP_VALUES_AUTO, now, codigo_oc, correlativo),
        )
        conn.commit()
    finally:
        conn.close()


def apply_learned_sap_values_to_line(linea: LineaOC, oc) -> LineaOC:
    """Aplica el ultimo ajuste manual compatible sin tocar valores originales de la OC."""
    if (linea.sap_values_origen or "").strip().lower() == SAP_VALUES_MANUAL:
        return linea

    codigo_mp = (linea.codigo_mp or "").strip()
    itemcode_sap = (linea.itemcode_sap or "").strip()
    if not codigo_mp and not itemcode_sap:
        return linea

    base_qty = _finite_or_default(linea.cantidad_sap, linea.cantidad)
    base_price = _finite_or_default(
        linea.precio_sap,
        _get_base_unit_price(linea.cantidad, linea.precio_neto, linea.total),
    )

    conn = get_connection()
    try:
        learning = _find_recent_values_learning(
            conn,
            tipo_oc=getattr(oc, "tipo_oc", ""),
            rut_unidad=getattr(oc, "rut_unidad", ""),
            codigo_mp=codigo_mp,
            itemcode_sap=itemcode_sap,
        )
    finally:
        conn.close()

    learned_values = _apply_learning_factors(base_qty, base_price, learning)
    if not learned_values:
        return linea

    linea.cantidad_sap, linea.precio_sap = learned_values
    linea.sap_values_origen = SAP_VALUES_APRENDIZAJE
    return linea


def update_line_sap_values(
    codigo_oc: str,
    correlativo: int,
    cantidad_sap: float,
    precio_sap: float,
    *,
    actor_user_id: Optional[int] = None,
    actor_username: str = "",
) -> dict:
    _validate_sap_value(cantidad_sap, "cantidad_sap")
    _validate_sap_value(precio_sap, "precio_sap")

    context = _get_line_context(codigo_oc, correlativo)
    if not context:
        raise ValueError("Linea no encontrada")

    base_qty, base_price = _calculate_standard_values_from_context(context)
    previous_qty = _finite_or_default(context["cantidad_sap"], base_qty)
    previous_price = _finite_or_default(context["precio_sap"], base_price)
    next_qty = round(float(cantidad_sap), 4)
    next_price = round(float(precio_sap), SAP_PRICE_DECIMALS)
    now = datetime.now().isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE oc_detalle
            SET cantidad_sap = ?,
                precio_sap = ?,
                sap_values_origen = ?,
                sap_values_updated_at = ?,
                sap_values_updated_by_user_id = ?,
                sap_values_updated_by_username = ?,
                updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
            """,
            (
                next_qty,
                next_price,
                SAP_VALUES_MANUAL,
                now,
                actor_user_id,
                actor_username or "",
                now,
                codigo_oc,
                correlativo,
            ),
        )
        _insert_values_history(
            conn,
            context,
            cantidad_base=base_qty,
            precio_base=base_price,
            cantidad_anterior=previous_qty,
            precio_anterior=previous_price,
            cantidad_nueva=next_qty,
            precio_nuevo=next_price,
            accion="manual",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            changed_at=now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "codigo_oc": codigo_oc,
        "correlativo": correlativo,
        "cantidad_sap": next_qty,
        "precio_sap": next_price,
        "sap_values_origen": SAP_VALUES_MANUAL,
        "sap_values_updated_at": now,
        "sap_values_updated_by_user_id": actor_user_id,
        "sap_values_updated_by_username": actor_username or "",
    }


def reset_line_sap_values(
    codigo_oc: str,
    correlativo: int,
    *,
    actor_user_id: Optional[int] = None,
    actor_username: str = "",
) -> dict:
    context = _get_line_context(codigo_oc, correlativo)
    if not context:
        raise ValueError("Linea no encontrada")

    base_qty, base_price = _calculate_standard_values_from_context(context)
    previous_qty = _finite_or_default(context["cantidad_sap"], base_qty)
    previous_price = _finite_or_default(context["precio_sap"], base_price)
    now = datetime.now().isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE oc_detalle
            SET cantidad_sap = ?,
                precio_sap = ?,
                sap_values_origen = ?,
                sap_values_updated_at = ?,
                sap_values_updated_by_user_id = ?,
                sap_values_updated_by_username = ?,
                updated_at = ?
            WHERE codigo_oc = ? AND correlativo = ?
            """,
            (
                base_qty,
                base_price,
                SAP_VALUES_AUTO,
                now,
                actor_user_id,
                actor_username or "",
                now,
                codigo_oc,
                correlativo,
            ),
        )
        _insert_values_history(
            conn,
            context,
            cantidad_base=base_qty,
            precio_base=base_price,
            cantidad_anterior=previous_qty,
            precio_anterior=previous_price,
            cantidad_nueva=base_qty,
            precio_nuevo=base_price,
            accion="revert",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            changed_at=now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "codigo_oc": codigo_oc,
        "correlativo": correlativo,
        "cantidad_sap": base_qty,
        "precio_sap": base_price,
        "sap_values_origen": SAP_VALUES_AUTO,
        "sap_values_updated_at": now,
        "sap_values_updated_by_user_id": actor_user_id,
        "sap_values_updated_by_username": actor_username or "",
    }


def get_line_sap_values_history(codigo_oc: str, correlativo: int, limit: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                codigo_oc,
                correlativo,
                codigo_mp,
                itemcode_sap,
                tipo_oc,
                rut_unidad,
                cantidad_base,
                precio_base,
                cantidad_anterior,
                precio_anterior,
                cantidad_nueva,
                precio_nuevo,
                cantidad_factor,
                precio_factor,
                accion,
                actor_user_id,
                actor_username,
                changed_at
            FROM oc_linea_sap_ajuste_historial
            WHERE codigo_oc = ? AND correlativo = ?
            ORDER BY datetime(changed_at) DESC, id DESC
            LIMIT ?
            """,
            (codigo_oc, correlativo, max(1, min(int(limit or 20), 100))),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_recent_mode_stats(itemcode_sap: Optional[str], factor: float, limit: int = SAP_HISTORY_LIMIT) -> dict[str, int]:
    if not itemcode_sap or factor <= 1:
        return {"display": 0, "unitario": 0, "total": 0}

    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in SAP_DISPLAY_TIPOS)
        rows = conn.execute(
            f"""
            SELECT
                d.sap_mode,
                d.sap_mode_origen,
                d.cantidad,
                d.cantidad_sap,
                d.precio_neto,
                d.precio_sap,
                d.total
            FROM oc_detalle d
            INNER JOIN oc_cabecera c ON c.codigo_oc = d.codigo_oc
            WHERE d.itemcode_sap = ?
              AND c.tipo_oc IN ({placeholders})
            ORDER BY COALESCE(NULLIF(d.updated_at, ''), d.created_at) DESC, d.id DESC
            LIMIT ?
            """,
            (itemcode_sap, *sorted(SAP_DISPLAY_TIPOS), limit),
        ).fetchall()
    finally:
        conn.close()

    display_count = 0
    unitario_count = 0
    considered = 0

    for row in rows:
        inferred_mode = None
        mode_origin = (row["sap_mode_origen"] or "").strip().lower()
        if mode_origin == SAP_MODE_USUARIO:
            inferred_mode = _normalize_mode(row["sap_mode"])
        elif not mode_origin:
            inferred_mode = _normalize_mode(row["sap_mode"]) or _infer_mode_from_values(
                cantidad=row["cantidad"] or 0.0,
                cantidad_sap=row["cantidad_sap"],
                precio_neto=row["precio_neto"] or 0.0,
                precio_sap=row["precio_sap"],
                total=row["total"] or 0.0,
                factor=factor,
            )

        if inferred_mode == SAP_MODE_DISPLAY:
            display_count += 1
            considered += 1
        elif inferred_mode == SAP_MODE_UNITARIO:
            unitario_count += 1
            considered += 1

    return {
        "display": display_count,
        "unitario": unitario_count,
        "total": considered,
    }


def _get_line_context(codigo_oc: str, correlativo: int):
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT
                d.codigo_oc,
                d.correlativo,
                d.cantidad,
                d.precio_neto,
                d.total,
                d.factor_empaque,
                d.cantidad_sap,
                d.precio_sap,
                d.sap_mode,
                d.sap_mode_origen,
                d.sap_values_origen,
                d.itemcode_sap,
                d.codigo_mp,
                c.tipo_oc,
                c.rut_unidad
            FROM oc_detalle d
            INNER JOIN oc_cabecera c ON c.codigo_oc = d.codigo_oc
            WHERE d.codigo_oc = ? AND d.correlativo = ?
            """,
            (codigo_oc, correlativo),
        ).fetchone()
    finally:
        conn.close()


def _calculate_standard_values_from_context(context) -> tuple[float, float]:
    cantidad = context["cantidad"] or 0.0
    precio_neto = context["precio_neto"] or 0.0
    total = context["total"] or 0.0
    factor = _finite_or_default(context["factor_empaque"], 1.0)
    tipo_oc = (context["tipo_oc"] or "").strip().upper()
    base_price = _get_base_unit_price(cantidad, precio_neto, total)

    if tipo_oc == "CM" and factor > 0:
        return (
            round(float(cantidad or 0.0) * factor, 4),
            round(base_price / factor if factor > 0 else base_price, SAP_PRICE_DECIMALS),
        )

    mode = _normalize_mode(context["sap_mode"]) or SAP_MODE_UNITARIO
    display_factor = factor
    if mode == SAP_MODE_DISPLAY and supports_display_mode(tipo_oc):
        display_factor = get_display_factor(context["itemcode_sap"], factor)

    return _calculate_sap_values(
        cantidad=cantidad,
        precio_neto=precio_neto,
        total=total,
        factor=display_factor,
        mode=mode,
    )


def _find_recent_values_learning(
    conn,
    *,
    tipo_oc: str,
    rut_unidad: str,
    codigo_mp: str,
    itemcode_sap: str,
):
    match_clauses: list[str] = []
    params: list[str] = [(tipo_oc or "").strip()]
    if codigo_mp:
        match_clauses.append("COALESCE(codigo_mp, '') = ?")
        params.append(codigo_mp)
    if itemcode_sap:
        match_clauses.append("COALESCE(itemcode_sap, '') = ?")
        params.append(itemcode_sap)
    if not match_clauses:
        return None

    params.append((rut_unidad or "").strip())
    return conn.execute(
        f"""
        SELECT *
        FROM oc_linea_sap_ajuste_historial
        WHERE accion IN ('manual', 'revert')
          AND COALESCE(tipo_oc, '') = ?
          AND ({' OR '.join(match_clauses)})
        ORDER BY
          CASE WHEN COALESCE(rut_unidad, '') = ? THEN 0 ELSE 1 END,
          datetime(changed_at) DESC,
          id DESC
        LIMIT 1
        """,
        params,
    ).fetchone()


def _apply_learning_factors(base_qty: float, base_price: float, learning) -> Optional[tuple[float, float]]:
    if not learning:
        return None
    if (learning["accion"] or "").strip().lower() != "manual":
        return None

    qty_factor = _optional_float(learning["cantidad_factor"])
    price_factor = _optional_float(learning["precio_factor"])
    qty_changed = qty_factor is not None and not _is_close(qty_factor, 1.0, abs_tol=0.0001, rel_tol=0.0001)
    price_changed = price_factor is not None and not _is_close(price_factor, 1.0, abs_tol=0.0001, rel_tol=0.0001)
    if not qty_changed and not price_changed:
        return None

    next_qty = round(base_qty * qty_factor, 4) if qty_factor is not None else round(base_qty, 4)
    next_price = (
        round(base_price * price_factor, SAP_PRICE_DECIMALS)
        if price_factor is not None
        else round(base_price, SAP_PRICE_DECIMALS)
    )
    return next_qty, next_price


def _insert_values_history(
    conn,
    context,
    *,
    cantidad_base: float,
    precio_base: float,
    cantidad_anterior: float,
    precio_anterior: float,
    cantidad_nueva: float,
    precio_nuevo: float,
    accion: str,
    actor_user_id: Optional[int],
    actor_username: str,
    changed_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO oc_linea_sap_ajuste_historial (
            codigo_oc, correlativo, codigo_mp, itemcode_sap, tipo_oc, rut_unidad,
            cantidad_base, precio_base, cantidad_anterior, precio_anterior,
            cantidad_nueva, precio_nuevo, cantidad_factor, precio_factor,
            accion, actor_user_id, actor_username, changed_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            context["codigo_oc"],
            context["correlativo"],
            context["codigo_mp"],
            context["itemcode_sap"],
            context["tipo_oc"],
            context["rut_unidad"],
            cantidad_base,
            precio_base,
            cantidad_anterior,
            precio_anterior,
            cantidad_nueva,
            precio_nuevo,
            _ratio(cantidad_nueva, cantidad_base),
            _ratio(precio_nuevo, precio_base),
            accion,
            actor_user_id,
            actor_username or "",
            changed_at,
            changed_at,
            changed_at,
        ),
    )


def _validate_sap_value(value: float, field: str) -> None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} debe ser numerico")
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError(f"{field} debe ser un numero mayor o igual a cero")


def _ratio(numerator: float, denominator: float) -> Optional[float]:
    den = _optional_float(denominator)
    num = _optional_float(numerator)
    if den is None or num is None or _is_close(den, 0.0, abs_tol=0.000001, rel_tol=0.0):
        return None
    return round(num / den, 8)


def _optional_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _finite_or_default(value, default: float) -> float:
    parsed = _optional_float(value)
    if parsed is None:
        parsed = _optional_float(default)
    return float(parsed if parsed is not None else 0.0)


def _suggest_mode_from_history(history: dict[str, int]) -> Optional[str]:
    total = history["total"]
    if total < SAP_HISTORY_MIN_SAMPLE:
        return None

    display_ratio = history["display"] / total if total else 0
    unitario_ratio = history["unitario"] / total if total else 0

    if display_ratio >= SAP_HISTORY_CONFIDENCE:
        return SAP_MODE_DISPLAY
    if unitario_ratio >= SAP_HISTORY_CONFIDENCE:
        return SAP_MODE_UNITARIO
    return None


def _calculate_sap_values(
    *,
    cantidad: float,
    precio_neto: float,
    total: float,
    factor: float,
    mode: str,
) -> tuple[float, float]:
    normalized_mode = _normalize_mode(mode) or SAP_MODE_UNITARIO
    applied_factor = factor if normalized_mode == SAP_MODE_DISPLAY and factor > 1 else 1.0
    base_price = _get_base_unit_price(cantidad, precio_neto, total)
    cantidad_sap = round(float(cantidad or 0.0) * applied_factor, 4)
    precio_sap = round(base_price / applied_factor if applied_factor > 1 else base_price, SAP_PRICE_DECIMALS)
    return cantidad_sap, precio_sap


def _get_base_unit_price(cantidad: float, precio_neto: float, total: float) -> float:
    if precio_neto and precio_neto > 0:
        return float(precio_neto)
    if cantidad and total:
        return float(total) / float(cantidad)
    return 0.0


def _infer_mode_from_values(
    *,
    cantidad: float,
    cantidad_sap: Optional[float],
    precio_neto: float,
    precio_sap: Optional[float],
    total: float,
    factor: float,
) -> Optional[str]:
    if factor <= 1:
        return None

    base_price = _get_base_unit_price(cantidad, precio_neto, total)
    display_qty = float(cantidad or 0.0) * factor
    display_price = round(base_price / factor, SAP_PRICE_DECIMALS) if factor > 1 else round(base_price, SAP_PRICE_DECIMALS)
    unit_qty = float(cantidad or 0.0)
    unit_price = round(base_price, SAP_PRICE_DECIMALS)

    if cantidad_sap is not None and _is_close(cantidad_sap, display_qty, abs_tol=0.01):
        if precio_sap is None or _is_close(precio_sap, display_price, abs_tol=0.05):
            return SAP_MODE_DISPLAY

    if cantidad_sap is not None and _is_close(cantidad_sap, unit_qty, abs_tol=0.01):
        if precio_sap is None or _is_close(precio_sap, unit_price, abs_tol=0.05):
            return SAP_MODE_UNITARIO

    return None


def _is_close(a: Optional[float], b: Optional[float], abs_tol: float = 0.01, rel_tol: float = 0.02) -> bool:
    if a is None or b is None:
        return False
    diff = abs(float(a) - float(b))
    if diff <= abs_tol:
        return True
    reference = max(abs(float(a)), abs(float(b)), 1.0)
    return diff / reference <= rel_tol


def _normalize_mode(mode: Optional[str]) -> Optional[str]:
    normalized = (mode or "").strip().lower()
    if normalized in {SAP_MODE_UNITARIO, SAP_MODE_DISPLAY}:
        return normalized
    return None
