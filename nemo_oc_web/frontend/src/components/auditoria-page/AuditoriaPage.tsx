import { useEffect, useState } from 'react'
import { format, subDays } from 'date-fns'
import { AlertTriangle, CheckCircle2, ExternalLink, FileDown, RefreshCw, ShieldAlert } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getAuditoria, marcarIngresada, exportAll } from '../../api/ocs'
import type { OcAuditoriaItem } from '../../types/oc'
import { fmtDate, fmtMoney } from '../../utils/formatters'
import api from '../../api/client'

const today = () => format(new Date(), 'yyyy-MM-dd')
const ago = (days: number) => format(subDays(new Date(), days), 'yyyy-MM-dd')

type Tab = 'aceptadas' | 'ingresadas'
type ActiveRange = 'hoy' | '7d' | '30d' | null

function EstadoMpBadge({ estado }: { estado: string }) {
  const lower = estado.toLowerCase()
  let cls = 'rounded px-2 py-0.5 text-xs font-medium '
  if (lower === 'aceptada') cls += 'bg-emerald-900/40 text-emerald-400'
  else if (lower.includes('recepci')) cls += 'bg-blue-900/40 text-blue-400'
  else if (lower === 'cancelada') cls += 'bg-red-900/40 text-red-400'
  else cls += 'bg-gray-800 text-gray-400'
  return <span className={cls}>{estado}</span>
}

function EstadoInternoBadge({ estado }: { estado: string }) {
  const lower = estado.toLowerCase()
  let cls = 'rounded px-2 py-0.5 text-xs font-medium '
  if (lower === 'ingresada') cls += 'bg-emerald-900/40 text-emerald-400'
  else if (lower === 'nueva') cls += 'bg-yellow-900/40 text-yellow-400'
  else if (lower === 'con error') cls += 'bg-red-900/40 text-red-400'
  else cls += 'bg-gray-800 text-gray-400'
  return <span className={cls}>{estado}</span>
}

