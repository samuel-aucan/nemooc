import api from './client'

export interface HoldingRut {
  rut_norm: string
  rut_display: string
  nombre_sucursal: string
}

export interface HoldingRule {
  id: number
  rule_type: string
  rule_value: string
  prioridad: number
  activo: boolean
  notas: string
}

export interface Holding {
  id: string
  nombre: string
  prefijo: string
  parser_type: string
  homo_file: string
  activo: boolean
  catalog_count: number
  ruts: HoldingRut[]
  rules: HoldingRule[]
}

export interface HoldingPayload {
  nombre: string
  prefijo: string
  parser_type: string
  homo_file?: string
  activo: boolean
}

export interface HoldingCreatePayload extends HoldingPayload {
  id: string
}

export interface HoldingRutPayload {
  rut: string
  rut_display?: string
  nombre_sucursal?: string
}

export interface HoldingRulePayload {
  rule_type: string
  rule_value: string
  prioridad: number
  activo: boolean
  notas?: string
}

export const getHoldings = () =>
  api.get<Holding[]>('/holdings').then(r => r.data)

export const createHolding = (payload: HoldingCreatePayload) =>
  api.post<Holding>('/holdings', payload).then(r => r.data)

export const updateHolding = (holdingId: string, payload: HoldingPayload) =>
  api.put<Holding>(`/holdings/${holdingId}`, payload).then(r => r.data)

export const upsertHoldingRut = (holdingId: string, payload: HoldingRutPayload) =>
  api.post<Holding>(`/holdings/${holdingId}/ruts`, payload).then(r => r.data)

export const deleteHoldingRut = (holdingId: string, rutNorm: string) =>
  api.delete<Holding>(`/holdings/${holdingId}/ruts/${encodeURIComponent(rutNorm)}`).then(r => r.data)

export const createHoldingRule = (holdingId: string, payload: HoldingRulePayload) =>
  api.post<Holding>(`/holdings/${holdingId}/rules`, payload).then(r => r.data)

export const updateHoldingRule = (holdingId: string, ruleId: number, payload: HoldingRulePayload) =>
  api.put<Holding>(`/holdings/${holdingId}/rules/${ruleId}`, payload).then(r => r.data)

export const deleteHoldingRule = (holdingId: string, ruleId: number) =>
  api.delete<Holding>(`/holdings/${holdingId}/rules/${ruleId}`).then(r => r.data)
