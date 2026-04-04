import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { format, subDays } from 'date-fns'
import { BarChart3, BrainCircuit, Check, ChevronDown, ExternalLink, Search, Sparkles, Wand2 } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { searchMaestra } from '../../api/catalogs'
import { asignarItemcode, getAnalytics, getSugerencias, limpiarAsignacion } from '../../api/ocs'
import type { AnalyticsResponse, ReviewQueueItem, Sugerencia } from '../../types/oc'
import { estadoInternoBgClass, fmtDate, fmtMoney, homoBadge } from '../../utils/formatters'

const today = () => format(new Date(), 'yyyy-MM-dd')
const ago = (days: number) => format(subDays(new Date(), days), 'yyyy-MM-dd')
const QUEUE_LIMIT = 220

type QueueMode = 'todos' | 'pendientes' | 'con_sugerencia' | 'manuales' | 'sin_sugerencia'
type ActiveRange = 'hoy' | '7d' | '30d' | null
type AssignOrigin = 'sugerencia' | 'manual'
type AssignPayload = { origin: AssignOrigin; code: string; desc: string }

export default function StatisticsPage() {
  const qc = useQueryClient()
  const [fechaDesde, setFechaDesde] = useState(today())
  const [fechaHasta, setFechaHasta] = useState(today())
  const [activeRange, setActiveRange] = useState<ActiveRange>('hoy')
  const [queueMode, setQueueMode] = useState<QueueMode>('pendientes')
  const [search, setSearch] = useState('')
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  const [solvedThisSession, setSolvedThisSession] = useState(0)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['ocs-analytics', fechaDesde, fechaHasta],
    queryFn: () => getAnalytics({ fecha_desde: fechaDesde, fecha_hasta: fechaHasta, limit: QUEUE_LIMIT }),
    staleTime: 30_000,
  })

  const filteredQueue = useMemo(() => {
    const queue = data?.queue ?? []
    const normalizedSearch = search.trim().toLowerCase()

    return queue.filter((item) => {
      const isPending = item.estado_homologacion === 'pendiente' || !item.itemcode_sap

      if (queueMode === 'pendientes' && !isPending) return false
      if (queueMode === 'con_sugerencia' && (!isPending || !item.sugerencia_principal)) return false
      if (queueMode === 'manuales' && item.estado_homologacion !== 'manual') return false
      if (queueMode === 'sin_sugerencia' && (!isPending || item.sugerencia_principal)) return false

      if (!normalizedSearch) return true

      const haystack = [
        item.codigo_oc,
        item.nombre_organismo,
        item.cliente_sap_sugerido,
        item.itemcode_sap ?? '',
        item.descripcion_sap ?? '',
        item.producto,
        item.especificacion_comprador,
        item.sugerencia_principal?.itemcode_sap ?? '',
        item.sugerencia_principal?.descripcion_sap ?? '',
      ]
        .join(' ')
        .toLowerCase()

      return haystack.includes(normalizedSearch)
    })
  }, [data?.queue, queueMode, search])

  useEffect(() => {
    if (!filteredQueue.length) {
      setExpandedKey(null)
      return
    }
    if (!expandedKey) {
      setExpandedKey(`${filteredQueue[0].codigo_oc}-${filteredQueue[0].correlativo}`)
      return
    }
    const stillVisible = filteredQueue.some((item) => `${item.codigo_oc}-${item.correlativo}` === expandedKey)
    if (!stillVisible) {
      setExpandedKey(`${filteredQueue[0].codigo_oc}-${filteredQueue[0].correlativo}`)
    }
  }, [expandedKey, filteredQueue])

  const summary = data?.summary

  // Optimistic: remove item + update summary immediately. Defer full refetch.
  const handleAssigned = (rowKey: string, assignment: AssignPayload) => {
    setSolvedThisSession((n) => n + 1)
    qc.setQueriesData<AnalyticsResponse>({ queryKey: ['ocs-analytics'] }, (old) => {
      if (!old) return old
      const currentItem = old.queue.find((q) => `${q.codigo_oc}-${q.correlativo}` === rowKey)
      if (!currentItem) return old

      const prevState = currentItem.estado_homologacion || 'pendiente'
      const wasPending = prevState === 'pendiente' || !currentItem.itemcode_sap
      const hadSugerencia = currentItem.sugerencia_principal != null
      const newResueltas = old.summary.lineas_resueltas + (wasPending ? 1 : 0)
      const newPendientes = Math.max(0, old.summary.lineas_pendientes - (wasPending ? 1 : 0))
      const newManuales = Math.max(
        0,
        old.summary.lineas_manuales - (prevState === 'manual' ? 1 : 0) + (assignment.origin === 'manual' ? 1 : 0),
      )
      const newSugeridas = Math.max(
        0,
        old.summary.lineas_sugeridas - (prevState === 'sugerido' ? 1 : 0) + (assignment.origin === 'sugerencia' ? 1 : 0),
      )
      const newQueue =
        assignment.origin === 'sugerencia'
          ? old.queue.filter((q) => `${q.codigo_oc}-${q.correlativo}` !== rowKey)
          : old.queue.map((q) =>
              `${q.codigo_oc}-${q.correlativo}` === rowKey
                ? {
                    ...q,
                    itemcode_sap: assignment.code,
                    descripcion_sap: assignment.desc,
                    estado_homologacion: 'manual',
                  }
                : q,
            )
      const queueDelta = assignment.origin === 'sugerencia' ? 1 : 0
      return {
        ...old,
        queue: newQueue,
        summary: {
          ...old.summary,
          lineas_resueltas: newResueltas,
          lineas_pendientes: newPendientes,
          lineas_manuales: newManuales,
          lineas_sugeridas: newSugeridas,
          cola_revision: Math.max(0, old.summary.cola_revision - queueDelta),
          total_cola_sin_limite: Math.max(0, old.summary.total_cola_sin_limite - queueDelta),
          pendientes_con_sugerencia: wasPending && hadSugerencia
            ? Math.max(0, old.summary.pendientes_con_sugerencia - 1)
            : old.summary.pendientes_con_sugerencia,
          pendientes_sin_sugerencia: wasPending && !hadSugerencia
            ? Math.max(0, old.summary.pendientes_sin_sugerencia - 1)
            : old.summary.pendientes_sin_sugerencia,
          cobertura_lineas_pct: old.summary.total_lineas > 0
            ? Math.round((newResueltas / old.summary.total_lineas) * 1000) / 10
            : 0,
        },
      }
    })
    // Mark ocs list stale (for when user navigates there)
    qc.invalidateQueries({ queryKey: ['ocs'] })
    // NO immediate invalidation of ocs-analytics — staleTime handles eventual consistency
  }

  const totalCola = summary?.total_cola_sin_limite ?? 0
  const queueTruncated = (data?.queue.length ?? 0) >= QUEUE_LIMIT && totalCola > QUEUE_LIMIT

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Estadisticas y revision</h1>
          <p className="text-xs text-gray-600">
            Cobertura automatica, cola de pendientes y correccion inline sin salir de la pantalla.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <QuickRangeButton
            label="Hoy"
            active={activeRange === 'hoy'}
            onClick={() => {
              setFechaDesde(today())
              setFechaHasta(today())
              setActiveRange('hoy')
            }}
          />
          <QuickRangeButton
            label="7 dias"
            active={activeRange === '7d'}
            onClick={() => {
              setFechaDesde(ago(7))
              setFechaHasta(today())
              setActiveRange('7d')
            }}
          />
          <QuickRangeButton
            label="30 dias"
            active={activeRange === '30d'}
            onClick={() => {
              setFechaDesde(ago(30))
              setFechaHasta(today())
              setActiveRange('30d')
            }}
          />
        </div>
      </div>

      <section className="card">
        <div className="card-header">
          <BarChart3 size={15} className="text-accent" />
          Ventana analizada
        </div>
        <div className="card-body space-y-3">
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_1fr_auto]">
            <label className="block">
              <span className="label">Fecha desde</span>
              <input
                type="date"
                className="input"
                value={fechaDesde}
                onChange={(event) => {
                  setFechaDesde(event.target.value)
                  setActiveRange(null)
                }}
              />
            </label>
            <label className="block">
              <span className="label">Fecha hasta</span>
              <input
                type="date"
                className="input"
                value={fechaHasta}
                onChange={(event) => {
                  setFechaHasta(event.target.value)
                  setActiveRange(null)
                }}
              />
            </label>
            <div className="flex items-end">
              <div className="rounded-xl border border-gray-800 bg-gray-950/60 px-4 py-3 text-sm text-gray-400">
                {isFetching ? 'Actualizando metricas...' : 'La cola de abajo permite corregir directo en la misma tabla.'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              icon={<BarChart3 size={16} />}
              label="Total OCs"
              value={summary?.total_ocs ?? 0}
              helper={`${summary?.total_lineas ?? 0} lineas analizadas`}
            />
            <MetricCard
              icon={<Sparkles size={16} />}
              label="Cobertura por lineas"
              value={`${summary?.cobertura_lineas_pct ?? 0}%`}
              helper={`${summary?.lineas_resueltas ?? 0} resueltas`}
              tone="emerald"
            />
            <MetricCard
              icon={<BrainCircuit size={16} />}
              label="Pendientes con sugerencia"
              value={summary?.pendientes_con_sugerencia ?? 0}
              helper="Clic para filtrar"
              tone="blue"
              onClick={() => setQueueMode('con_sugerencia')}
            />
            <MetricCard
              icon={<Wand2 size={16} />}
              label="Pendientes sin sugerencia"
              value={summary?.pendientes_sin_sugerencia ?? 0}
              helper="Clic para filtrar"
              tone="amber"
              onClick={() => setQueueMode('sin_sugerencia')}
            />
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <MetricStrip
              label="Monto cubierto"
              value={fmtMoney(summary?.monto_resuelto ?? 0)}
              helper={`${summary?.cobertura_monto_pct ?? 0}% del monto`}
            />
            <MetricStrip
              label="Lineas pendientes"
              value={(summary?.lineas_pendientes ?? 0).toLocaleString('es-CL')}
              helper="Sin itemcode final"
            />
            <MetricStrip
              label="Revisadas manualmente"
              value={(summary?.lineas_manuales ?? 0).toLocaleString('es-CL')}
              helper="Asignadas por un humano"
            />
            <MetricStrip
              label="OCs por revisar"
              value={(summary?.ocs_por_revisar ?? 0).toLocaleString('es-CL')}
              helper={`${summary?.cola_revision ?? 0} lineas en cola`}
            />
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-header flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Sparkles size={15} className="text-accent" />
            Cola de sugerencias y correcciones
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            {isLoading ? 'Cargando...' : `${filteredQueue.length} linea(s) visibles`}
            {solvedThisSession > 0 && (
              <span className="font-medium text-emerald-400">{solvedThisSession} resuelta(s) esta sesion</span>
            )}
          </div>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.1fr_auto]">
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3 top-3 text-gray-500" />
              <input
                className="input pl-9"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por OC, comprador, itemcode o descripcion..."
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <QueueModeButton label="Pendientes" active={queueMode === 'pendientes'} onClick={() => setQueueMode('pendientes')} />
              <QueueModeButton label="Con sugerencia" active={queueMode === 'con_sugerencia'} onClick={() => setQueueMode('con_sugerencia')} />
              <QueueModeButton label="Sin sugerencia" active={queueMode === 'sin_sugerencia'} onClick={() => setQueueMode('sin_sugerencia')} />
              <QueueModeButton label="Revisadas" active={queueMode === 'manuales'} onClick={() => setQueueMode('manuales')} />
              <QueueModeButton label="Todos" active={queueMode === 'todos'} onClick={() => setQueueMode('todos')} />
            </div>
          </div>

          {queueTruncated && (
            <div className="rounded-xl border border-amber-800/40 bg-amber-950/15 px-4 py-2.5 text-xs text-amber-200">
              Mostrando {QUEUE_LIMIT} de {totalCola} lineas en cola. Ajusta el rango de fechas para trabajar el resto.
            </div>
          )}

          <div className="rounded-2xl border border-gray-800 bg-gray-950/60">
            <div className="max-h-[70vh] overflow-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th className="w-12"></th>
                    <th>OC</th>
                    <th>Comprador</th>
                    <th>Detalle linea</th>
                    <th>Sugerencia / asignacion</th>
                    <th>Estado</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredQueue.map((item) => {
                    const rowKey = `${item.codigo_oc}-${item.correlativo}`
                    const expanded = expandedKey === rowKey
                    return (
                      <ExpertQueueRow
                        key={rowKey}
                        item={item}
                        expanded={expanded}
                        onToggle={() => setExpandedKey((current) => (current === rowKey ? null : rowKey))}
                        onAssigned={(assignment) => handleAssigned(rowKey, assignment)}
                      />
                    )
                  })}

                  {!isLoading && filteredQueue.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                        No hay lineas para esta vista. Prueba otro rango o cambia el filtro de revision.
                      </td>
                    </tr>
                  )}

                  {isLoading && (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                        Cargando estadisticas y cola de trabajo...
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

function ExpertQueueRow({
  item,
  expanded,
  onToggle,
  onAssigned,
}: {
  item: ReviewQueueItem
  expanded: boolean
  onToggle: () => void
  onAssigned: (assignment: AssignPayload) => void
}) {
  const qc = useQueryClient()
  const estadoLinea = homoBadge(item.estado_homologacion)
  const isPending = item.estado_homologacion === 'pendiente' || !item.itemcode_sap
  const sugerencia = item.sugerencia_principal

  const acceptMutation = useMutation({
    mutationFn: () =>
      asignarItemcode(
        item.codigo_oc,
        item.correlativo,
        sugerencia!.itemcode_sap,
        sugerencia!.descripcion_sap,
        'sugerencia',
      ),
    onSuccess: () => {
      onAssigned({
        origin: 'sugerencia',
        code: sugerencia!.itemcode_sap,
        desc: sugerencia!.descripcion_sap,
      })
    },
  })

  return (
    <>
      <tr
        className={`${expanded ? 'bg-blue-950/15' : isPending ? 'bg-gray-950/10' : ''} cursor-pointer`}
        onClick={onToggle}
      >
        <td>
          <button
            type="button"
            className="rounded-full border border-gray-800 bg-gray-900/70 p-1.5 text-gray-400 transition-colors hover:text-gray-200"
            onClick={(event) => {
              event.stopPropagation()
              onToggle()
            }}
            aria-label={expanded ? 'Ocultar editor' : 'Mostrar editor'}
          >
            <ChevronDown size={14} className={`transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </button>
        </td>
        <td className="min-w-[150px]">
          <div className="space-y-1">
            <div className="font-medium text-gray-100">{item.codigo_oc}</div>
            <div className="text-xs text-gray-500">
              {fmtDate(item.fecha_envio)} | linea {item.correlativo} | {item.tipo_oc}
            </div>
          </div>
        </td>
        <td className="min-w-[160px] max-w-[200px] whitespace-normal">
          <div className="space-y-1">
            <div className="font-medium text-gray-100">{item.nombre_organismo}</div>
            <div className="text-xs text-gray-500">
              {item.cliente_sap_sugerido || 'Sin cliente SAP'}
              {item.cartera ? ` | ${item.cartera}` : ''}
            </div>
          </div>
        </td>
        <td className="min-w-[240px] max-w-[360px] whitespace-normal">
          <div className="space-y-1">
            <div className="text-sm text-gray-100">{item.especificacion_comprador || item.producto || 'Sin descripcion'}</div>
            {item.producto && item.especificacion_comprador && item.producto !== item.especificacion_comprador && (
              <div className="text-xs text-gray-500">{item.producto}</div>
            )}
          </div>
        </td>
        <td className="min-w-[220px] max-w-[280px] whitespace-normal">
          {sugerencia ? (
            <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/15 px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-medium text-emerald-200">{sugerencia.itemcode_sap}</div>
                  <div className="mt-0.5 text-sm leading-5 text-gray-200">{sugerencia.descripcion_sap}</div>
                  <div className="mt-1 text-xs text-emerald-300">
                    Match {Math.round(sugerencia.score * 100)}%
                  </div>
                </div>
                <button
                  type="button"
                  className="mt-0.5 flex shrink-0 items-center gap-1 rounded-lg border border-emerald-700/50 bg-emerald-900/40 px-2.5 py-1.5 text-xs font-medium text-emerald-200 transition-colors hover:bg-emerald-800/50 disabled:opacity-50"
                  disabled={acceptMutation.isPending}
                  onClick={(event) => {
                    event.stopPropagation()
                    acceptMutation.mutate()
                  }}
                  title={`Aceptar: ${sugerencia.itemcode_sap} — ${sugerencia.descripcion_sap}`}
                >
                  <Check size={12} />
                  Aceptar
                </button>
              </div>
            </div>
          ) : item.itemcode_sap ? (
            <div className="rounded-xl border border-blue-800/40 bg-blue-950/15 px-3 py-2">
              <div className="font-medium text-blue-200">{item.itemcode_sap}</div>
              <div className="mt-1 text-sm text-gray-200">{item.descripcion_sap || 'Asignado manualmente'}</div>
            </div>
          ) : (
            <div className="rounded-xl border border-amber-800/40 bg-amber-950/15 px-3 py-2 text-sm text-amber-200">
              Sin sugerencia automatica aun.
            </div>
          )}
        </td>
        <td className="min-w-[140px]">
          <div className="space-y-2">
            <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${estadoInternoBgClass(item.estado_interno)}`}>
              {item.estado_interno}
            </span>
            <div className={`text-xs font-medium ${estadoLinea.color}`}>{estadoLinea.label}</div>
          </div>
        </td>
        <td className="min-w-[100px] font-medium text-gray-100">{fmtMoney(item.total)}</td>
      </tr>

      {expanded && <InlineCorrectionRow item={item} onAssigned={onAssigned} />}
    </>
  )
}

function InlineCorrectionRow({
  item,
  onAssigned,
}: {
  item: ReviewQueueItem
  onAssigned: (assignment: AssignPayload) => void
}) {
  const qc = useQueryClient()
  const [manualCode, setManualCode] = useState(item.itemcode_sap ?? '')
  const [manualDesc, setManualDesc] = useState(item.descripcion_sap ?? '')
  const [showDropdown, setShowDropdown] = useState(false)
  const [message, setMessage] = useState('')
  const [codeVerified, setCodeVerified] = useState(false)

  const { data: sugerencias = [], isLoading: loadingSugerencias } = useQuery({
    queryKey: ['stats-sugerencias', item.codigo_oc, item.correlativo],
    queryFn: () => getSugerencias(item.codigo_oc, item.correlativo),
    staleTime: 300_000,
  })

  const { data: searchResults = [], isLoading: searchLoading } = useQuery({
    queryKey: ['stats-maestra-search', manualCode],
    queryFn: () => searchMaestra(manualCode),
    enabled: showDropdown && manualCode.trim().length >= 3,
    staleTime: 60_000,
  })

  useEffect(() => {
    setManualCode(item.itemcode_sap ?? '')
    setManualDesc(item.descripcion_sap ?? '')
    setCodeVerified(!!item.itemcode_sap)
  }, [item.descripcion_sap, item.itemcode_sap])

  const assignMutation = useMutation({
    mutationFn: async ({ code, desc, origen }: { code: string; desc: string; origen: 'sugerencia' | 'manual' }) => {
      await asignarItemcode(item.codigo_oc, item.correlativo, code, desc, origen)
    },
    onSuccess: (_data, variables) => {
      setMessage('Linea actualizada')
      onAssigned({
        origin: variables.origen,
        code: variables.code,
        desc: variables.desc,
      })
      setTimeout(() => setMessage(''), 2000)
    },
  })

  const clearMutation = useMutation({
    mutationFn: async () => {
      await limpiarAsignacion(item.codigo_oc, item.correlativo)
    },
    onSuccess: () => {
      setManualCode('')
      setManualDesc('')
      setCodeVerified(false)
      setMessage('Asignacion eliminada')
      qc.invalidateQueries({ queryKey: ['ocs-analytics'] })
      qc.invalidateQueries({ queryKey: ['ocs'] })
      setTimeout(() => setMessage(''), 2000)
    },
  })

  const applySuggestion = (suggestion: Sugerencia) => {
    setManualCode(suggestion.itemcode_sap)
    setManualDesc(suggestion.descripcion_sap)
    setCodeVerified(true)
    assignMutation.mutate({ code: suggestion.itemcode_sap, desc: suggestion.descripcion_sap, origen: 'sugerencia' })
  }

  const applySearchResult = (code: string, desc: string) => {
    setManualCode(code)
    setManualDesc(desc)
    setShowDropdown(false)
    setCodeVerified(true)
    assignMutation.mutate({ code, desc, origen: 'manual' })
  }

  const renderStars = (score: number) => {
    const stars = Math.max(1, Math.round(score * 5))
    return '★'.repeat(stars) + '☆'.repeat(5 - stars)
  }

  return (
    <tr className="bg-gray-900/80">
      <td colSpan={7} className="px-4 py-4">
        <div className="space-y-4">
          {/* Contexto compacto de la OC — sin repetir datos ya visibles en la fila */}
          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-800 bg-gray-950/60 px-4 py-3 text-sm">
            <div>
              <span className="text-xs text-gray-500">OC </span>
              <span className="font-medium text-gray-100">{item.codigo_oc}</span>
            </div>
            <div>
              <span className="text-xs text-gray-500">Estado </span>
              <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${estadoInternoBgClass(item.estado_interno)}`}>
                {item.estado_interno}
              </span>
            </div>
            {item.cartera && (
              <div>
                <span className="text-xs text-gray-500">Cartera </span>
                <span className="text-gray-300">{item.cartera}</span>
              </div>
            )}
            <div className="text-gray-300">
              <span className="text-xs text-gray-500">Cantidad </span>
              {item.cantidad}
            </div>
            <Link to={`/oc/${item.codigo_oc}`} className="btn-secondary ml-auto px-3 py-1.5 text-xs">
              <ExternalLink size={12} />
              Ver OC completa
            </Link>
          </div>

          {/* Sugerencias del motor */}
          <div className="rounded-2xl border border-gray-800 bg-gray-950/60 px-4 py-4">
            <div className="mb-3 text-sm font-medium text-gray-100">Sugerencias del motor</div>
            {loadingSugerencias ? (
              <div className="text-sm text-gray-500">Buscando sugerencias...</div>
            ) : sugerencias.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
                {sugerencias.slice(0, 5).map((suggestion) => (
                  <button
                    key={suggestion.itemcode_sap}
                    type="button"
                    className="rounded-2xl border border-blue-800/40 bg-blue-950/15 px-4 py-3 text-left transition-colors hover:bg-blue-950/25"
                    onClick={() => applySuggestion(suggestion)}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-mono text-sm text-blue-200">{suggestion.itemcode_sap}</span>
                      <span
                        className="text-xs tracking-wider text-amber-300"
                        title={`Score: ${Math.round(suggestion.score * 100)}%`}
                      >
                        {renderStars(suggestion.score)}
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-gray-100">{suggestion.descripcion_sap}</div>
                    <div className="mt-2 text-xs text-gray-500">
                      {suggestion.descripcion_match || 'Sin detalle'} · {suggestion.frecuencia} uso(s)
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-amber-800/40 bg-amber-950/15 px-3 py-3 text-sm text-amber-200">
                Esta linea aun no tiene sugerencias automaticas. Puedes buscar y asignar manualmente desde la maestra.
              </div>
            )}
          </div>

          {/* Corrección manual */}
          <div className="rounded-2xl border border-gray-800 bg-gray-950/60 px-4 py-4">
            <div className="mb-3 text-sm font-medium text-gray-100">Correccion manual</div>
            <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.2fr_1.2fr_auto]">
              <div className="relative">
                <input
                  className="input"
                  placeholder="Buscar o escribir itemcode en la maestra..."
                  value={manualCode}
                  onChange={(event) => {
                    setManualCode(event.target.value)
                    setCodeVerified(false)
                    setShowDropdown(true)
                  }}
                  onFocus={() => setShowDropdown(true)}
                  onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
                />

                {showDropdown && manualCode.trim().length >= 3 && (
                  <div className="absolute z-20 mt-2 max-h-60 w-full overflow-y-auto rounded-xl border border-gray-700 bg-gray-950 shadow-2xl">
                    {searchLoading ? (
                      <div className="px-3 py-2 text-sm text-gray-400">Buscando en maestra...</div>
                    ) : searchResults.length ? (
                      searchResults.map((result) => (
                        <button
                          key={result.itemcode_sap}
                          type="button"
                          className="flex w-full flex-col border-b border-gray-800 px-3 py-3 text-left transition-colors last:border-b-0 hover:bg-gray-900"
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => applySearchResult(result.itemcode_sap, result.descripcion_sap)}
                        >
                          <span className="font-mono text-sm text-blue-300">{result.itemcode_sap}</span>
                          <span className="text-sm text-gray-300">{result.descripcion_sap}</span>
                        </button>
                      ))
                    ) : (
                      <div className="px-3 py-2 text-sm text-gray-400">Sin resultados en la maestra.</div>
                    )}
                  </div>
                )}
              </div>

              <input
                className="input"
                placeholder="Descripcion SAP (opcional)"
                value={manualDesc}
                onChange={(event) => setManualDesc(event.target.value)}
              />

              <div className="flex gap-2">
                <button
                  className={codeVerified ? 'btn-primary' : 'btn-secondary'}
                  disabled={!manualCode.trim() || !codeVerified || assignMutation.isPending}
                  onClick={() => assignMutation.mutate({ code: manualCode.trim(), desc: manualDesc.trim(), origen: 'manual' })}
                  title={codeVerified ? undefined : 'Selecciona un itemcode desde la maestra antes de guardar'}
                >
                  {codeVerified ? 'Asignar' : 'Selecciona desde maestra'}
                </button>
                <button
                  className="btn-danger"
                  disabled={!item.itemcode_sap || clearMutation.isPending}
                  onClick={() => clearMutation.mutate()}
                >
                  Limpiar
                </button>
              </div>
            </div>

            {(assignMutation.isError || clearMutation.isError || message) && (
              <div className={`mt-3 text-sm ${assignMutation.isError || clearMutation.isError ? 'text-red-300' : 'text-emerald-300'}`}>
                {assignMutation.isError
                  ? (assignMutation.error as Error).message
                  : clearMutation.isError
                    ? (clearMutation.error as Error).message
                    : message}
              </div>
            )}
            {!codeVerified && manualCode.trim().length > 0 && (
              <div className="mt-3 text-xs text-amber-300">
                Escribe y selecciona un resultado de la maestra para habilitar el guardado.
              </div>
            )}
          </div>
        </div>
      </td>
    </tr>
  )
}

function MetricCard({
  icon,
  label,
  value,
  helper,
  tone = 'default',
  onClick,
}: {
  icon: ReactNode
  label: string
  value: number | string
  helper: string
  tone?: 'default' | 'emerald' | 'amber' | 'blue'
  onClick?: () => void
}) {
  const toneClass =
    tone === 'emerald'
      ? 'border-emerald-800/40 bg-emerald-950/15 text-emerald-200'
      : tone === 'amber'
        ? 'border-amber-800/40 bg-amber-950/15 text-amber-200'
        : tone === 'blue'
          ? 'border-blue-800/40 bg-blue-950/15 text-blue-200'
          : 'border-gray-800 bg-gray-950/60 text-gray-200'

  return (
    <div
      className={`rounded-2xl border px-4 py-3 ${toneClass} ${onClick ? 'cursor-pointer transition-opacity hover:opacity-75' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {label}
      </div>
      <div className="mt-2 text-xl font-semibold tracking-tight">{value}</div>
      <div className="mt-1 text-xs text-gray-400">{helper}</div>
    </div>
  )
}

function MetricStrip({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-950/55 px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.12em] text-gray-500">{label}</div>
      <div className="mt-2 text-lg font-semibold text-gray-100">{value}</div>
      <div className="mt-1 text-xs text-gray-500">{helper}</div>
    </div>
  )
}

function QueueModeButton({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
        active
          ? 'border-accent text-accent'
          : 'border-gray-800 bg-gray-950/70 text-gray-400 hover:border-gray-700 hover:text-gray-200'
      }`}
      onClick={onClick}
      style={active ? { backgroundColor: 'rgba(var(--accent-500), 0.12)' } : undefined}
    >
      {label}
    </button>
  )
}

function QuickRangeButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
        active
          ? 'border-accent text-accent'
          : 'border-gray-800 bg-gray-950/70 text-gray-400 hover:border-gray-700 hover:text-gray-200'
      }`}
      onClick={onClick}
      style={active ? { backgroundColor: 'rgba(var(--accent-500), 0.12)' } : undefined}
    >
      {label}
    </button>
  )
}
