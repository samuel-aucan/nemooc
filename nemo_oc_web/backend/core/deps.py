"""
Dependency injection: expone los singletons de servicios existentes.
"""
from backend.core.paths import ensure_nemo_oc_in_path

ensure_nemo_oc_in_path()


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
