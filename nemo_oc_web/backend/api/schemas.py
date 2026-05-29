"""
Pydantic schemas para request/response de la API REST.
"""
from typing import List, Optional
from pydantic import BaseModel


# ── OC ──────────────────────────────────────────────────────────────────────

class OrdenCompraOut(BaseModel):
    codigo_oc: str
    nombre_oc: str
    codigo_estado_mp: int
    estado_mp: str
    codigo_tipo: str
    tipo_oc: str
    fecha_creacion: str
    fecha_envio: str
    fecha_aceptacion: str
    fecha_cancelacion: str
    fecha_ultima_modificacion: str
    total_neto: float
    impuestos: float
    total: float
    porcentaje_iva: float
    descuentos: float
    cargos: float
    moneda: str
    codigo_organismo: str
    nombre_organismo: str
    rut_unidad: str
    codigo_unidad: str
    nombre_unidad: str
    direccion_unidad: str
    comuna_unidad: str
    region_unidad: str
    codigo_licitacion: str
    direccion_despacho: str
    direccion_facturacion: str
    codigo_proveedor: str
    nombre_proveedor: str
    rut_proveedor: str
    cliente_sap_sugerido: str
    cantidad_lineas: int
    estado_interno: str
    fecha_ingreso: Optional[str]
    responsable_ingreso_user_id: Optional[int] = None
    responsable_ingreso_username: str = ""
    ingresado_por_user_id: Optional[int] = None
    ingresado_por_username: str = ""
    ingreso_sap_acuerdo_global: bool = False
    notas: Optional[str]
    created_at: str = ""
    updated_at: str = ""
    # Enriquecidos desde cartera
    cartera: str = ""
    vendedor: str = ""
    region_nombre: str = ""
    razon_social: str = ""
    holding_nombre: str = ""


class LineaOCOut(BaseModel):
    codigo_oc: str
    correlativo: int
    codigo_categoria: int
    categoria: str
    codigo_producto_api: str
    codigo_mp: Optional[str]
    producto: str
    especificacion_comprador: str
    especificacion_proveedor: str
    cantidad: float
    unidad: str
    moneda: str
    precio_neto: float
    total_cargos: float
    total_descuentos: float
    total_impuestos: float
    total: float
    factor_empaque: float
    cantidad_sap: Optional[float]
    precio_sap: Optional[float]
    sap_mode: Optional[str]
    sap_mode_origen: Optional[str]
    itemcode_sap: Optional[str]
    descripcion_sap: Optional[str]
    estado_homologacion: str
    sap_mode_sugerido: Optional[str] = None
    sap_mode_historial_total: int = 0
    sap_mode_historial_display: int = 0
    sap_mode_historial_unitario: int = 0
    sap_values_origen: Optional[str] = None
    sap_values_updated_at: str = ""
    sap_values_updated_by_user_id: Optional[int] = None
    sap_values_updated_by_username: str = ""


class EstadoHistorialOut(BaseModel):
    id: int
    codigo_oc: str
    estado_anterior: Optional[str]
    estado_nuevo: str
    origen: str
    actor_user_id: Optional[int] = None
    actor_username: str = ""
    changed_at: str


class DocumentoFuenteOut(BaseModel):
    codigo_oc: str
    source_type: str
    source_locator: str = ""
    access_payload: Optional[dict] = None
    snapshot_type: str = ""
    snapshot_path: str = ""
    snapshot_sha256: str = ""
    snapshot_size_bytes: int = 0
    document_available: bool = False
    document_regenerable: bool = False
    last_verified_at: str = ""
    created_at: str = ""
    updated_at: str = ""


class OcDetailOut(BaseModel):
    cabecera: OrdenCompraOut
    lineas: List[LineaOCOut]
    historial_estados: List[EstadoHistorialOut]
    documento: Optional[DocumentoFuenteOut] = None


class OcListResponse(BaseModel):
    items: List[OrdenCompraOut]
    total: int
    limit: int
    offset: int


class StatsOut(BaseModel):
    total: int
    sin_homolog: int
    ingresadas: int


