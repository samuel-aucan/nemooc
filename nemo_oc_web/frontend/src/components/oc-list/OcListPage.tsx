import { useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'
import { useQuery } from '@tanstack/react-query'
import {
  Download,
  FilterX,
  RefreshCw,
  Search,
} from 'lucide-react'

import { exportAll, getFiltros, getOcs, type OcFilters } from '../../api/ocs'
import { ESTADOS_INTERNOS, estadoInternoBgClass, fmtDate, fmtMoney } from '../../utils/formatters'
import type { OrdenCompra } from '../../types/oc'
import MultiSelect from '../common/MultiSelect'
import OcDetailPanel from '../oc-detail/OcDetailPanel'

const TIPO_CM = ['CM']
const TOP_SECTION_STORAGE_KEY = 'oc-list-top-section-height'
const DEFAULT_TOP_SECTION_HEIGHT = 330
const MIN_TOP_SECTION_HEIGHT = 220
const MIN_DETAIL_SECTION_HEIGHT = 240

function isCm(tipo: string) {
  return TIPO_CM.includes(tipo?.toUpperCase())
}

const today = () => format(new Date(), 'yyyy-MM-dd')

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

export default function OcListPage() {
  const rootRef = useRef<HTMLDivElement | null>(null)
  const resizeRef = useRef<{ startY: number; startHeight: number } | null>(null)
  const [filters, setFilters] = useState<OcFilters>({})
  const [draft, setDraft] = useState<OcFilters>({})
  const [selectedCodigo, setSelectedCodigo] = useState<string | null>(null)
  const [soloHoy, setSoloHoy] = useState(false)
  const [topSectionHeight, setTopSectionHeight] = useState(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_TOP_SECTION_HEIGHT
    }

    const saved = Number(window.localStorage.getItem(TOP_SECTION_STORAGE_KEY))
    return Number.isFinite(saved) && saved > 0 ? saved : DEFAULT_TOP_SECTION_HEIGHT
  })

  const { data: ocs = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['ocs', filters],
    queryFn: () => getOcs(filters),
  })

  const { data: filtros } = useQuery({
    queryKey: ['filtros'],
    queryFn: getFiltros,
  })

  useEffect(() => {
    if (selectedCodigo && !ocs.some((oc) => oc.codigo_oc === selectedCodigo)) {
      setSelectedCodigo(null)
    }
  }, [ocs, selectedCodigo])

  useEffect(() => {
    window.localStorage.setItem(TOP_SECTION_STORAGE_KEY, String(topSectionHeight))
  }, [topSectionHeight])

  const apply = () => setFilters({ ...draft })

  const clear = () => {
    setDraft({})
    setFilters({})
    setSoloHoy(false)
  }

  const handleSoloHoy = (checked: boolean) => {
    setSoloHoy(checked)
    if (checked) {
      const currentDay = today()
      const next = { ...draft, fecha_desde: currentDay, fecha_hasta: currentDay }
      setDraft(next)
      setFilters(next)
      return
    }

    const next = { ...draft, fecha_desde: undefined, fecha_hasta: undefined }
    setDraft(next)
    setFilters(next)
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
    <div ref={rootRef} className="flex h-full flex-col overflow-hidden bg-gray-950">
      <div className="border-b border-gray-800 px-5 py-3">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-gray-50">Ordenes de compra</h1>
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
          <section className="flex-none rounded-2xl border border-gray-800 bg-gray-900/80">
            <div className="flex flex-wrap items-end gap-2 px-4 py-2.5">
              <div className="min-w-[280px] flex-[1.2]">
                <label className="label">Busqueda</label>
                <div className="relative">
                  <Search size={15} className="pointer-events-none absolute left-3 top-2.5 text-gray-500" />
                  <input
                    className="input pl-9"
                    placeholder="Codigo, comprador o cliente SAP..."
                    value={draft.busqueda || ''}
                    onChange={(event) => set('busqueda', event.target.value)}
                    onKeyDown={(event) => event.key === 'Enter' && apply()}
                  />
                </div>
              </div>

              <div className="min-w-[170px] flex-1">
                <label className="label">Estado interno</label>
                <MultiSelect
                  options={[...ESTADOS_INTERNOS]}
                  value={draft.estado ?? []}
                  onChange={(value) => setMulti('estado', value)}
                />
              </div>

              <div className="min-w-[170px] flex-1">
                <label className="label">Estado MP</label>
                <MultiSelect
                  options={filtros?.estados_mp ?? []}
                  value={draft.estado_mp ?? []}
                  onChange={(value) => setMulti('estado_mp', value)}
                />
              </div>

              <div className="min-w-[150px] flex-1">
                <label className="label">Tipo</label>
                <MultiSelect
                  options={filtros?.tipos ?? []}
                  value={draft.tipo_oc ?? []}
                  onChange={(value) => setMulti('tipo_oc', value)}
                />
              </div>

              <div className="min-w-[150px] flex-1">
                <label className="label">Cartera</label>
                <MultiSelect
                  options={filtros?.carteras ?? []}
                  value={draft.cartera ?? []}
                  onChange={(value) => setMulti('cartera', value)}
                />
              </div>

              <label className="flex h-[42px] items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-3 py-2 text-sm text-gray-300">
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
                  <div className="w-full sm:w-auto">
                    <label className="label">Desde</label>
                    <input
                      type="date"
                      className="input min-w-[150px]"
                      value={draft.fecha_desde || ''}
                      onChange={(event) => set('fecha_desde', event.target.value)}
                    />
                  </div>
                  <div className="w-full sm:w-auto">
                    <label className="label">Hasta</label>
                    <input
                      type="date"
                      className="input min-w-[150px]"
                      value={draft.fecha_hasta || ''}
                      onChange={(event) => set('fecha_hasta', event.target.value)}
                    />
                  </div>
                </>
              )}

              <div className="ml-auto flex flex-wrap gap-2">
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

          <section className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-gray-800 bg-gray-900/80">
            <div className="flex flex-col gap-2 border-b border-gray-800 px-4 py-2.5">
              <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-100">Bandeja de OCs</div>
                  <div className="mt-0.5 text-[11px] text-gray-500">
                    {ocs.length} resultado(s){selectedCodigo ? ' | detalle abierto' : ' | selecciona una fila para ver detalle'}
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5 text-[11px] text-gray-500">
                  <span className="rounded-full border border-gray-800 bg-gray-950/70 px-2.5 py-0.5">
                    Navegacion rapida
                  </span>
                  <span className="rounded-full border border-gray-800 bg-gray-950/70 px-2.5 py-0.5">
                    Detalle siempre visible
                  </span>
                </div>
              </div>
            </div>

            <div className="h-full overflow-auto">
              {isLoading ? (
                <div className="flex h-40 items-center justify-center text-gray-500">Cargando ordenes de compra...</div>
              ) : (
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Codigo OC</th>
                      <th>Tipo</th>
                      <th>Estado MP</th>
                      <th>Estado</th>
                      <th>Fecha</th>
                      <th>Comprador</th>
                      <th>Cliente SAP</th>
                      <th>Cartera</th>
                      <th className="text-right">Total</th>
                      <th className="text-center">Lineas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ocs.length === 0 && (
                      <tr>
                        <td colSpan={10} className="px-6 py-14 text-center">
                          <div className="space-y-2">
                            <div className="text-sm font-medium text-gray-200">No hay OCs para la combinacion actual.</div>
                            <div className="text-sm text-gray-500">
                              Ajusta fechas o filtros para ampliar la bandeja.
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                    {ocs.map((oc) => (
                      <OcRow
                        key={oc.codigo_oc}
                        oc={oc}
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
        <div className="h-full overflow-hidden rounded-2xl border border-gray-800 bg-gray-900/40">
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
    </div>
  )
}

function OcRow({
  oc,
  selected,
  onToggle,
}: {
  oc: OrdenCompra
  selected: boolean
  onToggle: () => void
}) {
  return (
    <tr
      className={`cursor-pointer transition-colors ${
        selected ? 'bg-blue-950/20' : 'hover:bg-gray-900/70'
      }`}
      onClick={onToggle}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onToggle()
        }
      }}
      tabIndex={0}
      aria-selected={selected}
    >
      <td className="font-mono text-left text-blue-300">{oc.codigo_oc}</td>
      <td>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
            isCm(oc.tipo_oc) ? 'bg-violet-500/15 text-violet-300' : 'bg-gray-800 text-gray-300'
          }`}
        >
          {oc.tipo_oc}
        </span>
      </td>
      <td className="text-gray-400">{oc.estado_mp}</td>
      <td>
        <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-medium ${estadoInternoBgClass(oc.estado_interno)}`}>
          {oc.estado_interno}
        </span>
      </td>
      <td className="text-gray-400">{fmtDate(oc.fecha_envio)}</td>
      <td className="max-w-[280px] whitespace-normal">
        <div className="text-gray-100" title={oc.nombre_organismo}>
          {oc.nombre_organismo}
        </div>
      </td>
      <td className="font-mono text-xs text-gray-200">{oc.cliente_sap_sugerido || '-'}</td>
      <td className="text-gray-400">{oc.cartera || '-'}</td>
      <td className="text-right">{fmtMoney(oc.total, oc.moneda)}</td>
      <td className="text-center text-gray-400">{oc.cantidad_lineas}</td>
    </tr>
  )
}
