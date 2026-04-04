"""
CRUD web para administracion de holdings privados.
"""
import sqlite3
import sys
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException

_nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))

from app.services.holding_admin_service import (
    create_holding,
    create_holding_rule,
    delete_holding_rule,
    delete_holding_rut,
    list_holdings_admin,
    update_holding,
    update_holding_rule,
    upsert_holding_rut,
)
from .schemas import (
    HoldingCreateIn,
    HoldingOut,
    HoldingRuleIn,
    HoldingRuleOut,
    HoldingRutIn,
    HoldingRutOut,
    HoldingUpdateIn,
)

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


def _serialize_holding(item) -> HoldingOut:
    return HoldingOut(
        id=item.id,
        nombre=item.nombre,
        prefijo=item.prefijo,
        parser_type=item.parser_type,
        homo_file=item.homo_file,
        activo=item.activo,
        catalog_count=item.catalog_count,
        ruts=[
            HoldingRutOut(
                rut_norm=rut.rut_norm,
                rut_display=rut.rut_display,
                nombre_sucursal=rut.nombre_sucursal,
            )
            for rut in item.ruts
        ],
        rules=[
            HoldingRuleOut(
                id=rule.id,
                rule_type=rule.rule_type,
                rule_value=rule.rule_value,
                prioridad=rule.prioridad,
                activo=rule.activo,
                notas=rule.notas,
            )
            for rule in item.rules
        ],
    )


def _get_holding_or_404(holding_id: str) -> HoldingOut:
    for item in list_holdings_admin():
        if item.id == holding_id:
            return _serialize_holding(item)
    raise HTTPException(404, detail=f"Holding no existe: {holding_id}")


@router.get("", response_model=list[HoldingOut])
def list_holdings_endpoint():
    return [_serialize_holding(item) for item in list_holdings_admin()]


@router.post("", response_model=HoldingOut)
def create_holding_endpoint(payload: HoldingCreateIn):
    try:
        create_holding(
            holding_id=payload.id,
            nombre=payload.nombre,
            prefijo=payload.prefijo,
            parser_type=payload.parser_type,
            homo_file=payload.homo_file,
            activo=payload.activo,
        )
        return _get_holding_or_404(payload.id.strip().lower())
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(400, detail=f"No se pudo crear el holding: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@router.put("/{holding_id}", response_model=HoldingOut)
def update_holding_endpoint(holding_id: str, payload: HoldingUpdateIn):
    try:
        update_holding(
            holding_id=holding_id,
            nombre=payload.nombre,
            prefijo=payload.prefijo,
            parser_type=payload.parser_type,
            homo_file=payload.homo_file,
            activo=payload.activo,
        )
        return _get_holding_or_404(holding_id)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@router.post("/{holding_id}/ruts", response_model=HoldingOut)
def upsert_holding_rut_endpoint(holding_id: str, payload: HoldingRutIn):
    try:
        _get_holding_or_404(holding_id)
        upsert_holding_rut(
            holding_id=holding_id,
            rut_value=payload.rut,
            rut_display=payload.rut_display,
            nombre_sucursal=payload.nombre_sucursal,
        )
        return _get_holding_or_404(holding_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@router.delete("/{holding_id}/ruts/{rut_norm}", response_model=HoldingOut)
def delete_holding_rut_endpoint(holding_id: str, rut_norm: str):
    try:
        _get_holding_or_404(holding_id)
        delete_holding_rut(holding_id, unquote(rut_norm))
        return _get_holding_or_404(holding_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@router.post("/{holding_id}/rules", response_model=HoldingOut)
def create_holding_rule_endpoint(holding_id: str, payload: HoldingRuleIn):
    try:
        _get_holding_or_404(holding_id)
        create_holding_rule(
            holding_id=holding_id,
            rule_type=payload.rule_type,
            rule_value=payload.rule_value,
            prioridad=payload.prioridad,
            activo=payload.activo,
            notas=payload.notas,
        )
        return _get_holding_or_404(holding_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@router.put("/{holding_id}/rules/{rule_id}", response_model=HoldingOut)
def update_holding_rule_endpoint(holding_id: str, rule_id: int, payload: HoldingRuleIn):
    try:
        _get_holding_or_404(holding_id)
        update_holding_rule(
            rule_id=rule_id,
            holding_id=holding_id,
            rule_type=payload.rule_type,
            rule_value=payload.rule_value,
            prioridad=payload.prioridad,
            activo=payload.activo,
            notas=payload.notas,
        )
        return _get_holding_or_404(holding_id)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@router.delete("/{holding_id}/rules/{rule_id}", response_model=HoldingOut)
def delete_holding_rule_endpoint(holding_id: str, rule_id: int):
    try:
        _get_holding_or_404(holding_id)
        delete_holding_rule(holding_id, rule_id)
        return _get_holding_or_404(holding_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc
