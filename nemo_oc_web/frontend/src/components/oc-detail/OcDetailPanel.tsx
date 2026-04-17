import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react'
import { useDebounce } from '../../hooks/useDebounce'
import { createPortal } from 'react-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckSquare,
  Copy,
  ExternalLink,
  FileDown,
  RefreshCw,
  Save,
  Settings,
  X,
} from 'lucide-react'

import {
  asignarItemcode,
  exportOc,
  getOc,
  getSugerencias,
  limpiarAsignacion,
  marcarIngresada,
  rehomologarPrivada,
  updateEstado,
  updateNotas,
} from '../../api/ocs'
import { searchMaestra } from '../../api/catalogs'
import { getConfig, updateConfig } from '../../api/config'
import type { LineaOC } from '../../types/oc'
import { copyText, hasSelectedText } from '../../utils/clipboard'
import { storage } from '../../utils/storage'
import { ESTADOS_INTERNOS, estadoInternoBgClass, fmtDate, fmtMoney, fmtNumberCL, homoBadge, homoRowBg } from '../../utils/formatters'
import ResizableTable from './ResizableTable'
import SapColumnConfigModal from './SapColumnConfigModal'
import OcDetailActions from './OcDetailActions'

const IS_CM = (tipo: string) => tipo?.toUpperCase() === 'CM'
const SAP_VTA_MIGRATION_KEY = 'sap-columns-vta-migrated-v1'

