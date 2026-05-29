import api from './client'
import type {
  OrdenCompra,
  OcDetail,
  Stats,
  Filtros,
  ResponsableIngreso,
  SapValuesHistory,
  Sugerencia,
  AnalyticsResponse,
  AuditoriaResponse,
} from '../types/oc'

export interface OcFilters {
  estado?: string[]
  estado_mp?: string[]
  tipo_oc?: string[]
  cartera?: string[]
  holding?: string[]
  responsable?: string[]
  fecha_desde?: string
  fecha_hasta?: string
  fecha_ingreso_desde?: string
  fecha_ingreso_hasta?: string
  busqueda?: string
}

export interface OcListResponse {
  items: OrdenCompra[]
  total: number
  limit: number
  offset: number
}

export const getOcs = (filters: OcFilters = {}, limit = 50, offset = 0) =>
  api.get<OcListResponse>('/ocs', { params: { ...filters, limit, offset } }).then(r => r.data)

export const getOc = (codigo: string) =>
  api.get<OcDetail>(`/ocs/${codigo}`).then(r => r.data)

export const getStats = () =>
  api.get<Stats>('/ocs/stats').then(r => r.data)

export const getFiltros = () =>
  api.get<Filtros>('/ocs/filtros').then(r => r.data)

export const updateEstado = (codigo: string, estado: string) =>
  api.put(`/ocs/${codigo}/estado`, { estado })

export const marcarIngresada = (codigo: string, acuerdoGlobal = false) =>
  api.put(`/ocs/${codigo}/ingresada`, { acuerdo_global: acuerdoGlobal })

export const updateResponsableIngreso = (codigo: string, userId: number | null) =>
  api.put(`/ocs/${codigo}/responsable`, { user_id: userId })

export const getResponsablesIngreso = () =>
  api.get<ResponsableIngreso[]>('/ocs/responsables').then(r => r.data)

export const updateNotas = (codigo: string, notas: string) =>
  api.put(`/ocs/${codigo}/notas`, { notas })

export const getSapText = (codigo: string) =>
  api.get<{ text: string; excluidos: number[] }>(`/ocs/${codigo}/sap-text`).then(r => r.data)

export const importarOcMp = (codigo_oc: string) =>
  api.post<{ ok: boolean; created: boolean; codigo_oc: string; message: string; oc: OrdenCompra }>('/ocs/importar-mp', { codigo_oc }).then(r => r.data)

export const refreshOcMpStatus = (codigo: string) =>
  api.post<{
    ok: boolean
    updated: boolean
    estado_mp: string
    codigo_estado_mp: number
    refreshed_at: string
  }>(`/ocs/${codigo}/refresh-mp-status`).then(r => r.data)

export const asignarItemcode = (
  codigo: string, correlativo: number,
  itemcode_sap: string, descripcion_sap = '',
  origen: 'sugerencia' | 'manual' = 'manual',
) =>
  api.put(`/ocs/${codigo}/lineas/${correlativo}/asignar`, { itemcode_sap, descripcion_sap, origen })

export const limpiarAsignacion = (codigo: string, correlativo: number) =>
  api.delete(`/ocs/${codigo}/lineas/${correlativo}/asignar`)

export const updateSapMode = (codigo: string, correlativo: number, mode: 'unitario' | 'display') =>
  api.put(`/ocs/${codigo}/lineas/${correlativo}/sap-mode`, { mode })

export const updateSapValues = (
  codigo: string,
  correlativo: number,
  values: { cantidad_sap: number; precio_sap: number },
) =>
  api.put(`/ocs/${codigo}/lineas/${correlativo}/sap-values`, values).then(r => r.data)

export const resetSapValues = (codigo: string, correlativo: number) =>
  api.delete(`/ocs/${codigo}/lineas/${correlativo}/sap-values`).then(r => r.data)

export const getSapValuesHistory = (codigo: string, correlativo: number) =>
  api.get<SapValuesHistory[]>(`/ocs/${codigo}/lineas/${correlativo}/sap-values/historial`).then(r => r.data)

export const getSugerencias = (codigo: string, correlativo: number) =>
  api.get<Sugerencia[]>(`/ocs/${codigo}/lineas/${correlativo}/sugerencias`).then(r => r.data)

export const getAnalytics = (params: {
  fecha_desde?: string
  fecha_hasta?: string
  limit?: number
} = {}) =>
  api.get<AnalyticsResponse>('/ocs/analytics', { params }).then(r => r.data)

export const exportAll = (filters: OcFilters = {}) => {
  const parts: string[] = []
  for (const [key, value] of Object.entries(filters)) {
    if (value == null || value === '' || value === undefined) continue
    if (Array.isArray(value)) {
      for (const v of value) {
        if (v != null && v !== '') parts.push(`${key}=${encodeURIComponent(v)}`)
      }
    } else {
      parts.push(`${key}=${encodeURIComponent(value as string)}`)
    }
  }
  window.open(`/api/ocs/export-all?${parts.join('&')}`, '_blank')
}

export const exportOc = (codigo: string) =>
  window.open(`/api/ocs/${codigo}/export-excel`, '_blank')

export const openOcDocument = (codigo: string) =>
  window.open(`/api/v1/ocs/${encodeURIComponent(codigo)}/documento`, '_blank')

export const printOcDocument = (codigo: string) =>
  window.open(`/api/v1/ocs/${encodeURIComponent(codigo)}/documento?auto_print=1`, '_blank')

export const downloadOcDocumentHtml = (codigo: string) =>
  window.open(`/api/v1/ocs/${encodeURIComponent(codigo)}/documento?download=1`, '_blank')

export const downloadOcDocumentPdf = (codigo: string) =>
  window.open(`/api/v1/ocs/${encodeURIComponent(codigo)}/documento-pdf`, '_blank')

export const rehomologarPrivada = (codigo: string) =>
  api.post<{ actualizadas: number }>(`/ocs/${codigo}/rehomologar-privada`).then(r => r.data)

export const getAuditoria = (params: { fecha_desde?: string; fecha_hasta?: string } = {}) =>
  api.get<AuditoriaResponse>('/ocs/auditoria', { params }).then(r => r.data)