class AnalyticsSummaryOut(BaseModel):
    total_ocs: int
    total_lineas: int
    lineas_resueltas: int
    lineas_pendientes: int
    lineas_manuales: int
    lineas_sugeridas: int
    lineas_homologadas: int
    ocs_por_revisar: int
    monto_total: float
    monto_resuelto: float
    cobertura_lineas_pct: float
    cobertura_monto_pct: float
    cola_revision: int
    total_cola_sin_limite: int
    pendientes_con_texto: int
    pendientes_sin_texto: int


class AnalyticsDailyPointOut(BaseModel):
    fecha: str
    cantidad_ocs: int
    monto_total: float


class AnalyticsRankingItemOut(BaseModel):
    label: str
    cantidad_ocs: int
    monto_total: float


class AnalyticsTodayOut(BaseModel):
    fecha: str
    recibidas_ocs: int
    recibidas_lineas: int
    recibidas_monto: float
    ingresadas_ocs: int
    ingresadas_lineas: int
    ingresadas_monto: float
    same_day_ocs: int
    same_day_monto: float
    same_day_ratio_pct: float
    throughput_pct: float
    backlog_neto: int
    listas_sap: int
    bloqueadas: int
    aceptadas_sin_ingresar: int


class AnalyticsUserProductivityOut(BaseModel):
    user_id: Optional[int] = None
    username: str
    ocs_asignadas: int
    recibidas_hoy_asignadas: int
    same_day_ocs: int
    same_day_ratio_pct: float
    ingresadas_hoy: int
    ingresadas_total_rango: int
    lineas_ingresadas: int
    monto_ingresado: float
    privadas_ingresadas: int
    acuerdos_globales_ingresados: int
    backlog_pendiente: int


class AnalyticsAgingBucketOut(BaseModel):
    bucket: str
    cantidad_ocs: int
    monto_total: float


class AnalyticsAgingOut(BaseModel):
    listas_sap: List[AnalyticsAgingBucketOut] = []
    bloqueadas: List[AnalyticsAgingBucketOut] = []
    aceptadas_sin_ingresar: List[AnalyticsAgingBucketOut] = []


class AnalyticsFunnelItemOut(BaseModel):
    stage: str
    label: str
    cantidad_ocs: int
    monto_total: float


class AnalyticsPrivateOut(BaseModel):
    recibidas: int
    requieren_revision: int
    parser_fallido: int
    pdf_recuperable: int


class AnalyticsSyncHealthOut(BaseModel):
    running: bool = False
    active_tasks: List[str] = []
    last_mp_sync_at: Optional[str] = None
    next_sync_at: Optional[str] = None
    next_light_sync: Optional[str] = None
    errores_recientes: int = 0


class AnalyticsBlockingProductOut(BaseModel):
    label: str
    cantidad_lineas: int
    cantidad_ocs: int
    monto_total: float


class HoldingFiltroOut(BaseModel):
    id: str
    nombre: str


class FiltrosOut(BaseModel):
    estados_mp: List[str]
    tipos: List[str]
    carteras: List[str]
    holdings: List[HoldingFiltroOut] = []


class SapTextOut(BaseModel):
    text: str
    excluidos: List[int]


# ── Línea asignación ─────────────────────────────────────────────────────────

class AsignarItemcodeIn(BaseModel):
    itemcode_sap: str
    descripcion_sap: str = ""
    origen: str = "manual"  # 'sugerencia' | 'manual'


class SapModeIn(BaseModel):
    mode: str  # 'unitario' | 'display'


# ── Sugerencia ───────────────────────────────────────────────────────────────

class SapValuesIn(BaseModel):
    cantidad_sap: float
    precio_sap: float


class SapValuesOut(BaseModel):
    codigo_oc: str
    correlativo: int
    cantidad_sap: float
    precio_sap: float
    sap_values_origen: str
    sap_values_updated_at: str = ""
    sap_values_updated_by_user_id: Optional[int] = None
    sap_values_updated_by_username: str = ""


class SapValuesHistoryOut(BaseModel):
    id: int
    codigo_oc: str
    correlativo: int
    codigo_mp: Optional[str] = None
    itemcode_sap: Optional[str] = None
    tipo_oc: Optional[str] = None
    rut_unidad: Optional[str] = None
    cantidad_base: Optional[float] = None
    precio_base: Optional[float] = None
    cantidad_anterior: Optional[float] = None
    precio_anterior: Optional[float] = None
    cantidad_nueva: Optional[float] = None
    precio_nuevo: Optional[float] = None
    cantidad_factor: Optional[float] = None
    precio_factor: Optional[float] = None
    accion: str
    actor_user_id: Optional[int] = None
    actor_username: str = ""
    changed_at: str


