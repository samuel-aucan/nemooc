import { useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react'
import { format } from 'date-fns'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Download,
  FilterX,
  RefreshCw,
  Search,
  Settings2,
} from 'lucide-react'

import { getConfig } from '../../api/config'
import { exportAll, getFiltros, getOcs, importarOcMp, type OcFilters } from '../../api/ocs'
import { getSyncStatus } from '../../api/sync'
import { storage } from '../../utils/storage'
import { ESTADOS_INTERNOS, displayOcCode, estadoInternoBgClass, fmtDate, fmtMoney, normalizePublicOcCode } from '../../utils/formatters'
import type { OrdenCompra } from '../../types/oc'
import { copyText, hasSelectedText } from '../../utils/clipboard'
import MultiSelect from '../common/MultiSelect'
import OcDetailPanel from '../oc-detail/OcDetailPanel'
import OcListColumnConfigModal, {
  DEFAULT_OC_LIST_COLUMNS,
  OC_LIST_COLUMNS_AVAILABLE,
  normalizeOcListColumns,
  type OcListColumnId,
} from './OcListColumnConfigModal'

const TIPO_CM = ['CM']
const TOP_SECTION_STORAGE_KEY = 'oc-list-top-section-height'
const COL_WIDTHS_KEY = 'oc-list-col-widths'
const DEFAULT_TOP_SECTION_HEIGHT = 330
const MIN_TOP_SECTION_HEIGHT = 220
const MIN_DETAIL_SECTION_HEIGHT = 240

const DEFAULT_COL_WIDTHS: Record<OcListColumnId, number> = {
  codigo_oc: 130,
  tipo_oc: 75,
  holding: 140,
  estado_mp: 130,
  estado_interno: 120,
  fecha_envio: 105,
  fecha_ingreso: 105,
  nombre_organismo: 260,
  cliente_sap_sugerido: 140,
  responsable_ingreso_username: 140,
  ingresado_por_username: 140,
  ingreso_sap_acuerdo_global: 110,
  cartera: 110,
  vendedor: 130,
  total: 120,
  cantidad_lineas: 75,
}

const MIN_COL_WIDTH = 60

function buildColWidths(saved?: Record<string, number> | null) {
  const merged: Record<string, number> = {}
  for (const [columnId, defaultWidth] of Object.entries(DEFAULT_COL_WIDTHS)) {
    const savedWidth = saved?.[columnId]
    merged[columnId] = typeof savedWidth === 'number' && Number.isFinite(savedWidth)
      ? Math.max(MIN_COL_WIDTH, savedWidth)
      : defaultWidth
  }
  return merged
}

function isCm(tipo: string) {
  return TIPO_CM.includes(tipo?.toUpperCase())
}

const today = () => format(new Date(), 'yyyy-MM-dd')

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}


