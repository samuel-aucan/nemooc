export interface OrdenCompra {
  codigo_oc: string
  nombre_oc: string
  codigo_estado_mp: number
  estado_mp: string
  codigo_tipo: string
  tipo_oc: string
  fecha_creacion: string
  fecha_envio: string
  fecha_aceptacion: string
  fecha_cancelacion: string
  fecha_ultima_modificacion: string
  total_neto: number
  impuestos: number
  total: number
  porcentaje_iva: number
  descuentos: number
  cargos: number
  moneda: string
  codigo_organismo: string
  nombre_organismo: string
  rut_unidad: string
  codigo_unidad: string
  nombre_unidad: string
  direccion_unidad: string
  comuna_unidad: string
  region_unidad: string
  codigo_proveedor: string
  nombre_proveedor: string
  rut_proveedor: string
  cliente_sap_sugerido: string
  cantidad_lineas: number
  estado_interno: string
  fecha_ingreso: string | null
  notas: string | null
  cartera: string
  region_nombre: string
  razon_social: string
}

export interface LineaOC {
  codigo_oc: string
  correlativo: number
  codigo_categoria: number
  categoria: string
  codigo_producto_api: string
  codigo_mp: string | null
  producto: string
  especificacion_comprador: string
  especificacion_proveedor: string
  cantidad: number
  unidad: string
  moneda: string
  precio_neto: number
  total_cargos: number
  total_descuentos: number
  total_impuestos: number
  total: number
  factor_empaque: number
  cantidad_sap: number | null
  precio_sap: number | null
  itemcode_sap: string | null
  descripcion_sap: string | null
  estado_homologacion: string
}

export interface OcDetail {
  cabecera: OrdenCompra
  lineas: LineaOC[]
}

export interface Stats {
  total: number
  sin_homolog: number
  ingresadas: number
}

export interface Filtros {
  estados_mp: string[]
  tipos: string[]
  carteras: string[]
}

export interface Sugerencia {
  itemcode_sap: string
  descripcion_sap: string
  descripcion_match: string
  frecuencia: number
  score: number
  estrellas: number
}

export interface AnalyticsSummary {
  total_ocs: number
  total_lineas: number
  lineas_resueltas: number
  lineas_pendientes: number
  lineas_manuales: number
  lineas_sugeridas: number
  lineas_homologadas: number
  ocs_por_revisar: number
  monto_total: number
  monto_resuelto: number
  cobertura_lineas_pct: number
  cobertura_monto_pct: number
  cola_revision: number
  total_cola_sin_limite: number
  pendientes_con_sugerencia: number
  pendientes_sin_sugerencia: number
}

export interface ReviewQueueItem {
  codigo_oc: string
  correlativo: number
  fecha_envio: string
  tipo_oc: string
  nombre_organismo: string
  cliente_sap_sugerido: string
  cartera: string
  estado_interno: string
  estado_homologacion: string
  itemcode_sap: string | null
  descripcion_sap: string | null
  producto: string
  especificacion_comprador: string
  cantidad: number
  total: number
  rut_unidad: string
  sugerencia_principal: Sugerencia | null
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary
  queue: ReviewQueueItem[]
}
