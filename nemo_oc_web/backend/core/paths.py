"""
Centralizar la lógica de sys.path para evitar duplicación en 6 archivos.
"""
import sys
from pathlib import Path

def ensure_nemo_oc_in_path():
    """Agrega nemo_oc/ a sys.path si no está ya presente."""
    # Detectar si estamos empaquetados (PyInstaller)
    if getattr(sys, 'frozen', False):
        nemo_oc_dir = Path(sys._MEIPASS) / "nemo_oc"
    else:
        nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"

    nemo_oc_str = str(nemo_oc_dir)
    if nemo_oc_str not in sys.path:
        sys.path.insert(0, nemo_oc_str)

    return nemo_oc_dir
