import api from './client'

export const startSyncMp = (fecha_desde: string, fecha_hasta: string, solo_cm: boolean) =>
  api.post<{ sync_id: string }>('/sync/mercado-publico', { fecha_desde, fecha_hasta, solo_cm })
    .then(r => r.data.sync_id)

export const startSyncMpLight = (fecha_desde?: string, fecha_hasta?: string) =>
  api.post<{ sync_id: string }>('/sync/mp-estados-ligero', null, {
    params: { fecha_desde, fecha_hasta },
  }).then(r => r.data.sync_id)

export const startSyncGmail = () =>
  api.post<{ sync_id: string }>('/sync/gmail', {}).then(r => r.data.sync_id)

export const testApi = () =>
  api.post<{ ok: boolean; message: string }>('/sync/test-api').then(r => r.data)

export const getGlobalLogs = () =>
  api.get<{ logs: {time: string, message: string}[] }>('/sync/logs').then(r => r.data.logs)

export interface ArtikosSyncResult {
  ok: boolean
  codigo_oc: string
  nombre_organismo: string
  cantidad_lineas: number
  message: string
}

export const importarArtikoOC = (url: string) =>
  api.post<ArtikosSyncResult>('/sync/artikos', { url }).then(r => r.data)