class SugerenciaOut(BaseModel):
    itemcode_sap: str
    descripcion_sap: str
    descripcion_match: str
    frecuencia: int
    score: float
    estrellas: int  # 1-5


class ReviewQueueItemOut(BaseModel):
    codigo_oc: str
    correlativo: int
    fecha_envio: str
    tipo_oc: str
    nombre_organismo: str
    cliente_sap_sugerido: str
    cartera: str = ""
    estado_interno: str
    estado_homologacion: str
    itemcode_sap: Optional[str]
    descripcion_sap: Optional[str]
    producto: str
    especificacion_comprador: str
    cantidad: float
    total: float
    rut_unidad: str
    sugerencia_principal: Optional[SugerenciaOut] = None


class AnalyticsOut(BaseModel):
    summary: AnalyticsSummaryOut
    received_by_day: List[AnalyticsDailyPointOut] = []
    entered_by_day: List[AnalyticsDailyPointOut] = []
    top_clients: List[AnalyticsRankingItemOut] = []
    top_buyers: List[AnalyticsRankingItemOut] = []
    queue: List[ReviewQueueItemOut]
    productividad_hoy: Optional[AnalyticsTodayOut] = None
    productividad_usuarios: List[AnalyticsUserProductivityOut] = []
    aging: Optional[AnalyticsAgingOut] = None
    funnel: List[AnalyticsFunnelItemOut] = []
    salud_sync: Optional[AnalyticsSyncHealthOut] = None
    privadas: Optional[AnalyticsPrivateOut] = None
    top_blockers: List[AnalyticsBlockingProductOut] = []


# ── Auth ─────────────────────────────────────────────────────────────────────

class AuthUserOut(BaseModel):
    id: int
    username: str
    nombre_completo: str
    rol: str
    activo: bool
    last_login_at: str
    must_reset_password: bool = False
    auth_disabled: bool = False


class AuthBootstrapStatusOut(BaseModel):
    requires_setup: bool
    auth_disabled: bool = False


class AuthLoginIn(BaseModel):
    username: str
    password: str


class AuthBootstrapIn(BaseModel):
    username: str
    nombre_completo: str = ""
    password: str
    password_confirm: str


class AuthCreateUserIn(BaseModel):
    username: str
    nombre_completo: str = ""
    password: str
    password_confirm: str
    rol: str = "operador"


class AuthUpdateUserIn(BaseModel):
    nombre_completo: str = ""
    rol: str
    activo: bool


class AuthResetPasswordIn(BaseModel):
    password: str
    password_confirm: str


class AuthResetAccessOut(BaseModel):
    reset_token: str
    expires_at: str


class AuthCompleteResetIn(BaseModel):
    username: str
    token: str
    password: str
    password_confirm: str


# ── Auditoría ────────────────────────────────────────────────────────────────

class OcAuditoriaItem(BaseModel):
    codigo_oc: str
    tipo_oc: str
    estado_mp: str
    estado_interno: str
    fecha_envio: str
    nombre_organismo: str
    total_neto: float
    moneda: str


class AuditoriaResponse(BaseModel):
    aceptadas_sin_ingresar: List[OcAuditoriaItem]
    ingresadas_sin_aceptar: List[OcAuditoriaItem]


# ── Estado / Notas ───────────────────────────────────────────────────────────

class EstadoIn(BaseModel):
    estado: str


class IngresadaIn(BaseModel):
    acuerdo_global: bool = False


class ResponsableIn(BaseModel):
    user_id: Optional[int] = None


class ResponsableOut(BaseModel):
    id: int
    username: str
    nombre_completo: str = ""


class NotasIn(BaseModel):
    notas: str


class ImportarOcMpIn(BaseModel):
    codigo_oc: str


class ImportarOcMpOut(BaseModel):
    ok: bool
    created: bool
    codigo_oc: str
    message: str
    oc: OrdenCompraOut


# ── Sync ─────────────────────────────────────────────────────────────────────

class SyncMpIn(BaseModel):
    fecha_desde: str   # YYYY-MM-DD
    fecha_hasta: str   # YYYY-MM-DD
    solo_cm: bool = False
    ruts_filter: Optional[List[str]] = None  # RUTs normalizados (sin DV, sin puntos) para filtrar por cartera


