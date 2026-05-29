import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react'
import { useDebounce } from '../../hooks/useDebounce'
import { createPortal } from 'react-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  Copy,
  RotateCcw,
  Save,
} from 'lucide-react'

import {
  downloadOcDocumentPdf,
  asignarItemcode,
  downloadOcDocumentHtml,
  exportOc,
  getOc,
  getResponsablesIngreso,
  getSugerencias,
  importarOcMp,
  limpiarAsignacion,
  marcarIngresada,
  openOcDocument,
  refreshOcMpStatus,
  rehomologarPrivada,
  resetSapValues,
  updateResponsableIngreso,
  updateEstado,
  updateNotas,
  updateSapMode,
  updateSapValues,
} from '../../api/ocs'
import { searchMaestra } from '../../api/catalogs'
import { getConfig, updateConfig } from '../../api/config'
import type { LineaOC } from '../../types/oc'
import { copyText, hasSelectedText } from '../../utils/clipboard'
import { storage } from '../../utils/storage'
import {
  ESTADOS_INTERNOS,
  displayOcCode,
  estadoInternoBgClass,
  fmtDate,
  fmtMoney,
  fmtMoneySmart,
  fmtNumberCL,
  fmtNumberSmartCL,
  homoBadge,
  homoRowBg,
  normalizePublicOcCode,
  parseDecimalCL,
} from '../../utils/formatters'
import ResizableTable from './ResizableTable'
import SapColumnConfigModal from './SapColumnConfigModal'
import OcDetailActions from './OcDetailActions'

const IS_CM = (tipo: string) => tipo?.toUpperCase() === 'CM'
const SAP_DISPLAY_TIPOS = new Set(['SE', 'AG', 'CC', 'TD'])
const SAP_VTA_MIGRATION_KEY = 'sap-columns-vta-migrated-v1'

