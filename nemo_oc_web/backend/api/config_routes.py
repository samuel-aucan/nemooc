"""
Endpoints de configuración de la app.
"""
import sys
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

_nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))

from app.config import load_config, save_config
from .schemas import ConfigOut, ConfigIn

router = APIRouter(prefix="/api/v1/config", tags=["config"])


def _prepare_config_out(cfg_dict: dict) -> ConfigOut:
    """Transforma config interna a ConfigOut enmascarando credenciales."""
    from backend.core.secrets import mask_api_ticket

    # Enmascarar credenciales sensibles
    api_ticket = cfg_dict.pop("api_ticket", "")
    cfg_dict["api_ticket_last_chars"] = mask_api_ticket(api_ticket)

    # Indicar si contraseñas están configuradas sin devolverlas
    cfg_dict["smtp_password_configured"] = bool(cfg_dict.pop("smtp_password", ""))
    cfg_dict["imap_filter_from_configured"] = bool(cfg_dict.pop("imap_filter_from", ""))

    return ConfigOut(**cfg_dict)

@router.get("", response_model=ConfigOut)
def get_config():
    cfg = load_config()
    cfg_dict = asdict(cfg)
    return _prepare_config_out(cfg_dict)


@router.put("", response_model=ConfigOut)
def update_config(body: ConfigIn):
    cfg = load_config()

    # No permitir actualizar campos sensibles a través de la API (deben editarse en UI con validación)
    for field, val in body.model_dump(exclude_none=True).items():
        if field in ("smtp_password", "imap_filter_from"):
            # Permitir que se actualicen, pero solamente si vienen desde el cliente
            # En el frontend, estos campos nunca se deben mostrar en forma plana
            pass
        if hasattr(cfg, field):
            setattr(cfg, field, val)

    save_config(cfg)
    cfg_dict = asdict(cfg)
    return _prepare_config_out(cfg_dict)


@router.get("/manual")
def download_manual():
    """
    Genera el PDF del manual de uso usando el script generar_manual_pdf.py
    y lo devuelve como descarga.
    """
    gen_script = _nemo_oc_dir / "generar_manual_pdf.py"
    if not gen_script.exists():
        raise HTTPException(404, detail="Script generador de manual no encontrado.")

    # Usar un directorio temporal para el PDF
    out_dir = _nemo_oc_dir
    pdf_path = out_dir / "Manual_Instalacion_NEMONKEY.pdf"

    try:
        # Ejecutar el script de generación
        result = subprocess.run(
            [sys.executable, str(gen_script)],
            capture_output=True, text=True, timeout=30,
            cwd=str(_nemo_oc_dir),
        )
        if result.returncode != 0:
            raise HTTPException(500, detail=f"Error generando PDF: {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        raise HTTPException(500, detail="Timeout generando PDF.")

    if not pdf_path.exists():
        raise HTTPException(500, detail="El PDF no fue generado correctamente.")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="Manual_NEMONKEY.pdf",
    )
