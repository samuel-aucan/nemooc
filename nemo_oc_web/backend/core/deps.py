"""
Dependency injection: expone los singletons de servicios existentes.
"""
import sys
from pathlib import Path

_nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))


def get_homologacion_service():
    from app.services.homologacion_service import get_homologacion_service as _get
    return _get()


def get_cartera_service():
    from app.services.cartera_service import get_cartera_service as _get
    return _get()


def get_maestra_service():
    from app.services.maestra_service import get_maestra_service as _get
    return _get()


def get_licitaciones_service():
    from app.services.licitaciones_service import get_licitaciones_service as _get
    return _get()


def get_email_service():
    from app.services.email_service import get_email_service as _get
    return _get()


def get_redsalud_homo_service():
    from app.services.redsalud_homo_service import get_redsalud_homo_service as _get
    return _get()
