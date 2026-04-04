"""
Endpoints para carga de catálogos Excel y consulta de estadísticas.
"""
import sys
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query

_nemo_oc_dir = Path(__file__).parent.parent.parent.parent / "nemo_oc"
if str(_nemo_oc_dir) not in sys.path:
    sys.path.insert(0, str(_nemo_oc_dir))

from app.config import (
    CORREOS_FILENAME,
    LICITACIONES_FILENAME,
    REDSALUD_HOMO_FILENAME,
    CARTERA_FILENAME,
    HOMOLOGACION_FILENAME,
    MAESTRA_FILENAME,
    get_catalogs_dir,
    load_config,
    save_config,
)
from app.repositories.homologacion_repo import count_homologacion
from app.repositories.cartera_repo import count_cartera
from app.repositories.maestra_repo import count_maestra
from app.repositories.licitaciones_repo import count_licitaciones
from .schemas import CatalogStatsOut, CatalogImportOut, PrivateHoldingCatalogOut, CarteraSearchOut

router = APIRouter(prefix="/api/catalogs", tags=["catalogs"])


def _save_upload(file: UploadFile, filename: str) -> Path:
    """Guarda el archivo subido en catalogs/ y retorna la ruta."""
    dest = get_catalogs_dir() / filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest


def _persist_catalog_path(field_name: str, dest: Path) -> None:
    """Persiste en settings.json la ruta final del catálogo subido."""
    cfg = load_config()
    setattr(cfg, field_name, str(dest))
    save_config(cfg)


@router.get("/stats", response_model=CatalogStatsOut)
def catalog_stats():
    try:
        homo = count_homologacion()
        return CatalogStatsOut(
            homologacion_cm=homo["cm"],
            homologacion_sap=homo["sap"],
            maestra=count_maestra(),
            cartera=count_cartera(),
            licitaciones=count_licitaciones(),
            redsalud=_count_redsalud(),
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))


def _count_redsalud() -> int:
    try:
        from app.services.redsalud_homo_service import get_redsalud_homo_service
        return get_redsalud_homo_service().count()
    except Exception:
        return 0


@router.post("/homologacion", response_model=CatalogImportOut)
async def upload_homologacion(file: UploadFile = File(...)):
    dest = _save_upload(file, HOMOLOGACION_FILENAME)
    from app.services.homologacion_service import get_homologacion_service
    svc = get_homologacion_service()
    cnt, errors = svc.cargar_homologacion_excel(str(dest))
    svc.reload()
    _persist_catalog_path("homologacion_path", dest)
    return CatalogImportOut(imported=cnt, errors=errors)


@router.post("/maestra", response_model=CatalogImportOut)
async def upload_maestra(file: UploadFile = File(...)):
    dest = _save_upload(file, MAESTRA_FILENAME)
    from app.services.homologacion_service import get_homologacion_service
    from app.services.maestra_service import get_maestra_service
    svc_homo = get_homologacion_service()
    cnt, errors = svc_homo.cargar_maestra_sap(str(dest))
    svc_homo.reload()
    svc_maestra = get_maestra_service()
    svc_maestra.cargar_excel(str(dest))
    svc_maestra.reload()
    _persist_catalog_path("maestra_path", dest)
    return CatalogImportOut(imported=cnt, errors=errors)


@router.get("/maestra/search")
def search_maestra_endpoint(q: str):
    if not q or len(q) < 3:
        return []
    from app.repositories.maestra_repo import search_maestra
    return search_maestra(q)


@router.post("/cartera", response_model=CatalogImportOut)
async def upload_cartera(file: UploadFile = File(...)):
    dest = _save_upload(file, CARTERA_FILENAME)
    from app.services.cartera_service import get_cartera_service
    svc = get_cartera_service()
    cnt, errors = svc.cargar_cartera_excel(str(dest))
    svc.reload()
    _persist_catalog_path("cartera_path", dest)
    return CatalogImportOut(imported=cnt, errors=errors)


@router.get("/cartera/search", response_model=list[CarteraSearchOut])
def search_cartera_endpoint(q: str = Query(default="", min_length=2), limit: int = Query(default=8, ge=1, le=20)):
    from app.services.cartera_service import get_cartera_service

    items = get_cartera_service().search(q, limit=limit)
    return [
        CarteraSearchOut(
            cod_cliente=item.cod_cliente,
            rut=item.rut,
            razon=item.razon,
            comuna=item.comuna,
            region_nombre=item.region_nombre,
            cartera=item.cartera,
            vendedor=item.vendedor,
        )
        for item in items
    ]


@router.post("/correos", response_model=CatalogImportOut)
async def upload_correos(file: UploadFile = File(...)):
    dest = _save_upload(file, CORREOS_FILENAME)
    from app.services.email_service import get_email_service
    ok, msg = get_email_service().cargar_correos(str(dest))
    if ok:
        _persist_catalog_path("correos_path", dest)
    return CatalogImportOut(imported=1 if ok else 0, errors=[] if ok else [msg])


@router.post("/redsalud", response_model=CatalogImportOut)
async def upload_redsalud(file: UploadFile = File(...)):
    dest = _save_upload(file, REDSALUD_HOMO_FILENAME)
    from app.services.redsalud_homo_service import get_redsalud_homo_service
    from app.services.private_catalog_service import import_private_catalog

    svc = get_redsalud_homo_service()
    cnt, errors = svc.cargar_excel(str(dest))
    svc.reload()
    import_private_catalog("redsalud", str(dest), file.filename or REDSALUD_HOMO_FILENAME)
    _persist_catalog_path("redsalud_homo_path", dest)
    return CatalogImportOut(imported=cnt, errors=errors)


@router.post("/licitaciones", response_model=CatalogImportOut)
async def upload_licitaciones(file: UploadFile = File(...)):
    dest = _save_upload(file, LICITACIONES_FILENAME)
    from app.services.licitaciones_service import get_licitaciones_service
    svc = get_licitaciones_service()
    cnt, errors = svc.importar_lic(str(dest))
    svc.reload()
    _persist_catalog_path("licitaciones_path", dest)
    return CatalogImportOut(imported=cnt, errors=errors)


@router.get("/private-holdings", response_model=list[PrivateHoldingCatalogOut])
def list_private_holdings_endpoint():
    from app.services.private_catalog_service import list_private_holdings

    return [
        PrivateHoldingCatalogOut(
            id=item.id,
            nombre=item.nombre,
            prefijo=item.prefijo,
            parser_type=item.parser_type,
            homo_file=item.homo_file,
            catalog_count=item.catalog_count,
        )
        for item in list_private_holdings()
    ]


@router.post("/private/{holding_id}", response_model=CatalogImportOut)
async def upload_private_catalog(holding_id: str, file: UploadFile = File(...)):
    from app.services.private_catalog_service import import_private_catalog, list_private_holdings

    holdings = {item.id: item for item in list_private_holdings()}
    if holding_id not in holdings:
        raise HTTPException(404, detail=f"Holding no existe: {holding_id}")

    filename = holdings[holding_id].homo_file or f"HOMO_{holding_id.upper()}.xlsx"
    dest = _save_upload(file, filename)
    imported, errors = import_private_catalog(holding_id, str(dest), file.filename or filename)
    return CatalogImportOut(imported=imported, errors=errors)
