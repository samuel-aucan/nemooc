"""
Endpoints para el módulo GD Sin Facturar.
Consulta estado de OCs en Mercado Público para validar facturabilidad.
"""
import logging
import sys
import time
import threading
from pathlib import Path
from typing import List

from fastapi import APIRouter, Query
from pydantic import BaseModel

_nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))

from app.config import load_config
from app.services.mp_api_service import MercadoPublicoAPI, APIError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gd", tags=["gd"])

_OC_CACHE: dict[str, dict] = {}
_CACHE_LOCK = threading.Lock()
_LAST_MP_REQUEST_AT = 0.0
_MP_LOCK = threading.Lock()
MIN_MP_INTERVAL = 0.9

ESTADOS_FALLBACK = {
    0: "Enviada",
    4: "Enviada a proveedor",
    5: "En proceso",
    6: "Aceptada",
    9: "Cancelada",
    12: "Recepción Conforme",
    13: "Pendiente de recepcionar",
    14: "Recepcionada parcialmente",
    15: "Recepción conforme incompleta",
}

TRANSIENT_CODES = {429, 500, 502, 503, 504}


class BatchRequest(BaseModel):
    ocs: List[str]


def _wait_mp():
    global _LAST_MP_REQUEST_AT
    with _MP_LOCK:
        elapsed = time.monotonic() - _LAST_MP_REQUEST_AT
        if elapsed < MIN_MP_INTERVAL:
            time.sleep(MIN_MP_INTERVAL - elapsed)
        _LAST_MP_REQUEST_AT = time.monotonic()


def _is_transient(result: dict) -> bool:
    sc = int(result.get("statusCode") or result.get("codigoHttp") or 0)
    if sc in TRANSIENT_CODES:
        return True
    msg = str(result.get("error") or "").lower()
    return "429" in msg or "limito temporalmente" in msg


def _estado_recepcion_conforme(codigo: int, estado: str) -> bool:
    normalized = (estado or "").lower()
    for ch, rep in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        normalized = normalized.replace(ch, rep)
    normalized = " ".join(normalized.split())
    if codigo == 12:
        return True
    if "recepcion conforme" not in normalized:
        return False
    if "incompleta" in normalized or "parcial" in normalized:
        return False
    return normalized == "recepcion conforme"


def _consultar_oc(codigo_oc: str) -> dict:
    codigo = (codigo_oc or "").strip().upper()
    if not codigo:
        return {"oc": codigo_oc, "recepcionConforme": False, "estado": "", "codigoEstado": 0,
                "detalleRecepcion": "OC vacía.", "error": "OC vacía"}

    with _CACHE_LOCK:
        if codigo in _OC_CACHE:
            return _OC_CACHE[codigo]

    try:
        cfg = load_config()
        if not cfg.api_ticket:
            return {"oc": codigo, "recepcionConforme": False, "estado": "", "codigoEstado": 0,
                    "detalleRecepcion": "Sin ticket API configurado.", "error": "Sin ticket"}

        _wait_mp()
        api = MercadoPublicoAPI(ticket=cfg.api_ticket, codigo_empresa=cfg.codigo_empresa)
        raw = api.obtener_detalle_oc(codigo)
        codigo_estado = int(raw.get("CodigoEstado") or 0)

        try:
            from app.services.transform_service import resolve_estado_mp
            estado = resolve_estado_mp(raw.get("Estado", ""), codigo_estado)
        except Exception:
            estado = str(raw.get("Estado", "") or "")

        estado = estado or ESTADOS_FALLBACK.get(codigo_estado, "")
        recepcion = _estado_recepcion_conforme(codigo_estado, estado)
        detalle = ("OC con Recepción Conforme en Mercado Público." if recepcion
                   else f"Estado Mercado Público: {estado or 'sin estado'}.")

        result = {"oc": codigo, "recepcionConforme": recepcion, "estado": estado,
                  "codigoEstado": codigo_estado, "detalleRecepcion": detalle, "error": None}

    except APIError as exc:
        result = {"oc": codigo, "recepcionConforme": False, "estado": "", "codigoEstado": 0,
                  "statusCode": getattr(exc, "status_code", 0),
                  "detalleRecepcion": "No se pudo consultar Mercado Público.", "error": str(exc)}
        logger.warning("APIError consultando GD OC %s: %s", codigo, exc)
    except Exception as exc:
        result = {"oc": codigo, "recepcionConforme": False, "estado": "", "codigoEstado": 0,
                  "statusCode": 0,
                  "detalleRecepcion": "Error local consultando Mercado Público.", "error": str(exc)}
        logger.warning("Error consultando GD OC %s: %s", codigo, exc)

    # Solo cachear si tiene recepción conforme (estado final).
    # Si no tiene recepción, volver a consultar la próxima vez.
    if result.get("recepcionConforme") and not _is_transient(result):
        with _CACHE_LOCK:
            _OC_CACHE[codigo] = result
    return result


@router.get("/oc-status")
def get_oc_status(oc: str = Query(...)):
    return _consultar_oc(oc)


@router.post("/oc-status/batch")
def batch_oc_status(body: BatchRequest):
    seen: set[str] = set()
    unique = []
    for oc in body.ocs:
        c = (oc or "").strip().upper()
        if c and c not in seen:
            seen.add(c)
            unique.append(c)
    results = [_consultar_oc(c) for c in unique]
    return {"results": results, "count": len(results)}
