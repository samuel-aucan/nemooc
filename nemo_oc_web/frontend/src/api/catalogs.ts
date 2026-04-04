import api from './client'

export interface CatalogStats {
  homologacion_cm: number
  homologacion_sap: number
  maestra: number
  cartera: number
  licitaciones: number
  redsalud: number
}

export interface PrivateHoldingCatalog {
  id: string
  nombre: string
  prefijo: string
  parser_type: string
  homo_file: string
  catalog_count: number
}

export interface CarteraSearchResult {
  cod_cliente: string
  rut: string
  razon: string
  comuna: string
  region_nombre: string
  cartera: string
  vendedor: string
}

export const getCatalogStats = () =>
  api.get<CatalogStats>('/catalogs/stats').then(r => r.data)

const uploadCatalog = (tipo: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<{ imported: number; errors: string[] }>(`/catalogs/${tipo}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const uploadHomologacion  = (f: File) => uploadCatalog('homologacion', f)
export const uploadMaestra       = (f: File) => uploadCatalog('maestra', f)
export const uploadCartera       = (f: File) => uploadCatalog('cartera', f)
export const uploadCorreos       = (f: File) => uploadCatalog('correos', f)
export const uploadRedsalud      = (f: File) => uploadCatalog('redsalud', f)
export const uploadLicitaciones  = (f: File) => uploadCatalog('licitaciones', f)
export const uploadPrivateHoldingCatalog = (holdingId: string, f: File) => uploadCatalog(`private/${holdingId}`, f)

export const getPrivateHoldings = () =>
  api.get<PrivateHoldingCatalog[]>('/catalogs/private-holdings').then(r => r.data)

export const searchMaestra = (q: string) =>
  api.get<{itemcode_sap: string, descripcion_sap: string}[]>(`/catalogs/maestra/search?q=${encodeURIComponent(q)}`)
    .then(r => r.data)

export const searchCartera = (q: string, limit = 8) =>
  api
    .get<CarteraSearchResult[]>(`/catalogs/cartera/search?q=${encodeURIComponent(q)}&limit=${limit}`)
    .then(r => r.data)