class SyncGmailIn(BaseModel):
    pass  # usa config guardada


class SyncStartOut(BaseModel):
    sync_id: str


class ArtikosSyncIn(BaseModel):
    url: str  # link completo del email Artikos


class ArtikosSyncOut(BaseModel):
    ok: bool
    codigo_oc: str = ""
    nombre_organismo: str = ""
    cantidad_lineas: int = 0
    message: str


# ── Config ───────────────────────────────────────────────────────────────────

class ConfigOut(BaseModel):
    auth_enabled: bool
    api_ticket_last_chars: str
    codigo_empresa: str
    rut_proveedor: str
    homologacion_path: str
    maestra_path: str
    cartera_path: str
    correos_path: str
    theme: str
    color_theme: str
    auto_sync: bool
    auto_sync_days: int
    auto_sync_interval: int
    last_sync: str
    log_level: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password_configured: bool  # Solo indica si está configurada (sin devolver valor)
    smtp_enabled: bool
    redsalud_homo_path: str
    imap_server: str
    imap_port: int
    imap_folder: str
    imap_filter_from_configured: bool  # Solo indica si está configurada
    licitaciones_path: str
    sap_columns: List[str]
    sap_global_columns: List[str]
    oc_list_columns: List[str]


class ConfigIn(BaseModel):
    auth_enabled: Optional[bool] = None
    api_ticket: Optional[str] = None
    codigo_empresa: Optional[str] = None
    rut_proveedor: Optional[str] = None
    homologacion_path: Optional[str] = None
    maestra_path: Optional[str] = None
    cartera_path: Optional[str] = None
    correos_path: Optional[str] = None
    theme: Optional[str] = None
    color_theme: Optional[str] = None
    auto_sync: Optional[bool] = None
    auto_sync_days: Optional[int] = None
    auto_sync_interval: Optional[int] = None
    log_level: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_enabled: Optional[bool] = None
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    imap_folder: Optional[str] = None
    imap_filter_from: Optional[str] = None
    redsalud_homo_path: Optional[str] = None
    licitaciones_path: Optional[str] = None
    sap_columns: Optional[List[str]] = None
    sap_global_columns: Optional[List[str]] = None
    oc_list_columns: Optional[List[str]] = None


# ── Catálogos ─────────────────────────────────────────────────────────────────

class CatalogStatsOut(BaseModel):
    homologacion_cm: int
    homologacion_sap: int
    maestra: int
    cartera: int
    licitaciones: int
    redsalud: int


class CatalogImportOut(BaseModel):
    imported: int
    errors: List[str]


class PrivateHoldingCatalogOut(BaseModel):
    id: str
    nombre: str
    prefijo: str
    parser_type: str
    homo_file: str
    catalog_count: int


class CarteraSearchOut(BaseModel):
    cod_cliente: str
    rut: str
    razon: str
    comuna: str
    region_nombre: str
    cartera: str
    vendedor: str


class CorreoVendedorOut(BaseModel):
    id: int
    cartera: str
    nombre: str
    email: str
    activo: bool


class CorreoVendedorToggleIn(BaseModel):
    activo: bool


class HoldingRutOut(BaseModel):
    rut_norm: str
    rut_display: str
    nombre_sucursal: str


class HoldingRuleOut(BaseModel):
    id: int
    rule_type: str
    rule_value: str
    prioridad: int
    activo: bool
    notas: str


class HoldingOut(BaseModel):
    id: str
    nombre: str
    prefijo: str
    parser_type: str
    homo_file: str
    activo: bool
    catalog_count: int
    ruts: List[HoldingRutOut]
    rules: List[HoldingRuleOut]


class HoldingCreateIn(BaseModel):
    id: str
    nombre: str
    prefijo: str
    parser_type: str
    homo_file: str = ""
    activo: bool = True


class HoldingUpdateIn(BaseModel):
    nombre: str
    prefijo: str
    parser_type: str
    homo_file: str = ""
    activo: bool = True


class HoldingRutIn(BaseModel):
    rut: str
    rut_display: str = ""
    nombre_sucursal: str = ""


class HoldingRuleIn(BaseModel):
    rule_type: str
    rule_value: str
    prioridad: int = 100
    activo: bool = True
    notas: str = ""
