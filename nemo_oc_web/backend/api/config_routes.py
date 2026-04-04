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

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigOut)
def get_config():
    cfg = load_config()
    return ConfigOut(**asdict(cfg))


@router.put("", response_model=ConfigOut)
def update_config(body: ConfigIn):
    cfg = load_config()
    for field, val in body.model_dump(exclude_none=True).items():
        if hasattr(cfg, field):
            setattr(cfg, field, val)
    save_config(cfg)
    return ConfigOut(**asdict(cfg))


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
    pdf_path = out_dir / "Manual_Instalacion_NemoOC.pdf"

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
        filename="Manual_NemoOC.pdf",
    )