export default function OcListPage() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const rootRef = useRef<HTMLDivElement | null>(null)
  const resizeRef = useRef<{ startY: number; startHeight: number } | null>(null)
  const colResizeRef = useRef<{ colId: string; startX: number; startWidth: number } | null>(null)
  const lastSeenMpSyncRef = useRef<string | null>(null)
  const autoImportTriedRef = useRef<string | null>(null)

  const [colWidths, setColWidths] = useState<Record<string, number>>(() => {
    try {
      const saved = storage.getItem(COL_WIDTHS_KEY)
      return saved ? buildColWidths(JSON.parse(saved)) : buildColWidths()
    } catch {
      return buildColWidths()
    }
  })
  const [filters, setFilters] = useState<OcFilters>({})
  const [draft, setDraft] = useState<OcFilters>({})
  const [selectedCodigo, setSelectedCodigo] = useState<string | null>(null)
  const [soloHoy, setSoloHoy] = useState(false)
  const [showColumnConfig, setShowColumnConfig] = useState(false)
  const [topSectionHeight, setTopSectionHeight] = useState(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_TOP_SECTION_HEIGHT
    }

    const saved = Number(storage.getItem(TOP_SECTION_STORAGE_KEY))
    return Number.isFinite(saved) && saved > 0 ? saved : DEFAULT_TOP_SECTION_HEIGHT
  })

  const urlFilters = useMemo<OcFilters>(() => {
    const multi = (key: string) => searchParams.getAll(key).filter(Boolean)
    return {
      estado: multi('estado'),
      estado_mp: multi('estado_mp'),
      tipo_oc: multi('tipo_oc'),
      cartera: multi('cartera'),
      holding: multi('holding'),
      responsable: multi('responsable'),
      fecha_desde: searchParams.get('fecha_desde') || undefined,
      fecha_hasta: searchParams.get('fecha_hasta') || undefined,
      fecha_ingreso_desde: searchParams.get('fecha_ingreso_desde') || undefined,
      fecha_ingreso_hasta: searchParams.get('fecha_ingreso_hasta') || undefined,
      busqueda: searchParams.get('busqueda') || undefined,
    }
  }, [searchParams])

  const { data: ocs = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['ocs', filters],
    queryFn: () => getOcs(filters),
  })

  const { data: filtros } = useQuery({
    queryKey: ['filtros'],
    queryFn: getFiltros,
  })

  const { data: appConfig } = useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
  })

  const { data: syncStatus } = useQuery({
    queryKey: ['sync-status'],
    queryFn: getSyncStatus,
    refetchInterval: 5000,
  })

  useEffect(() => {
    const hasUrlFilters = Array.from(searchParams.keys()).length > 0
    if (!hasUrlFilters) return
    setDraft(urlFilters)
    setFilters(urlFilters)
    setSoloHoy(urlFilters.fecha_desde === today() && urlFilters.fecha_hasta === today())
  }, [searchParams, urlFilters])

  useEffect(() => {
    if (selectedCodigo && !ocs.some((oc) => oc.codigo_oc === selectedCodigo)) {
      setSelectedCodigo(null)
    }
  }, [ocs, selectedCodigo])

  useEffect(() => {
    const marker = syncStatus?.last_mp_sync_at ?? null
    if (!marker) return

    if (lastSeenMpSyncRef.current === null) {
      lastSeenMpSyncRef.current = marker
      return
    }

    if (marker === lastSeenMpSyncRef.current) return

    lastSeenMpSyncRef.current = marker
    void refetch()
    void qc.invalidateQueries({ queryKey: ['stats'] })
    void qc.invalidateQueries({ queryKey: ['filtros'] })
  }, [qc, refetch, syncStatus?.last_mp_sync_at])

  useEffect(() => {
    storage.setItem(TOP_SECTION_STORAGE_KEY, String(topSectionHeight))
  }, [topSectionHeight])

  useEffect(() => {
    storage.setItem(COL_WIDTHS_KEY, JSON.stringify(colWidths))
  }, [colWidths])

  useEffect(() => {
    setColWidths((previous) => buildColWidths(previous))
  }, [])

  const handleColResizeMouseDown = (colId: string, startX: number, currentWidth: number) => {
    colResizeRef.current = { colId, startX, startWidth: currentWidth }

    const onMouseMove = (e: MouseEvent) => {
      const active = colResizeRef.current
      if (!active) return
      const diff = e.clientX - active.startX
      const newWidth = Math.max(MIN_COL_WIDTH, active.startWidth + diff)
      setColWidths((prev) => ({ ...prev, [active.colId]: newWidth }))
    }

    const onMouseUp = () => {
      colResizeRef.current = null
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  const activeColumns = normalizeOcListColumns(appConfig?.oc_list_columns?.length ? appConfig.oc_list_columns : DEFAULT_OC_LIST_COLUMNS)
    .map((id) => OC_LIST_COLUMNS_AVAILABLE.find((column) => column.id === id))
    .filter(Boolean) as Array<{ id: OcListColumnId; name: string }>

  const syncSearchParams = (next: OcFilters) => {
    const params = new URLSearchParams()
    const appendMulti = (key: keyof OcFilters) => {
      const value = next[key]
      if (Array.isArray(value)) {
        value.forEach((entry) => entry && params.append(key, entry))
      }
    }
    appendMulti('estado')
    appendMulti('estado_mp')
    appendMulti('tipo_oc')
    appendMulti('cartera')
    appendMulti('holding')
    appendMulti('responsable')
    if (next.fecha_desde) params.set('fecha_desde', next.fecha_desde)
    if (next.fecha_hasta) params.set('fecha_hasta', next.fecha_hasta)
    if (next.fecha_ingreso_desde) params.set('fecha_ingreso_desde', next.fecha_ingreso_desde)
    if (next.fecha_ingreso_hasta) params.set('fecha_ingreso_hasta', next.fecha_ingreso_hasta)
    if (next.busqueda) params.set('busqueda', next.busqueda)
    setSearchParams(params, { replace: true })
  }

  const searchedOcCode = normalizePublicOcCode(filters.busqueda)
  const canImportFromMp = !isLoading && ocs.length === 0 && Boolean(searchedOcCode)

  const importMpMutation = useMutation({
    mutationFn: () => importarOcMp(searchedOcCode),
    onSuccess: (result) => {
      const next = { busqueda: result.codigo_oc }
      qc.setQueryData(['ocs', next], [result.oc])
      setDraft(next)
      setFilters(next)
      syncSearchParams(next)
      setSelectedCodigo(result.codigo_oc)
      void qc.invalidateQueries({ queryKey: ['ocs'] })
      void qc.invalidateQueries({ queryKey: ['stats'] })
      void qc.invalidateQueries({ queryKey: ['filtros'] })
    },
  })

  // Auto-import desde MP cuando la búsqueda parece un código válido y no hay resultados
  useEffect(() => {
    if (
      canImportFromMp &&
      !importMpMutation.isPending &&
      !importMpMutation.isSuccess &&
      autoImportTriedRef.current !== searchedOcCode
    ) {
      autoImportTriedRef.current = searchedOcCode
      importMpMutation.mutate()
    }
  }, [canImportFromMp, searchedOcCode, importMpMutation])

  const apply = () => {
    const next = { ...draft }
    setFilters(next)
    syncSearchParams(next)
  }

  const clear = () => {
    setDraft({})
    setFilters({})
    setSoloHoy(false)
    setSearchParams({}, { replace: true })
  }

  const handleSoloHoy = (checked: boolean) => {
    setSoloHoy(checked)
    if (checked) {
      const currentDay = today()
      const next = { ...draft, fecha_desde: currentDay, fecha_hasta: currentDay }
      setDraft(next)
      setFilters(next)
      syncSearchParams(next)
      return
    }

    const next = { ...draft, fecha_desde: undefined, fecha_hasta: undefined }
    setDraft(next)
    setFilters(next)
    syncSearchParams(next)
  }

  const set = (key: keyof OcFilters, value: string) =>
    setDraft((previous) => ({ ...previous, [key]: value || undefined }))

  const setMulti = (key: keyof OcFilters, value: string[]) =>
    setDraft((previous) => ({ ...previous, [key]: value.length ? value : undefined }))

  const handleDividerMouseDown = (clientY: number) => {
    resizeRef.current = { startY: clientY, startHeight: topSectionHeight }

    const onMouseMove = (event: MouseEvent) => {
      if (!resizeRef.current) return
      const diff = event.clientY - resizeRef.current.startY
      const containerHeight = rootRef.current?.clientHeight ?? window.innerHeight
      const maxTopHeight = Math.max(MIN_TOP_SECTION_HEIGHT, containerHeight - MIN_DETAIL_SECTION_HEIGHT)
      setTopSectionHeight(clamp(resizeRef.current.startHeight + diff, MIN_TOP_SECTION_HEIGHT, maxTopHeight))
    }

    const onMouseUp = () => {
      resizeRef.current = null
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    document.body.style.cursor = 'row-resize'
    document.body.style.userSelect = 'none'
  }

  return (
    <div ref={rootRef} className="oc-view-shell app-content-transparent flex h-full flex-col overflow-hidden">
      <div className="border-b border-gray-800 px-5 py-3">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="page-title">Ordenes de compra</h1>
            <p className="mt-0.5 text-sm text-gray-400">
              Navegacion rapida con bandeja arriba y detalle siempre visible abajo.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button className="btn-secondary" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
              Actualizar
            </button>
            <button className="btn-secondary" onClick={() => exportAll(filters)}>
              <Download size={14} />
              Exportar
            </button>
          </div>
        </div>
      </div>

      <div className="flex-none px-5 py-2" style={{ height: topSectionHeight }}>
        <div className="flex h-full flex-col gap-2">
          <section className="oc-surface flex-none rounded-2xl border border-gray-800 overflow-visible">
            <div className="flex flex-wrap items-end gap-1.5 px-3 py-2">
              <div className="min-w-[180px] flex-[1.2]">
                <label className="label">Busqueda</label>
                <div className="relative">
                  <Search size={13} className="pointer-events-none absolute left-2.5 top-2 text-gray-500" />
                  <input
                    className="input pl-8"
                    placeholder="Codigo, comprador..."
                    value={draft.busqueda || ''}
                    onChange={(event) => set('busqueda', event.target.value)}
                    onKeyDown={(event) => event.key === 'Enter' && apply()}
                  />
                </div>
              </div>

              <div className="min-w-[110px] flex-1">
                <label className="label">Estado interno</label>
                <MultiSelect
                  options={[...ESTADOS_INTERNOS]}
                  value={draft.estado ?? []}
                  onChange={(value) => setMulti('estado', value)}
                />
              </div>

              <div className="min-w-[110px] flex-1">
                <label className="label">Estado MP</label>
                <MultiSelect
                  options={filtros?.estados_mp ?? []}
                  value={draft.estado_mp ?? []}
                  onChange={(value) => setMulti('estado_mp', value)}
                />
              </div>

              <div className="min-w-[100px] flex-1">
                <label className="label">Tipo</label>
                <MultiSelect
                  options={filtros?.tipos ?? []}
                  value={draft.tipo_oc ?? []}
                  onChange={(value) => setMulti('tipo_oc', value)}
                />
              </div>

              <div className="min-w-[100px] flex-1">
                <label className="label">Cartera</label>
                <MultiSelect
                  options={filtros?.carteras ?? []}
                  value={draft.cartera ?? []}
                  onChange={(value) => setMulti('cartera', value)}
                />
              </div>

              {(filtros?.holdings?.length ?? 0) > 0 && (
                <div className="min-w-[100px] flex-1">
                  <label className="label">Holding</label>
                  <MultiSelect
                    options={(filtros?.holdings ?? []).map((h) => h.nombre)}
                    value={(draft.holding ?? []).map(
                      (id) => filtros?.holdings.find((h) => h.id === id)?.nombre ?? id
                    )}
                    onChange={(names) =>
                      setMulti(
                        'holding',
                        names.map(
                          (n) => filtros?.holdings.find((h) => h.nombre === n)?.id ?? n
                        )
                      )
                    }
                  />
                </div>
              )}

              <label className="flex h-[32px] items-center gap-1.5 rounded-lg border border-gray-800 bg-gray-950/60 px-2 text-xs text-gray-300 whitespace-nowrap self-end">
                <input
                  type="checkbox"
                  className="rounded border-gray-700 bg-gray-900"
                  checked={soloHoy}
                  onChange={(event) => handleSoloHoy(event.target.checked)}
                />
                Solo hoy
              </label>

              {!soloHoy && (
                <>
                  <div>
                    <label className="label">Desde</label>
                    <input
                      type="date"
                      className="input min-w-[120px]"
                      value={draft.fecha_desde || ''}
                      onChange={(event) => set('fecha_desde', event.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label">Hasta</label>
                    <input
                      type="date"
                      className="input min-w-[120px]"
                      value={draft.fecha_hasta || ''}
                      onChange={(event) => set('fecha_hasta', event.target.value)}
                    />
                  </div>
                </>
              )}

              <div className="flex gap-1.5 self-end">
                <button className="btn-primary" onClick={apply}>
                  Aplicar
                </button>
                <button className="btn-secondary" onClick={clear}>
                  <FilterX size={14} />
                  Limpiar
                </button>
              </div>
            </div>
          </section>

          <section className="oc-surface min-h-0 flex-1 overflow-hidden rounded-2xl border border-gray-800">
            <div className="oc-subtle-strip flex flex-col gap-2 border-b border-gray-800 px-4 py-2.5">
              <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-100">Bandeja de OCs</div>
                  <div className="mt-0.5 text-[11px] text-gray-500">
                    {ocs.length} resultado(s){selectedCodigo ? ' | detalle abierto' : ' | selecciona una fila para ver detalle'}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-gray-500">
                  <span className="rounded-full border border-gray-800 bg-gray-950/70 px-2.5 py-0.5">
                    Navegacion rapida
                  </span>
                  <span className="rounded-full border border-gray-800 bg-gray-950/70 px-2.5 py-0.5">
                    Detalle siempre visible
                  </span>
                  <button className="btn-ghost px-2.5 py-1 text-[11px]" onClick={() => setShowColumnConfig(true)}>
                    <Settings2 size={13} />
                    Columnas
                  </button>
                </div>
              </div>
            </div>

            <div className="h-full overflow-auto">
              {isLoading ? (
                <div className="flex h-40 items-center justify-center text-gray-500">Cargando ordenes de compra...</div>
              ) : (
                <table className="tbl" style={{ tableLayout: 'fixed', width: '100%' }}>
                  <colgroup>
                    {activeColumns.map((col) => (
                      <col key={col.id} style={{ width: colWidths[col.id] ?? DEFAULT_COL_WIDTHS[col.id] ?? 120 }} />
                    ))}
                  </colgroup>
                  <thead>
                    <tr>
                      {activeColumns.map((column, index) => (
                        <th
                          key={column.id}
                          className={column.id === 'total' ? 'text-right' : column.id === 'cantidad_lineas' ? 'text-center' : ''}
                          style={{ position: 'relative', width: colWidths[column.id] ?? DEFAULT_COL_WIDTHS[column.id] ?? 120 }}
                        >
                          {column.name}
                          {index < activeColumns.length - 1 && (
                            <div
                              aria-hidden="true"
                              style={{
                                position: 'absolute',
                                right: 0,
                                top: 8,
                                bottom: 8,
                                width: 1,
                                background: 'rgba(148, 163, 184, 0.22)',
                                pointerEvents: 'none',
                              }}
                            />
                          )}
                          <div
                            style={{
                              position: 'absolute',
                              right: 0,
                              top: 0,
                              bottom: 0,
                              width: 6,
                              cursor: 'col-resize',
                              zIndex: 1,
                            }}
                            onMouseDown={(e) => {
                              e.stopPropagation()
                              const th = (e.currentTarget as HTMLDivElement).parentElement as HTMLTableCellElement | null
                              handleColResizeMouseDown(
                                column.id,
                                e.clientX,
                                th?.offsetWidth ?? colWidths[column.id] ?? DEFAULT_COL_WIDTHS[column.id] ?? 120
                              )
                            }}
                          />
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {ocs.length === 0 && (
                      <tr>
                        <td colSpan={activeColumns.length || 1} className="px-6 py-14 text-center">
                          <div className="space-y-3">
                            <div className="text-sm font-medium text-gray-200">No hay OCs para la combinacion actual.</div>
                            <div className="text-sm text-gray-500">
                              Ajusta fechas o filtros para ampliar la bandeja.
                            </div>
                            {canImportFromMp && importMpMutation.isPending && (
                              <div className="flex items-center gap-2 text-sm text-cyan-400">
                                <RefreshCw size={14} className="animate-spin" />
                                Buscando en Mercado Público…
                              </div>
                            )}
                            {canImportFromMp && importMpMutation.isError && (
                              <div className="flex flex-col items-center gap-2">
                                <div className="max-w-md text-xs text-red-300">
                                  {importMpMutation.error instanceof Error
                                    ? importMpMutation.error.message
                                    : 'No encontrada en Mercado Público'}
                                </div>
                                <button
                                  className="btn-secondary text-xs"
                                  onClick={() => {
                                    autoImportTriedRef.current = null
                                    importMpMutation.reset()
                                  }}
                                >
                                  <RefreshCw size={12} />
                                  Reintentar
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                    {ocs.map((oc) => (
                      <OcRow
                        key={oc.codigo_oc}
                        oc={oc}
                        columns={activeColumns}
                        selected={oc.codigo_oc === selectedCodigo}
                        onToggle={() => setSelectedCodigo((current) => (current === oc.codigo_oc ? null : oc.codigo_oc))}
                      />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </div>
      </div>

      <div className="flex-none px-5 pb-2">
        <div
          className="group flex h-4 cursor-row-resize items-center justify-center"
          onMouseDown={(event) => handleDividerMouseDown(event.clientY)}
          onDoubleClick={() => setTopSectionHeight(DEFAULT_TOP_SECTION_HEIGHT)}
          title="Arrastra para ajustar la altura entre bandeja y detalle"
          aria-label="Ajustar altura entre bandeja y detalle"
        >
          <div className="h-1 w-16 rounded-full bg-gray-700 transition-colors group-hover:bg-blue-400/60" />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden px-5 pb-5">
        <div className="oc-detail-surface h-full overflow-hidden rounded-2xl border border-gray-800">
          {selectedCodigo ? (
            <OcDetailPanel codigo={selectedCodigo} onClose={() => setSelectedCodigo(null)} />
          ) : (
            <div className="flex h-full items-center justify-center px-6 text-center">
              <div className="max-w-lg space-y-3">
                <div className="text-lg font-semibold text-gray-100">Selecciona una OC para ver el detalle</div>
                <div className="text-sm leading-6 text-gray-500">
                  Mantuvimos la bandeja arriba y el detalle abajo para que puedas revisar y avanzar mas rapido
                  entre una OC y otra sin salir de la pantalla principal.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {showColumnConfig && <OcListColumnConfigModal onClose={() => setShowColumnConfig(false)} />}
    </div>
  )
}

function OcRow({
  oc,
  columns,
  selected,
  onToggle,
}: {
  oc: OrdenCompra
  columns: Array<{ id: OcListColumnId; name: string }>
  selected: boolean
  onToggle: () => void
}) {
  return (
    <tr
      className={`cursor-pointer transition-colors ${
        selected ? 'bg-blue-950/20' : 'hover:bg-gray-900/70'
      }`}
      onClick={() => {
        if (hasSelectedText()) return
        onToggle()
      }}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onToggle()
        }
      }}
      tabIndex={0}
      aria-selected={selected}
    >
      {columns.map((column) => (
        <td
          key={column.id}
          className={`${
            column.id === 'total'
              ? 'text-right'
              : column.id === 'cantidad_lineas'
                ? 'text-center text-gray-400'
                : ''
          }`}
        >
          {renderOcCell(oc, column.id)}
        </td>
      ))}
    </tr>
  )
}

function renderOcCell(oc: OrdenCompra, columnId: OcListColumnId) {
  const copyableProps = (text: string) => ({
    className: 'copyable-text',
    title: 'Doble clic para copiar',
    onMouseDown: (event: ReactMouseEvent) => {
      event.stopPropagation()
    },
    onClick: (event: ReactMouseEvent) => {
      event.stopPropagation()
    },
    onDoubleClick: (event: ReactMouseEvent) => {
      event.stopPropagation()
      void copyText(text)
    },
  })

  if (columnId === 'codigo_oc') {
    const displayCode = displayOcCode(oc.codigo_oc, oc.tipo_oc)
    return (
      <span
        {...copyableProps(oc.codigo_oc)}
        className="copyable-text font-mono text-left text-blue-300"
        title={displayCode !== oc.codigo_oc ? oc.codigo_oc : undefined}
      >
        {displayCode}
      </span>
    )
  }
  if (columnId === 'holding') {
    const nombre = oc.holding_nombre || (oc.tipo_oc === 'PRIVADA' ? oc.codigo_organismo : '')
    return nombre
      ? <span {...copyableProps(nombre)} className="copyable-text text-gray-300">{nombre}</span>
      : <span className="text-gray-600">-</span>
  }
  if (columnId === 'tipo_oc') {
    return (
      <span
        className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
          isCm(oc.tipo_oc) ? 'bg-violet-500/15 text-violet-300' : 'bg-gray-800 text-gray-300'
        }`}
      >
        {oc.tipo_oc}
      </span>
    )
  }
  if (columnId === 'estado_mp') {
    return <span {...copyableProps(oc.estado_mp)} className="copyable-text text-gray-400">{oc.estado_mp}</span>
  }
  if (columnId === 'estado_interno') {
    return (
      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-medium ${estadoInternoBgClass(oc.estado_interno)}`}>
        {oc.estado_interno}
      </span>
    )
  }
  if (columnId === 'fecha_envio') {
    return <span {...copyableProps(fmtDate(oc.fecha_envio))} className="copyable-text text-gray-400">{fmtDate(oc.fecha_envio)}</span>
  }
  if (columnId === 'fecha_ingreso') {
    const val = oc.fecha_ingreso ? fmtDate(oc.fecha_ingreso) : '-'
    return <span {...copyableProps(val)} className={`copyable-text ${oc.fecha_ingreso ? 'text-green-400' : 'text-gray-600'}`}>{val}</span>
  }
  if (columnId === 'nombre_organismo') {
    return (
      <div className="max-w-[280px] whitespace-normal">
        <div {...copyableProps(oc.nombre_organismo)} className="copyable-text text-gray-100" title={oc.nombre_organismo}>
          {oc.nombre_organismo}
        </div>
      </div>
    )
  }
  if (columnId === 'cliente_sap_sugerido') {
    return <span {...copyableProps(oc.cliente_sap_sugerido || '')} className="copyable-text font-mono text-xs text-gray-200">{oc.cliente_sap_sugerido || '-'}</span>
  }
  if (columnId === 'responsable_ingreso_username') {
    return <span {...copyableProps(oc.responsable_ingreso_username || '')} className="copyable-text text-gray-300">{oc.responsable_ingreso_username || 'Sin responsable'}</span>
  }
  if (columnId === 'ingresado_por_username') {
    return <span {...copyableProps(oc.ingresado_por_username || '')} className="copyable-text text-gray-300">{oc.ingresado_por_username || '-'}</span>
  }
  if (columnId === 'ingreso_sap_acuerdo_global') {
    return (
      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
        oc.ingreso_sap_acuerdo_global ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/25' : 'bg-gray-800 text-gray-400'
      }`}>
        {oc.ingreso_sap_acuerdo_global ? 'Global' : 'Normal'}
      </span>
    )
  }
  if (columnId === 'cartera') {
    return <span {...copyableProps(oc.cartera || '')} className="copyable-text text-gray-400">{oc.cartera || '-'}</span>
  }
  if (columnId === 'vendedor') {
    return <span {...copyableProps(oc.vendedor || '')} className="copyable-text text-gray-300">{oc.vendedor || '-'}</span>
  }
  if (columnId === 'total') {
    return <span {...copyableProps(fmtMoney(oc.total, oc.moneda))} className="copyable-text">{fmtMoney(oc.total, oc.moneda)}</span>
  }
  if (columnId === 'cantidad_lineas') {
    return <span {...copyableProps(String(oc.cantidad_lineas))} className="copyable-text">{oc.cantidad_lineas}</span>
  }
  return null
}