function OcTable({
  items,
  showMarcarIngresada,
  onMarcarIngresada,
  pendingCodes,
}: {
  items: OcAuditoriaItem[]
  showMarcarIngresada: boolean
  onMarcarIngresada: (codigo: string) => void
  pendingCodes: Set<string>
}) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-gray-500">
        <CheckCircle2 size={32} className="text-emerald-500/60" />
        <p className="text-sm">No hay discrepancias en este rango de fechas.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
            <th className="pb-3 pr-4">Código OC</th>
            <th className="pb-3 pr-4">Tipo</th>
            <th className="pb-3 pr-4">Organismo</th>
            <th className="pb-3 pr-4">Estado Portal</th>
            <th className="pb-3 pr-4">Estado Interno</th>
            <th className="pb-3 pr-4">Fecha Envío</th>
            <th className="pb-3 pr-4 text-right">Total Neto</th>
            <th className="pb-3 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800/60">
          {items.map((oc) => (
            <tr key={oc.codigo_oc} className="group hover:bg-gray-900/40">
              <td className="py-3 pr-4 font-mono text-xs text-gray-300">{oc.codigo_oc}</td>
              <td className="py-3 pr-4 text-gray-400">{oc.tipo_oc}</td>
              <td className="py-3 pr-4 max-w-[200px] truncate text-gray-300" title={oc.nombre_organismo}>
                {oc.nombre_organismo}
              </td>
              <td className="py-3 pr-4">
                <EstadoMpBadge estado={oc.estado_mp} />
              </td>
              <td className="py-3 pr-4">
                <EstadoInternoBadge estado={oc.estado_interno} />
              </td>
              <td className="py-3 pr-4 text-gray-400">{fmtDate(oc.fecha_envio)}</td>
              <td className="py-3 pr-4 text-right font-mono text-gray-300">
                {fmtMoney(oc.total_neto, oc.moneda)}
              </td>
              <td className="py-3 text-right">
                <div className="flex items-center justify-end gap-2">
                  {showMarcarIngresada && (
                    <button
                      className="btn-primary py-1 px-2 text-xs"
                      disabled={pendingCodes.has(oc.codigo_oc)}
                      onClick={() => onMarcarIngresada(oc.codigo_oc)}
                      title="Marcar como Ingresada en SAP"
                    >
                      {pendingCodes.has(oc.codigo_oc) ? (
                        <RefreshCw size={12} className="animate-spin" />
                      ) : (
                        <CheckCircle2 size={12} />
                      )}
                      <span className="ml-1">Ingresada</span>
                    </button>
                  )}
                  <Link
                    to={`/oc/${oc.codigo_oc}`}
                    className="btn-secondary py-1 px-2 text-xs"
                    title="Ver detalle"
                  >
                    <ExternalLink size={12} />
                    <span className="ml-1">Detalle</span>
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function AuditoriaPage() {
  const qc = useQueryClient()
  const [fechaDesde, setFechaDesde] = useState(ago(30))
  const [fechaHasta, setFechaHasta] = useState(today())
  const [activeRange, setActiveRange] = useState<ActiveRange>('30d')
  const [activeTab, setActiveTab] = useState<Tab>('aceptadas')
  const [pendingCodes, setPendingCodes] = useState<Set<string>>(new Set())
  const [syncNotification, setSyncNotification] = useState<string | null>(null)

  // Hook para escuchar eventos de sync completo via SSE
  useEffect(() => {
    const eventSource = new EventSource('/api/sync/status')

    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        // Cuando un sync ligero termina, refrescar tabla
        if (event.type === 'message' && data?.next_light_sync) {
          qc.invalidateQueries({ queryKey: ['auditoria'] })
          setSyncNotification('✓ Estados actualizados desde Mercado Público')
          setTimeout(() => setSyncNotification(null), 4000)
        }
      } catch {
        // ignore parse errors
      }
    }

    const handleStatusCheck = setInterval(() => {
      // Polling simple cada 2 minutos para verificar si hubo cambios
      api.get<{ running: boolean }>('/sync/status').then((r) => {
        if (!r.data.running) {
          qc.invalidateQueries({ queryKey: ['auditoria'] })
        }
      }).catch(() => {
        // ignore errors
      })
    }, 120_000)

    eventSource.addEventListener('message', handleMessage)

    return () => {
      eventSource.close()
      clearInterval(handleStatusCheck)
    }
  }, [qc])

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['auditoria', fechaDesde, fechaHasta],
    queryFn: () => getAuditoria({ fecha_desde: fechaDesde, fecha_hasta: fechaHasta }),
    staleTime: 30_000,
  })

  const ingresarMutation = useMutation({
    mutationFn: (codigo: string) => marcarIngresada(codigo),
    onMutate: (codigo) => {
      setPendingCodes((prev) => new Set(prev).add(codigo))
    },
    onSettled: (_, __, codigo) => {
      setPendingCodes((prev) => {
        const next = new Set(prev)
        next.delete(codigo)
        return next
      })
      qc.invalidateQueries({ queryKey: ['auditoria'] })
    },
  })

  function setRange(range: ActiveRange) {
    setActiveRange(range)
    const t = today()
    if (range === 'hoy') { setFechaDesde(t); setFechaHasta(t) }
    else if (range === '7d') { setFechaDesde(ago(7)); setFechaHasta(t) }
    else if (range === '30d') { setFechaDesde(ago(30)); setFechaHasta(t) }
  }

  const aceptadas = data?.aceptadas_sin_ingresar ?? []
  const ingresadas = data?.ingresadas_sin_aceptar ?? []
  const totalDiscrepancias = aceptadas.length + ingresadas.length

  function handleExport() {
    if (activeTab === 'aceptadas') {
      exportAll({ estado_mp: ['Aceptada'], fecha_desde: fechaDesde, fecha_hasta: fechaHasta })
    } else {
      exportAll({ estado: ['Ingresada'], fecha_desde: fechaDesde, fecha_hasta: fechaHasta })
    }
  }

  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      {syncNotification && (
        <div className="rounded-lg border border-emerald-800 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-300">
          {syncNotification}
        </div>
      )}
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-orange-500/10 p-3">
            <ShieldAlert size={22} className="text-orange-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-100">Auditoría de Estados</h1>
            <p className="text-sm text-gray-500">
              Detecta discrepancias entre el estado del portal y el estado interno
            </p>
          </div>
        </div>

        <button className="btn-secondary" onClick={handleExport} title="Exportar tabla activa a Excel">
          <FileDown size={15} />
          Exportar
        </button>
      </div>

      {/* Filtros de fecha */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Rango</span>

        {(['hoy', '7d', '30d'] as ActiveRange[]).map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              activeRange === r
                ? 'border-accent bg-accent/10 text-accent'
                : 'border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200'
            }`}
          >
            {r === 'hoy' ? 'Hoy' : r === '7d' ? 'Últimos 7 días' : 'Últimos 30 días'}
          </button>
        ))}

        <div className="flex items-center gap-2 ml-2">
          <input
            type="date"
            value={fechaDesde}
            onChange={(e) => { setFechaDesde(e.target.value); setActiveRange(null) }}
            className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-accent"
          />
          <span className="text-xs text-gray-500">—</span>
          <input
            type="date"
            value={fechaHasta}
            onChange={(e) => { setFechaHasta(e.target.value); setActiveRange(null) }}
            className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-accent"
          />
        </div>

        {isFetching && <RefreshCw size={13} className="ml-1 animate-spin text-gray-500" />}
      </div>

      {/* Resumen */}
      {!isLoading && data && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-red-900/40 bg-red-950/20 px-4 py-4">
            <div className="text-2xl font-bold text-red-400">{aceptadas.length}</div>
            <div className="mt-1 text-xs text-gray-400">Aceptadas en portal sin ingresar</div>
          </div>
          <div className="rounded-xl border border-yellow-900/40 bg-yellow-950/20 px-4 py-4">
            <div className="text-2xl font-bold text-yellow-400">{ingresadas.length}</div>
            <div className="mt-1 text-xs text-gray-400">Ingresadas en SAP sin aceptar en portal</div>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-4">
            <div className={`text-2xl font-bold ${totalDiscrepancias > 0 ? 'text-orange-400' : 'text-emerald-400'}`}>
              {totalDiscrepancias}
            </div>
            <div className="mt-1 text-xs text-gray-400">Total discrepancias</div>
          </div>
        </div>
      )}

      {/* Tabs + Tabla */}
      <div className="flex-1 rounded-xl border border-gray-800 bg-gray-900/40">
        {/* Tab header */}
        <div className="flex border-b border-gray-800">
          <button
            onClick={() => setActiveTab('aceptadas')}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors ${
              activeTab === 'aceptadas'
                ? 'border-b-2 border-red-500 text-red-400'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <AlertTriangle size={14} />
            Aceptadas sin ingresar
            {!isLoading && (
              <span className="rounded-full bg-red-900/40 px-2 py-0.5 text-xs text-red-400">
                {aceptadas.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('ingresadas')}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors ${
              activeTab === 'ingresadas'
                ? 'border-b-2 border-yellow-500 text-yellow-400'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <AlertTriangle size={14} />
            Ingresadas sin aceptar en portal
            {!isLoading && (
              <span className="rounded-full bg-yellow-900/40 px-2 py-0.5 text-xs text-yellow-400">
                {ingresadas.length}
              </span>
            )}
          </button>
        </div>

        {/* Contenido */}
        <div className="p-5">
          {isLoading ? (
            <div className="flex items-center justify-center gap-3 py-16 text-gray-500">
              <RefreshCw size={18} className="animate-spin" />
              <span className="text-sm">Consultando discrepancias...</span>
            </div>
          ) : activeTab === 'aceptadas' ? (
            <>
              <p className="mb-4 text-xs text-gray-500">
                Estas OCs tienen estado <strong className="text-gray-300">"Aceptada"</strong> en el portal Mercado Público
                pero aún no están marcadas como <strong className="text-gray-300">"Ingresada"</strong> en nuestro sistema.
              </p>
              <OcTable
                items={aceptadas}
                showMarcarIngresada={true}
                onMarcarIngresada={(codigo) => ingresarMutation.mutate(codigo)}
                pendingCodes={pendingCodes}
              />
            </>
          ) : (
            <>
              <p className="mb-4 text-xs text-gray-500">
                Estas OCs están marcadas como <strong className="text-gray-300">"Ingresada"</strong> en nuestro sistema
                pero el portal Mercado Público no las muestra como <strong className="text-gray-300">"Aceptada"</strong>.
              </p>
              <OcTable
                items={ingresadas}
                showMarcarIngresada={false}
                onMarcarIngresada={() => {}}
                pendingCodes={pendingCodes}
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
