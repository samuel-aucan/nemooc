export const fmtMoney = (value: number, moneda = 'CLP') =>
  new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: moneda,
    maximumFractionDigits: 0,
  }).format(value)

export const fmtDate = (iso: string) => {
  if (!iso) return ''
  return iso.slice(0, 10)
}

export const fmtNumberCL = (value: number, decimals = 2): string => {
  if (value === Math.floor(value) && decimals <= 0) return value.toString()
  return value.toFixed(decimals).replace('.', ',')
}

export const homoClass = (estado: string): string => {
  switch (estado) {
    case 'homologado':
      return 'homo-ok'
    case 'manual':
    case 'asignado_auto':
      return 'homo-manual'
    case 'sugerido':
      return 'homo-ok'
    case 'pendiente':
      return 'homo-pending'
    default:
      return 'homo-missing'
  }
}

export const homoRowBg = (estado: string): string => {
  switch (estado) {
    case 'homologado':
      return 'bg-emerald-950/30'
    case 'sugerido':
      return 'bg-teal-950/25'
    case 'sin_homologacion':
      return 'bg-red-950/35'
    case 'pendiente':
      return 'bg-amber-950/25'
    case 'manual':
    case 'asignado_auto':
      return 'bg-blue-950/25'
    default:
      return ''
  }
}

export const homoBadge = (estado: string): { label: string; color: string } => {
  switch (estado) {
    case 'homologado':
      return { label: 'OK', color: 'text-emerald-400' }
    case 'sugerido':
      return { label: 'Sugerido', color: 'text-teal-400' }
    case 'sin_homologacion':
      return { label: 'Sin homo', color: 'text-red-400' }
    case 'pendiente':
      return { label: 'Pendiente', color: 'text-amber-400' }
    case 'manual':
      return { label: 'Manual', color: 'text-blue-400' }
    case 'asignado_auto':
      return { label: 'Auto', color: 'text-blue-400' }
    default:
      return { label: 'Desconocido', color: 'text-gray-500' }
  }
}

export const estadoBadgeClass = (estado: string): string => {
  switch (estado?.toLowerCase()) {
    case 'pendiente':
      return 'badge-proceso'
    case 'nueva':
      return 'badge-nueva'
    case 'revisada':
      return 'badge-proceso'
    case 'lista para sap':
      return 'badge-proceso'
    case 'ingresada':
      return 'badge-ingresada'
    case 'con error':
      return 'badge-alert'
    default:
      return 'badge-proceso'
  }
}

export const estadoInternoBgClass = (estado: string): string => {
  switch (estado?.toLowerCase()) {
    case 'pendiente':
      return 'bg-amber-500/15 text-amber-300 border border-amber-500/25'
    case 'nueva':
      return 'bg-blue-500/15 text-blue-300 border border-blue-500/25'
    case 'revisada':
      return 'bg-violet-500/15 text-violet-300 border border-violet-500/25'
    case 'lista para sap':
      return 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/25'
    case 'ingresada':
      return 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/25'
    case 'con error':
      return 'bg-red-500/15 text-red-300 border border-red-500/25'
    default:
      return 'bg-gray-500/15 text-gray-300 border border-gray-500/25'
  }
}

export const ESTADOS_INTERNOS = [
  'Pendiente',
  'Nueva',
  'Revisada',
  'Lista para SAP',
  'Ingresada',
  'Con error',
] as const
