import api from './client'

export interface AppConfig {
  auth_enabled: boolean
  api_ticket: string
  codigo_empresa: string
  rut_proveedor: string
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password: string
  smtp_enabled: boolean
  imap_server: string
  imap_port: number
  imap_folder: string
  imap_filter_from: string
  auto_sync: boolean
  auto_sync_days: number
  auto_sync_interval: number
  log_level: string
  theme: string
  color_theme: string
  sap_columns: string[]
  oc_list_columns: string[]
  [key: string]: unknown
}

export const getConfig = () =>
  api.get<AppConfig>('/config').then(r => r.data)

export const updateConfig = (data: Partial<AppConfig>) =>
  api.put<AppConfig>('/config', data).then(r => r.data)