export default function OcDetailPanel({ codigo, onClose }: { codigo: string; onClose: () => void }) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['oc', codigo],
    queryFn: () => getOc(codigo),
    enabled: !!codigo,
  })

  const [selectedCorr, setSelectedCorr] = useState<number | null>(null)
  const [showSapConfig, setShowSapConfig] = useState(false)
  const [copyMsg, setCopyMsg] = useState('')
  const [notas, setNotas] = useState('')
  const [notasSaved, setNotasSaved] = useState(false)
  const [notasDirty, setNotasDirty] = useState(false)

  const { data: appConfig } = useQuery({ queryKey: ['config'], queryFn: getConfig })

  const migrateSapColumns = useMutation({
    mutationFn: (columns: string[]) => updateConfig({ sap_columns: columns }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] })
    },
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['oc', codigo] })

  const mutEstado = useMutation({
    mutationFn: (estado: string) => updateEstado(codigo, estado),
    onSuccess: invalidate,
  })

  const mutIngresada = useMutation({
    mutationFn: () => marcarIngresada(codigo),
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['stats'] })
      qc.invalidateQueries({ queryKey: ['ocs'] })
    },
  })

  const mutRehomologar = useMutation({
    mutationFn: () => rehomologarPrivada(codigo),
    onSuccess: (result) => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['stats'] })
      setCopyMsg(
        result.actualizadas > 0
          ? `${result.actualizadas} linea(s) homologadas desde el catalogo.`
          : 'No se encontraron nuevas homologaciones en el catalogo.'
      )
      setTimeout(() => setCopyMsg(''), 4000)
    },
  })

  const mutNotas = useMutation({
    mutationFn: (nextNotas: string) => updateNotas(codigo, nextNotas),
    onSuccess: () => {
      setNotasDirty(false)
      setNotasSaved(true)
      setTimeout(() => setNotasSaved(false), 2000)
      invalidate()
    },
  })

  useEffect(() => {
    if (data?.cabecera) {
      setNotas(data.cabecera.notas || '')
      setNotasDirty(false)
    }
  }, [data?.cabecera])

  useEffect(() => {
    if (typeof window === 'undefined' || !appConfig?.sap_columns?.length) return
    if (storage.getItem(SAP_VTA_MIGRATION_KEY)) return
    if (appConfig.sap_columns.includes('vta')) {
      storage.setItem(SAP_VTA_MIGRATION_KEY, '1')
      return
    }

    const nextColumns = [...appConfig.sap_columns]
    const itemcodeIdx = nextColumns.indexOf('itemcode')
    nextColumns.splice(itemcodeIdx >= 0 ? itemcodeIdx + 1 : 0, 0, 'vta')
    storage.setItem(SAP_VTA_MIGRATION_KEY, '1')
    migrateSapColumns.mutate(nextColumns)
  }, [appConfig?.sap_columns, migrateSapColumns])

  if (isLoading) {
    return <div className="flex h-full items-center justify-center text-gray-500">Cargando OC...</div>
  }

  if (!data) {
    return <div className="p-4 text-red-400">OC no encontrada</div>
  }

  const { cabecera: oc, lineas } = data
  const esCM = IS_CM(oc.tipo_oc)
  const sinHomologar = lineas.filter((linea) => !linea.itemcode_sap).length

  const handleCopySap = async () => {
    let excluidos = 0
    const columns = appConfig?.sap_columns?.length
      ? appConfig.sap_columns
      : ['itemcode', 'descripcion', 'cantidad', 'precio']

    const rows = lineas
      .map((linea) => {
        if (!linea.itemcode_sap) {
          excluidos += 1
          return null
        }

        return columns
          .map((column) => {
            if (column === 'itemcode') return linea.itemcode_sap || ''
            if (column === 'vta') return 'VTA'
            if (column === 'descripcion') return linea.descripcion_sap || linea.producto || ''
            if (column === 'cantidad') return linea.cantidad != null ? fmtNumberCL(linea.cantidad, 0) : ''
            if (column === 'cantidad_sap') {
              return linea.cantidad_sap != null ? fmtNumberCL(linea.cantidad_sap, 0) : fmtNumberCL(linea.cantidad, 0)
            }
            if (column === 'precio') return linea.precio_neto != null ? fmtNumberCL(linea.precio_neto) : ''
            if (column === 'precio_sap') {
              return linea.precio_sap != null ? fmtNumberCL(linea.precio_sap) : linea.precio_neto != null ? fmtNumberCL(linea.precio_neto) : ''
            }
            if (column === 'total') return linea.total != null ? fmtNumberCL(linea.total) : ''
            if (column === 'unidad') return linea.unidad || ''
            if (column === 'especificacion') return linea.especificacion_comprador || ''
            return ''
          })
          .join('\t')
      })
      .filter(Boolean)

    await copyText(rows.join('\r\n'))
    setCopyMsg(excluidos > 0 ? `Copiado. ${excluidos} linea(s) sin itemcode fueron omitidas.` : 'Texto copiado para SAP.')
    setTimeout(() => setCopyMsg(''), 3000)
  }

  const handleCopy = async (text: string, label: string) => {
    await copyText(text)
    setCopyMsg(`${label} copiado.`)
    setTimeout(() => setCopyMsg(''), 2000)
  }

  const handleCopyInline = async (event: ReactMouseEvent, text: string, label: string) => {
    event.stopPropagation()
    if (!text) return
    await handleCopy(text, label)
  }

  const blockRowToggle = (event: ReactMouseEvent) => {
    event.stopPropagation()
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-gray-950">
      <div className="border-b border-gray-800 bg-gray-900/90 px-4 py-2.5">
        <div className="flex flex-col gap-2.5">
          <div className="flex flex-col gap-2 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0 flex flex-wrap items-center gap-2">
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <span className="rounded-full border border-gray-800 bg-gray-950/70 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.12em] text-gray-400">
                  Cliente SAP
                </span>
                <span className={`font-mono text-base font-semibold ${oc.cliente_sap_sugerido ? 'text-emerald-300' : 'text-gray-500'}`}>
                  {oc.cliente_sap_sugerido || 'Sin homologar'}
                </span>
                {oc.cliente_sap_sugerido && (
                  <button
                    className="btn-ghost px-2.5 py-1.5 text-[11px]"
                    onClick={() => handleCopy(oc.cliente_sap_sugerido, 'Cliente SAP')}
                    aria-label="Copiar cliente SAP"
                  >
                    <Copy size={13} />
                    Copiar
                  </button>
                )}
              </div>
              <span className="hidden text-gray-700 md:inline">|</span>
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <span
                  className="copyable-text font-mono text-xl font-semibold text-blue-300"
                  title="Doble clic para copiar"
                  onMouseDown={blockRowToggle}
                  onClick={blockRowToggle}
                  onDoubleClick={(event) => handleCopyInline(event, oc.codigo_oc, 'Codigo OC')}
                >
                  {oc.codigo_oc}
                </span>
                <button
                  className="btn-ghost px-2.5 py-1.5 text-[11px]"
                  onClick={() => handleCopy(oc.codigo_oc, 'Codigo OC')}
                  aria-label="Copiar codigo OC"
                >
                  <Copy size={13} />
                  Copiar codigo
                </button>
                <span
                  className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                    esCM ? 'bg-violet-500/15 text-violet-300' : 'bg-gray-800 text-gray-300'
                  }`}
                >
                  {oc.tipo_oc}
                </span>
                <span className="rounded-full border border-gray-800 bg-gray-950/70 px-2.5 py-1 text-[11px] text-gray-400">
                  {oc.estado_mp}
                </span>
              </div>
            </div>

            <OcDetailActions
              oc={oc}
              esCM={esCM}
              isRehomologating={mutRehomologar.isPending}
              isIngresando={mutIngresada.isPending}
              onRehomologar={() => mutRehomologar.mutate()}
              onCopySap={handleCopySap}
              onOpenSapConfig={() => setShowSapConfig(true)}
              onExport={() => exportOc(codigo)}
              onIngresar={() => mutIngresada.mutate()}
              onClose={onClose}
            />
          </div>

          <div className="flex flex-wrap items-end gap-2.5">
            <CompactMeta
              label="Comprador"
              value={oc.nombre_organismo}
              title={oc.razon_social || oc.nombre_organismo}
              className="min-w-[260px] flex-[1.4]"
            />
            <CompactMeta label="Fecha envio" value={fmtDate(oc.fecha_envio)} className="min-w-[120px]" />
            <CompactMeta label="Cartera" value={oc.cartera || 'Sin cartera'} className="min-w-[110px]" />
            <CompactMeta
              label="Neto"
              value={fmtMoney(oc.total_neto, oc.moneda)}
              className="min-w-[130px]"
            />
            <CompactMeta
              label="IVA"
              value={fmtMoney(oc.impuestos, oc.moneda)}
              className="min-w-[120px]"
            />
            <CompactMeta
              label="Total bruto"
              value={fmtMoney(oc.total, oc.moneda)}
              secondary={`${lineas.length} linea(s)`}
              className="min-w-[150px]"
            />
            {oc.codigo_licitacion && (
              <div className="min-w-[150px]">
                <div className="mb-0.5 text-[10px] uppercase tracking-[0.12em] text-gray-500">Licitacion</div>
                <div className="flex items-center gap-2">
                  <div
                    className="copyable-text truncate text-sm font-medium leading-5 text-gray-100"
                    title="Doble clic para copiar"
                    onMouseDown={blockRowToggle}
                    onClick={blockRowToggle}
                    onDoubleClick={(event) => handleCopyInline(event, oc.codigo_licitacion, 'Licitacion')}
                  >
                    {oc.codigo_licitacion}
                  </div>
                  <button
                    className="btn-ghost px-2 py-1 text-[11px]"
                    onClick={() => handleCopy(oc.codigo_licitacion, 'Licitacion')}
                    aria-label="Copiar licitacion"
                  >
                    <Copy size={12} />
                    Copiar
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-end gap-2.5">
            <CopyableMetaWithButton
              label="Direccion despacho"
              value={oc.direccion_despacho || oc.direccion_unidad || 'Sin direccion'}
              copyLabel="Direccion despacho"
              onCopy={handleCopy}
              className="min-w-[280px] flex-[1.2]"
            />
            <CopyableMetaWithButton
              label="Direccion facturacion"
              value={oc.direccion_facturacion || 'Sin direccion'}
              copyLabel="Direccion facturacion"
              onCopy={handleCopy}
              className="min-w-[280px] flex-[1.2]"
            />

            <div className="min-w-[170px]">
              <label className="mb-0.5 block text-[10px] uppercase tracking-[0.12em] text-gray-500">Estado interno</label>
              <select
                className="select"
                value={oc.estado_interno}
                onChange={(event) => mutEstado.mutate(event.target.value)}
              >
                {ESTADOS_INTERNOS.map((estado) => (
                  <option key={estado}>{estado}</option>
                ))}
              </select>
            </div>

            <div className="min-w-[280px] flex-1">
              <label className="mb-0.5 block text-[10px] uppercase tracking-[0.12em] text-gray-500">Notas internas</label>
              <input
                className="input"
                value={notas}
                onChange={(event) => {
                  setNotas(event.target.value)
                  setNotasDirty(true)
                }}
                placeholder="Observaciones, seguimiento o contexto para el equipo..."
              />
            </div>

            <div className="flex items-end gap-2">
              <button
                className="btn-secondary px-3 py-2 text-xs"
                onClick={() => mutNotas.mutate(notas)}
                disabled={!notasDirty || mutNotas.isPending}
              >
                <Save size={14} />
                {mutNotas.isPending ? 'Guardando...' : 'Guardar notas'}
              </button>
              {notasSaved && <span className="text-xs text-emerald-300">Guardado</span>}
            </div>
          </div>

          {copyMsg && (
            <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/25 px-4 py-3 text-sm text-emerald-200">
              {copyMsg}
            </div>
          )}
        </div>
      </div>

      {sinHomologar > 0 && (
        <div className="flex items-center gap-3 border-b border-amber-800/50 bg-amber-950/30 px-5 py-3 text-sm text-amber-200">
          <AlertTriangle size={16} className="shrink-0" />
          <span>
            {sinHomologar} linea(s) sin homologar. Quedaran fuera del texto copiado para SAP hasta que tengan itemcode.
          </span>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        <ResizableTable
          storageKey="oc-detail"
          columns={[
            { id: 'corr', label: '#', minWidth: 40, defaultWidth: 44 },
            { id: 'codmp', label: 'Cod. Cliente', minWidth: 70, defaultWidth: 95 },
            { id: 'desc', label: 'Descripcion OC', minWidth: 130, defaultWidth: 250 },
            { id: 'itemcode', label: 'ItemCode SAP', minWidth: 90, defaultWidth: 150 },
            { id: 'descitem', label: 'Descripcion item', minWidth: 140, defaultWidth: 210 },
            { id: 'cant', label: 'Cant', align: 'right', minWidth: 55, defaultWidth: 70 },
            { id: 'cantsap', label: 'Cant SAP', align: 'right', minWidth: 60, defaultWidth: 80 },
            { id: 'pneto', label: 'P. Neto', align: 'right', minWidth: 70, defaultWidth: 90 },
            { id: 'psap', label: 'P. SAP', align: 'right', minWidth: 70, defaultWidth: 90 },
            { id: 'total', label: 'Total', align: 'right', minWidth: 70, defaultWidth: 100 },
            { id: 'estado', label: 'Estado', minWidth: 90, defaultWidth: 120 },
          ]}
        >
          {lineas.map((linea) => (
            <LineaRow
              key={linea.correlativo}
              linea={linea}
              selected={selectedCorr === linea.correlativo}
              onClick={() => setSelectedCorr((current) => (current === linea.correlativo ? null : linea.correlativo))}
              codigoOc={codigo}
              onUpdate={invalidate}
            />
          ))}
        </ResizableTable>
      </div>

      {showSapConfig && <SapColumnConfigModal onClose={() => setShowSapConfig(false)} />}
    </div>
  )
}

function LineaRow({
  linea,
  selected,
  onClick,
  codigoOc,
  onUpdate,
}: {
  linea: LineaOC
  selected: boolean
  onClick: () => void
  codigoOc: string
  onUpdate: () => void
}) {
  const [manualCode, setManualCode] = useState('')
  const [message, setMessage] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [dropdownRect, setDropdownRect] = useState<DOMRect | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const debouncedCode = useDebounce(manualCode, 300)

  const { data: sugerencias, isLoading: loadingSugerencias } = useQuery({
    queryKey: ['sugs', codigoOc, linea.correlativo],
    queryFn: () => getSugerencias(codigoOc, linea.correlativo),
    enabled: selected && !linea.itemcode_sap,
    staleTime: 60_000,
  })

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ['maestra-search', debouncedCode],
    queryFn: () => searchMaestra(debouncedCode),
    enabled: selected && showDropdown && debouncedCode.length >= 3,
    staleTime: 60_000,
  })

  const assign = async (itemcode: string, descripcion = '') => {
    await asignarItemcode(codigoOc, linea.correlativo, itemcode, descripcion)
    setMessage(`Asignado ${itemcode}`)
    setManualCode('')
    setShowDropdown(false)
    setTimeout(() => setMessage(''), 2500)
    onUpdate()
  }

  const clearAssign = async () => {
    await limpiarAsignacion(codigoOc, linea.correlativo)
    setMessage('Asignacion eliminada')
    setTimeout(() => setMessage(''), 2000)
    onUpdate()
  }

  const descText = linea.especificacion_comprador || linea.producto || ''
  const badge = homoBadge(linea.estado_homologacion)
  const copyCell = async (event: ReactMouseEvent, text: string, okMessage: string) => {
    event.stopPropagation()
    if (!text) return
    await copyText(text)
    setMessage(okMessage)
    setTimeout(() => setMessage(''), 1800)
  }

  const blockRowToggle = (event: ReactMouseEvent) => {
    event.stopPropagation()
  }

  return (
    <>
      <tr
        className={`${selected ? 'bg-blue-950/20' : homoRowBg(linea.estado_homologacion)} cursor-pointer`}
        onClick={() => {
          if (hasSelectedText()) return
          onClick()
        }}
      >
        <td className="text-gray-500">{linea.correlativo}</td>
        <td className="font-mono text-xs text-gray-400">{linea.codigo_mp || '-'}</td>
        <td className="max-w-[220px] whitespace-normal" title={descText}>
          <span
            className="copyable-text text-gray-100"
            title="Doble clic para copiar"
            onMouseDown={blockRowToggle}
            onClick={blockRowToggle}
            onDoubleClick={(event) => copyCell(event, descText, 'Descripcion OC copiada')}
          >
            {descText}
          </span>
        </td>
        <td>
          {linea.itemcode_sap ? (
            <span
              className="copyable-text font-mono text-xs text-blue-300"
              title="Doble clic para copiar"
              onMouseDown={blockRowToggle}
              onClick={blockRowToggle}
              onDoubleClick={(event) => copyCell(event, linea.itemcode_sap || '', 'ItemCode SAP copiado')}
            >
              {linea.itemcode_sap}
            </span>
          ) : (
            <span className="copyable-text font-mono text-xs text-gray-500">Sin itemcode</span>
          )}
        </td>
        <td className="max-w-[220px] whitespace-normal" title={linea.descripcion_sap || ''}>
          <span
            className="copyable-text text-gray-300"
            title="Doble clic para copiar"
            onMouseDown={blockRowToggle}
            onClick={blockRowToggle}
            onDoubleClick={(event) => copyCell(event, linea.descripcion_sap || '', 'Descripcion SAP copiada')}
          >
            {linea.descripcion_sap || '-'}
          </span>
        </td>
        <td className="text-right">{linea.cantidad}</td>
        <td className="text-right text-gray-400">{linea.cantidad_sap ?? '-'}</td>
        <td className="text-right">{fmtMoney(linea.precio_neto)}</td>
        <td className="text-right text-gray-400">{linea.precio_sap != null ? fmtMoney(linea.precio_sap) : '-'}</td>
        <td className="text-right">{fmtMoney(linea.total)}</td>
        <td>
          <span className={`text-xs font-medium ${badge.color}`}>{badge.label}</span>
        </td>
      </tr>

      {selected && (
        <tr className="bg-gray-900/70">
          <td colSpan={11} className="px-4 py-3">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {sugerencias && sugerencias.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-gray-500">Sugerencias:</span>
                    {sugerencias.slice(0, 3).map((sugerencia) => (
                      <button
                        key={sugerencia.itemcode_sap}
                        className="rounded-lg border border-blue-700/40 bg-blue-950/30 px-2.5 py-1 text-blue-300 transition-colors hover:bg-blue-900/40"
                        title={`${sugerencia.descripcion_match}\n${sugerencia.descripcion_sap}`}
                        onClick={() => assign(sugerencia.itemcode_sap, sugerencia.descripcion_sap)}
                      >
                        {sugerencia.itemcode_sap}
                      </button>
                    ))}
                  </div>
                )}

                {sugerencias?.length === 0 && !loadingSugerencias && (
                  <span className="text-gray-500">No hay sugerencias automaticas para esta linea.</span>
                )}
              </div>

              <div className="flex flex-wrap items-start gap-2">
                <div className="relative min-w-[280px] flex-1">
                  <input
                    ref={inputRef}
                    className="input"
                    placeholder="Buscar itemcode o descripcion en la maestra..."
                    value={manualCode}
                    onChange={(event) => {
                      setManualCode(event.target.value)
                      setShowDropdown(true)
                      setDropdownRect(inputRef.current?.getBoundingClientRect() ?? null)
                    }}
                    onFocus={() => {
                      setShowDropdown(true)
                      setDropdownRect(inputRef.current?.getBoundingClientRect() ?? null)
                    }}
                    onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
                    onKeyDown={(event) => event.key === 'Enter' && manualCode && assign(manualCode)}
                  />

                  {showDropdown && manualCode.length >= 3 && dropdownRect && createPortal(
                    <div
                      className="max-h-52 overflow-y-auto rounded-xl border border-gray-700 bg-gray-950 shadow-2xl"
                      style={{
                        position: 'fixed',
                        top: dropdownRect.bottom + 4,
                        left: dropdownRect.left,
                        width: dropdownRect.width,
                        zIndex: 9999,
                      }}
                    >
                      {searchLoading ? (
                        <div className="px-3 py-2 text-sm text-gray-400">Buscando...</div>
                      ) : searchResults?.length ? (
                        searchResults.map((result) => (
                          <button
                            key={result.itemcode_sap}
                            type="button"
                            className="flex w-full flex-col border-b border-gray-800 px-3 py-2 text-left transition-colors last:border-b-0 hover:bg-gray-900"
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => assign(result.itemcode_sap, result.descripcion_sap)}
                          >
                            <span className="font-mono text-sm text-blue-300">{result.itemcode_sap}</span>
                            <span className="text-sm text-gray-300">{result.descripcion_sap}</span>
                          </button>
                        ))
                      ) : (
                        <div className="px-3 py-2 text-sm text-gray-400">Sin resultados en la maestra.</div>
                      )}
                    </div>,
                    document.body
                  )}
                </div>

                <button className="btn-primary" disabled={!manualCode} onClick={() => assign(manualCode)}>
                  Asignar
                </button>
                {linea.itemcode_sap && (
                  <button className="btn-danger" onClick={clearAssign}>
                    Limpiar
                  </button>
                )}
                {message && <span className="self-center text-sm text-emerald-300">{message}</span>}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function CompactMeta({
  label,
  value,
  secondary,
  className = '',
  title,
}: {
  label: string
  value: string
  secondary?: string
  className?: string
  title?: string
}) {
  return (
    <div className={className}>
      <div className="mb-0.5 text-[10px] uppercase tracking-[0.12em] text-gray-500">{label}</div>
      <div
        className="copyable-text truncate text-sm font-medium leading-5 text-gray-100"
        title={title || value}
        onMouseDown={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
      >
        {value || '-'}
      </div>
      {secondary && <div className="text-xs text-gray-500">{secondary}</div>}
    </div>
  )
}

function CopyableMetaWithButton({
  label,
  value,
  copyLabel,
  className = '',
  onCopy,
}: {
  label: string
  value: string
  copyLabel: string
  className?: string
  onCopy: (text: string, label: string) => Promise<void>
}) {
  return (
    <div className={className}>
      <div className="mb-0.5 text-[10px] uppercase tracking-[0.12em] text-gray-500">{label}</div>
      <div className="flex items-center gap-2">
        <div
          className="copyable-text truncate text-sm font-medium leading-5 text-gray-100"
          title={value}
          onMouseDown={(event) => event.stopPropagation()}
          onClick={(event) => event.stopPropagation()}
        >
          {value || '-'}
        </div>
        <button
          className="btn-ghost px-2 py-1 text-[11px]"
          onClick={() => void onCopy(value, copyLabel)}
          aria-label={`Copiar ${copyLabel}`}
        >
          <Copy size={12} />
          Copiar
        </button>
      </div>
    </div>
  )
}
