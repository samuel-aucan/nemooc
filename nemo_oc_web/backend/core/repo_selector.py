"""
Selector de repositorio de datos.
Lee DATA_SOURCE del entorno: 'sqlite' (default) o 'supabase'.

Uso en routes:
    from backend.core.repo_selector import oc_repo as oc_repository
    # luego usar igual que antes: oc_repository.get_oc(...)
"""
import os
import logging

logger = logging.getLogger(__name__)

_DATA_SOURCE = os.getenv("DATA_SOURCE", "sqlite").lower().strip()

if _DATA_SOURCE == "supabase":
    logger.info("[repo_selector] Fuente de datos: SUPABASE")
    from backend import supabase_oc_repository as oc_repo
else:
    logger.info("[repo_selector] Fuente de datos: SQLITE")
    from app.repositories import oc_repository as oc_repo  # type: ignore

__all__ = ["oc_repo"]
