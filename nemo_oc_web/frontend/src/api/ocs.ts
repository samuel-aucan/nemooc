import api from './client'
import type {
  OrdenCompra,
  OcDetail,
  Stats,
  Filtros,
  Sugerencia,
  AnalyticsResponse,
} from '../types/oc'

export interface OcFilters {
  estado?: string[]
  estado_mp?: string[]
  tipo_oc?: string[]
  cartera?: string[]
  fecha_desde?: string
  fecha_hasta?: string
  busqueda?: string
}

export const getOcs = (filters: OcFilters = {}) =>
  api.get<OrdenCompra[]>('/ocs', { params: filters }).then(r => r.data)

export const getOc = (codigo: string) =>
  api.get<OcDetail>(`/ocs/${codigo}`).then(r => r.data)

export const getStats = () =>
  api.get<Stats>('/ocs/stats').then(r => r.data)

export const getFiltros = () =>
  api.get<Filtros>('/ocs/filtros').then(r => r.data)

export const updateEstado = (codigo: string, estado: string) =>
  api.put(`/ocs/${codigo}/estado`, { estado })

export const marcarIngresada = (codigo: string) =>
  api.put(`/ocs/${codigo}/ingresada`)

export const updateNotas = (codigo: string, notas: string) =>
  api.put(`/ocs/${codigo}/notas`, { notas })

export const getSapText = (codigo: string) =>
  api.get<{ text: string; excluidos: number[] }>(`/ocs/${codigo}/sap-text`).then(r => r.data)

export const asignarItemcode = (
  codigo: string, correlativo: number,
  itemcode_sap: string, descripcion_sap = '',
  origen: 'sugerencia' | 'manual' = 'manual',
) =>
  api.put(`/ocs/${codigo}/lineas/${correlativo}/asignar`, { itemcode_sap, descripcion_sap, origen })

export const limpiarAsignacion = (codigo: string, correlativo: number) =>
  api.delete(`/ocs/${codigo}/lineas/${correlativo}/asignar`)

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