export default function OcDetailPanel({ codigo, onClose }: { codigo: string; onClose: () => void }) {
  const qc = useQueryClient()
  const autoImportTriedRef = useRef<string | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['oc', codigo],
    queryFn: () => getOc(codigo),
    enabled: !!codigo,
    retry: false,
  })

  const importMpMutation = useMutation({
    mutationFn: () => importarOcMp(codigo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['oc', codigo] })
      void qc.invalidateQueries({ queryKey: ['ocs'] })
    },
  })

  // Auto-import desde MP cuando la OC no está en la base y parece código público
  useEffect(() => {
    if (
      !isLoading &&
      !data &&
      error &&
      normalizePublicOcCode(codigo) &&
      !importMpMutation.isPending &&
      !importMpMutation.isSuccess &&
      autoImportTriedRef.current !== codigo
    ) {
      autoImportTriedRef.current = codigo
      importMpMutation.mutate()
    }
  }, [isLoading, data, error, codigo, importMpMutation])

  const [selectedCorr, setSelectedCorr] = useState<number | null>(null)
  const [showSapConfig, setShowSapConfig] = useState(false)
  const [copyMsg, setCopyMsg] = useState('')
  const [notas, setNotas] = useState('')
  const [notasSaved, setNotasSaved] = useState(false)
  const [notasDirty, setNotasDirty] = useState(false)
  const [acuerdoGlobal, setAcuerdoGlobal] = useState(false)

  const { data: appConfig } = useQuery({ queryKey: ['config'], queryFn: getConfig })
  const { data: responsables = [] } = useQuery({
    queryKey: ['responsables-ingreso'],
    queryFn: getResponsablesIngreso,
    staleTime: 5 * 60_000,
  })

  const migrateSapColumns = useMutation({
    mutationFn: (payload: { sap_columns?: string[]; sap_global_columns?: string[] }) => updateConfig(payload),
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
    mutationFn: () => marcarIngresada(codigo, acuerdoGlobal),
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['stats'] })
      qc.invalidateQueries({ queryKey: ['ocs'] })
      qc.invalidateQueries({ queryKey: ['ocs-analytics'] })
    },
  })

  const mutResponsable = useMutation({
    mutationFn: (userId: number | null) => updateResponsableIngreso(codigo, userId),
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['ocs'] })
      qc.invalidateQueries({ queryKey: ['ocs-analytics'] })
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

  const mutRefreshMp = useMutation({
    mutationFn: () => refreshOcMpStatus(codigo),
    onSuccess: (result) => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['ocs'] })
      qc.invalidateQueries({ queryKey: ['sync-status'] })
      const label = result.estado_mp || `codigo ${result.codigo_estado_mp}`
      setCopyMsg(result.updated ? `Estado MP actualizado: ${label}.` : `Estado MP sin cambios: ${label}.`)
      setTimeout(() => setCopyMsg(''), 3500)
    },
    onError: (err) => {
      const detail = err instanceof Error ? err.message : 'No se pudo consultar Mercado Publico.'
      setCopyMsg(detail)
      setTimeout(() => setCopyMsg(''), 4500)
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

    const payload: { sap_columns?: string[]; sap_global_columns?: string[] } = {}
    if (!appConfig.sap_columns.includes('vta')) {
      const nextColumns = [...appConfig.sap_columns]
      const itemcodeIdx = nextColumns.indexOf('itemcode')
      nextColumns.splice(itemcodeIdx >= 0 ? itemcodeIdx + 1 : 0, 0, 'vta')
      payload.sap_columns = nextColumns
    }

    if (appConfig.sap_global_columns?.length && !appConfig.sap_global_columns.includes('vta')) {
      const nextGlobalColumns = [...appConfig.sap_global_columns]
      const itemcodeIdx = nextGlobalColumns.indexOf('itemcode')
      nextGlobalColumns.splice(itemcodeIdx >= 0 ? itemcodeIdx + 1 : 0, 0, 'vta')
      payload.sap_global_columns = nextGlobalColumns
    }

    if (!payload.sap_columns && !payload.sap_global_columns) {
      storage.setItem(SAP_VTA_MIGRATION_KEY, '1')
      return
    }

    storage.setItem(SAP_VTA_MIGRATION_KEY, '1')
    migrateSapColumns.mutate(payload)
  }, [appConfig?.sap_columns, appConfig?.sap_global_columns, migrateSapColumns])

  if (isLoading) {
    return <div className="flex h-full items-center justify-center text-gray-500">Cargando OC...</div>
  }

  if (!data) {
    // Mientras intenta buscar en MP
    if (importMpMutation.isPending) {
      return (
        <div className="flex h-full items-center justify-center gap-2 text-cyan-400">
          <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Buscando en Mercado Público…
        </div>
      )
    }
    const detailError = importMpMutation.isError
      ? (importMpMutation.error instanceof Error ? importMpMutation.error.message : 'No encontrada en Mercado Público')
      : (error instanceof Error ? error.message : '')
    return (
      <div className="space-y-3 p-4">
        <div className="text-red-400">No se pudo cargar el detalle de la OC.</div>
        {detailError ? <div className="text-sm text-gray-500">{detailError}</div> : null}
        {normalizePublicOcCode(codigo) && importMpMutation.isError && (
          <button
            className="btn-secondary text-xs"
            onClick={() => {
              autoImportTriedRef.current = null
              importMpMutation.reset()
            }}
          >
            Reintentar búsqueda en MP
          </button>
        )}
      </div>
    )
  }

  const { cabecera: oc, lineas, documento } = data
  const esCM = IS_CM(oc.tipo_oc)
  const displayCode = displayOcCode(oc.codigo_oc, oc.tipo_oc)
  const sinHomologar = lineas.filter((linea) => !linea.itemcode_sap).length
  const hasDocument = Boolean(documento?.document_available)
  const hasArtikosDocument = documento?.source_type === 'artikos' && documento.document_available
  const hasImapPdfDocument = documento?.source_type === 'imap_attachment' && documento.document_available
  const documentAccessKind = getDocumentAccessKindLabel(documento?.access_payload?.credential_kind)
  const documentVerifiedAt = formatDateTime(documento?.last_verified_at || '')
  const detectedAt = formatDateTime(oc.created_at || documento?.created_at || '')

  const handleCopySap = async () => {
    let excluidos = 0
    const defaultColumns = ['itemcode', 'vta', 'cantidad_sap', 'precio_sap']
    const normalColumns = appConfig?.sap_columns?.length ? appConfig.sap_columns : defaultColumns
    const columns = acuerdoGlobal
      ? appConfig?.sap_global_columns?.length
        ? appConfig.sap_global_columns
        : normalColumns
      : normalColumns

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
              return linea.cantidad_sap != null ? fmtNumberSmartCL(linea.cantidad_sap, 4) : fmtNumberSmartCL(linea.cantidad, 4)
            }
            if (column === 'precio') return linea.precio_neto != null ? fmtNumberSmartCL(linea.precio_neto, 4) : ''
            if (column === 'precio_sap') {
              return linea.precio_sap != null ? fmtNumberSmartCL(linea.precio_sap, 4) : linea.precio_neto != null ? fmtNumberSmartCL(linea.precio_neto, 4) : ''
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
    const formatLabel = acuerdoGlobal ? 'Acuerdo global' : 'Normal'
    setCopyMsg(
      excluidos > 0
        ? `Copiado (${formatLabel}). ${excluidos} linea(s) sin itemcode fueron omitidas.`
        : `Texto copiado para SAP (${formatLabel}).`
    )
    setTimeout(() => setCopyMsg(''), 3000)
  }

  const handleCopy = async (text: string, label: string) => {
    await copyText(text)
    setCopyMsg(`${label} copiado.`)
    setTimeout(() => setCopyMsg(''), 2000)
  }

  const handleOpenDocument = () => {
    if (!hasDocument) return
    openOcDocument(codigo)
  }

  const handleDownloadPdf = () => {
    if (!hasDocument) return
    downloadOcDocumentPdf(codigo)
  }

  const handleDownloadDocument = () => {
    if (!hasArtikosDocument) return
    downloadOcDocumentHtml(codigo)
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
    <div className="oc-view-shell app-content-transparent flex h-full flex-col overflow-hidden">
      <div className="oc-subtle-strip border-b border-gray-800 px-4 py-2.5">
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
                  onDoubleClick={(event) => handleCopyInline(event, displayCode, 'Codigo OC')}
                >
                  {displayCode}
                </span>
                <button
                  className="btn-ghost px-2.5 py-1.5 text-[11px]"
                  onClick={() => handleCopy(displayCode, 'Codigo OC')}
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
              documento={documento}
              esCM={esCM}
              isRehomologating={mutRehomologar.isPending}
              isIngresando={mutIngresada.isPending}
              isRefreshingMp={mutRefreshMp.isPending}
              acuerdoGlobal={acuerdoGlobal}
              onToggleAcuerdoGlobal={setAcuerdoGlobal}
              onRehomologar={() => mutRehomologar.mutate()}
              onRefreshMpStatus={() => mutRefreshMp.mutate()}
              onCopySap={handleCopySap}
              onOpenSapConfig={() => setShowSapConfig(true)}
              onExport={() => exportOc(codigo)}
              onOpenDocument={handleOpenDocument}
              onDownloadPdf={handleDownloadPdf}
              onDownloadDocument={handleDownloadDocument}
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
            <CompactMeta
              label="Detectada"
              value={detectedAt || 'Sin registro'}
              className="min-w-[145px]"
            />
            <CompactMeta label="Fecha envio" value={fmtDate(oc.fecha_envio)} className="min-w-[120px]" />
            <CompactMeta label="Cartera" value={oc.cartera || 'Sin cartera'} className="min-w-[110px]" />
            <CompactMeta label="Ejecutivo" value={oc.vendedor || 'Sin ejecutivo'} className="min-w-[140px]" />
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

            <div className="min-w-[190px]">
              <label className="mb-0.5 block text-[10px] uppercase tracking-[0.12em] text-gray-500">Responsable SAP</label>
              <select
                className="select"
                value={oc.responsable_ingreso_user_id ?? ''}
                onChange={(event) => {
                  const raw = event.target.value
                  mutResponsable.mutate(raw === '' ? null : Number(raw))
                }}
                disabled={mutResponsable.isPending}
              >
                <option value="">Sin responsable</option>
                {responsables.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.nombre_completo || user.username}
                  </option>
                ))}
              </select>
            </div>

            <CompactMeta
              label="Ingresado por"
              value={oc.ingresado_por_username || 'Sin dato'}
              secondary={oc.ingreso_sap_acuerdo_global ? 'Acuerdo global' : undefined}
              className="min-w-[130px]"
            />

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

          {(hasArtikosDocument || hasImapPdfDocument) && (
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-cyan-900/50 bg-cyan-950/20 px-4 py-3">
              <div className="min-w-[220px] flex-1">
                <div className="mb-1 text-[10px] uppercase tracking-[0.12em] text-cyan-300/75">
                  {hasImapPdfDocument ? 'Documento privado' : 'Documento Artikos'}
                </div>
                <div className="text-sm font-medium text-cyan-100">
                  {hasImapPdfDocument
                    ? 'PDF recuperable desde el correo original sin almacenarlo en NemoOC.'
                    : 'Respaldo HTML disponible con PDF automatico generado al momento.'}
                </div>
                <div className="mt-1 text-xs text-cyan-200/80">
                  {documentVerifiedAt ? `Validado: ${documentVerifiedAt}` : 'Validado recientemente'}
                  {documentAccessKind ? ` | Acceso: ${documentAccessKind}` : ''}
                </div>
              </div>
            </div>
          )}

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
            { id: 'sap', label: 'SAP', minWidth: 96, defaultWidth: 112 },
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
              tipoOc={oc.tipo_oc}
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
  tipoOc,
  onUpdate,
}: {
  linea: LineaOC
  selected: boolean
  onClick: () => void
  codigoOc: string
  tipoOc: string
  onUpdate: () => void
}) {
  const [manualCode, setManualCode] = useState('')
  const [message, setMessage] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [dropdownRect, setDropdownRect] = useState<DOMRect | null>(null)
  const [cantidadSapDraft, setCantidadSapDraft] = useState(formatSapDraftValue(linea.cantidad_sap ?? linea.cantidad))
  const [precioSapDraft, setPrecioSapDraft] = useState(formatSapDraftValue(linea.precio_sap ?? linea.precio_neto))
  const inputRef = useRef<HTMLInputElement>(null)
  const debouncedCode = useDebounce(manualCode, 300)

  useEffect(() => {
    setCantidadSapDraft(formatSapDraftValue(linea.cantidad_sap ?? linea.cantidad))
    setPrecioSapDraft(formatSapDraftValue(linea.precio_sap ?? linea.precio_neto))
  }, [linea.correlativo, linea.cantidad, linea.cantidad_sap, linea.precio_neto, linea.precio_sap])

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

  const mutSapMode = useMutation({
    mutationFn: (mode: 'unitario' | 'display') => updateSapMode(codigoOc, linea.correlativo, mode),
    onSuccess: () => {
      onUpdate()
    },
  })

  const mutSapValues = useMutation({
    mutationFn: (values: { cantidad_sap: number; precio_sap: number }) =>
      updateSapValues(codigoOc, linea.correlativo, values),
    onSuccess: () => {
      setMessage('Valores SAP guardados')
      setTimeout(() => setMessage(''), 2500)
      onUpdate()
    },
  })

  const mutResetSapValues = useMutation({
    mutationFn: () => resetSapValues(codigoOc, linea.correlativo),
    onSuccess: () => {
      setMessage('Valores SAP recalculados')
      setTimeout(() => setMessage(''), 2500)
      onUpdate()
    },
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
  const sapModeVisible = SAP_DISPLAY_TIPOS.has((tipoOc || '').toUpperCase()) && !!linea.itemcode_sap
  const sapModeEnabled = sapModeVisible && (linea.factor_empaque || 1) > 1
  const currentSapMode = linea.sap_mode === 'display' ? 'display' : 'unitario'
  const historyText = linea.sap_mode_historial_total > 0
    ? `Historial ${linea.sap_mode_historial_display} DISP / ${linea.sap_mode_historial_unitario} UNI`
    : 'Sin historial aun'
  const sapModeTitle = sapModeEnabled
    ? `Factor display x${fmtNumberCL(linea.factor_empaque || 1, 0)}. ${historyText}.`
    : sapModeVisible
      ? 'Este item no tiene factor util en la maestra, por eso DISP no esta disponible.'
      : ''
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

  const handleSapMode = async (event: ReactMouseEvent, mode: 'unitario' | 'display') => {
    event.stopPropagation()
    if (!sapModeEnabled || currentSapMode === mode || mutSapMode.isPending) return
    await mutSapMode.mutateAsync(mode)
  }

  const handleSaveSapValues = async () => {
    const cantidad_sap = parseSapDraftValue(cantidadSapDraft)
    const precio_sap = parseSapDraftValue(precioSapDraft)
    if (cantidad_sap == null || precio_sap == null) {
      setMessage('Cantidad y precio SAP deben ser numericos')
      setTimeout(() => setMessage(''), 2500)
      return
    }
    await mutSapValues.mutateAsync({ cantidad_sap, precio_sap })
  }

  const handleResetSapValues = async () => {
    await mutResetSapValues.mutateAsync()
  }

  const sapValueTone = linea.sap_values_origen === 'manual'
    ? 'text-amber-300'
    : linea.sap_values_origen === 'aprendizaje'
      ? 'text-emerald-300'
      : 'text-gray-400'
  const sapOriginLabel = getSapValuesOriginLabel(linea.sap_values_origen)

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
            <div className="flex items-center gap-1">
              <span
                className="copyable-text font-mono text-xs text-blue-300"
                title="Doble clic para copiar"
                onMouseDown={blockRowToggle}
                onClick={blockRowToggle}
                onDoubleClick={(event) => copyCell(event, linea.itemcode_sap || '', 'ItemCode SAP copiado')}
              >
                {linea.itemcode_sap}
              </span>
              {linea.estado_homologacion === 'manual' && (
                <span className="rounded bg-amber-500/20 px-1 py-0.5 text-[9px] font-semibold uppercase text-amber-300" title="Asignado manualmente">Editado</span>
              )}
              {linea.estado_homologacion === 'sugerido' && (
                <span className="rounded bg-violet-500/20 px-1 py-0.5 text-[9px] font-semibold uppercase text-violet-300" title="Asignado desde sugerencia">Sugerido</span>
              )}
            </div>
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
        <td className="text-right">{fmtNumberSmartCL(linea.cantidad, 4)}</td>
        <td className={`text-right ${sapValueTone}`}>{fmtNumberSmartCL(linea.cantidad_sap ?? linea.cantidad, 4)}</td>
        <td className="text-right">{fmtMoneySmart(linea.precio_neto, linea.moneda, 4)}</td>
        <td className={`text-right ${sapValueTone}`}>{fmtMoneySmart(linea.precio_sap ?? linea.precio_neto, linea.moneda, 4)}</td>
        <td className="text-right">{fmtMoney(linea.total)}</td>
        <td>
          <div className="space-y-1">
          {sapModeVisible ? (
            <div className="space-y-1" title={sapModeTitle}>
              <div className="inline-flex rounded-lg border border-gray-800 bg-gray-950/70 p-0.5">
                <button
                  type="button"
                  className={`rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] transition-colors ${
                    currentSapMode === 'unitario'
                      ? 'bg-cyan-500/20 text-cyan-200'
                      : 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
                  }`}
                  onMouseDown={blockRowToggle}
                  onClick={(event) => handleSapMode(event, 'unitario')}
                  disabled={mutSapMode.isPending || !sapModeEnabled || currentSapMode === 'unitario'}
                >
                  UNI
                </button>
                <button
                  type="button"
                  className={`rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] transition-colors ${
                    currentSapMode === 'display'
                      ? 'bg-emerald-500/20 text-emerald-200'
                      : sapModeEnabled
                        ? 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
                        : 'cursor-not-allowed text-gray-600'
                  }`}
                  onMouseDown={blockRowToggle}
                  onClick={(event) => handleSapMode(event, 'display')}
                  disabled={mutSapMode.isPending || !sapModeEnabled || currentSapMode === 'display'}
                >
                  DISP
                </button>
              </div>
              {!sapModeEnabled && (
                <div className="text-[10px] text-amber-400/80">
                  Sin factor maestra
                </div>
              )}
            </div>
          ) : (
            <span className="text-xs text-gray-600">-</span>
          )}
          {sapOriginLabel && (
            <div className={`text-[10px] font-semibold uppercase tracking-[0.08em] ${sapValueTone}`}>
              {sapOriginLabel}
            </div>
          )}
          </div>
        </td>
        <td>
          <span className={`text-xs font-medium ${badge.color}`}>{badge.label}</span>
        </td>
      </tr>

      {selected && (
        <tr className="bg-gray-900/70">
          <td colSpan={12} className="px-4 py-3">
            <div
              className="sticky left-0 space-y-3 pr-3"
              style={{ width: 'min(980px, max(320px, calc(100vw - 13rem)))', maxWidth: 'calc(100vw - 2rem)' }}
            >
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

              <div className="grid grid-cols-[auto_auto_1fr] items-end gap-x-3 gap-y-2 rounded-lg border border-gray-800 bg-gray-950/45 px-3 py-3">
                <label className="text-xs text-gray-400">
                  Cant SAP
                  <input
                    className="input mt-1 h-9 w-28 text-right font-mono"
                    inputMode="decimal"
                    value={cantidadSapDraft}
                    onChange={(event) => setCantidadSapDraft(event.target.value)}
                  />
                </label>
                <label className="text-xs text-gray-400">
                  Precio SAP
                  <input
                    className="input mt-1 h-9 w-32 text-right font-mono"
                    inputMode="decimal"
                    value={precioSapDraft}
                    onChange={(event) => setPrecioSapDraft(event.target.value)}
                  />
                </label>
                <div className="flex gap-2 justify-self-start">
                  <button
                    className="btn-primary h-9 px-3 text-xs"
                    onClick={handleSaveSapValues}
                    disabled={mutSapValues.isPending || mutResetSapValues.isPending}
                    title="Guardar valores SAP manuales"
                  >
                    <Save size={14} />
                    Guardar y aprender
                  </button>
                  <button
                    className="btn-secondary h-9 px-3 text-xs"
                    onClick={handleResetSapValues}
                    disabled={mutSapValues.isPending || mutResetSapValues.isPending}
                    title="Recalcular con la regla automatica"
                  >
                    <RotateCcw size={14} />
                    Recalcular
                  </button>
                </div>
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

function formatDateTime(value: string): string {
  if (!value) return ''
  const utcValue = value.endsWith('Z') || value.includes('+') ? value : value + 'Z'
  const parsed = new Date(utcValue)
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(parsed)
}

function getDocumentAccessKindLabel(kind?: string): string {
  switch ((kind || '').toLowerCase()) {
    case 'rut':
    case 'rut_normalizado':
    case 'rut_sin_guion':
      return 'RUT proveedor'
    case 'codigo_empresa':
    case 'codigo_empresa_digitos':
      return 'Codigo empresa'
    default:
      return ''
  }
}

function formatSapDraftValue(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) return ''
  return fmtNumberSmartCL(Number(value), 4)
}

function parseSapDraftValue(value: string): number | null {
  const parsed = parseDecimalCL(value)
  if (parsed == null || parsed < 0) return null
  return parsed
}

function getSapValuesOriginLabel(origin?: string | null): string {
  switch ((origin || '').toLowerCase()) {
    case 'manual':
      return 'Manual'
    case 'aprendizaje':
      return 'Aprendido'
    default:
      return ''
  }
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
