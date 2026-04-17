import { useEffect, useState, type DragEvent } from 'react'
import { Eye, EyeOff, GripVertical, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getConfig, updateConfig } from '../../api/config'

interface Props {
  onClose: () => void
}

export const OC_LIST_COLUMNS_AVAILABLE = [
  { id: 'codigo_oc', name: 'Codigo OC' },
  { id: 'tipo_oc', name: 'Tipo' },
  { id: 'holding', name: 'Holding' },
  { id: 'estado_mp', name: 'Estado MP' },
  { id: 'estado_interno', name: 'Estado interno' },
  { id: 'fecha_envio', name: 'Fecha envio' },
  { id: 'fecha_ingreso', name: 'Ingreso SAP' },
  { id: 'nombre_organismo', name: 'Comprador' },
  { id: 'cliente_sap_sugerido', name: 'Cliente SAP' },
  { id: 'cartera', name: 'Cartera' },
  { id: 'total', name: 'Total' },
  { id: 'cantidad_lineas', name: 'Lineas' },
] as const

export const DEFAULT_OC_LIST_COLUMNS = OC_LIST_COLUMNS_AVAILABLE.map((column) => column.id)

export type OcListColumnId = (typeof OC_LIST_COLUMNS_AVAILABLE)[number]['id']

export default function OcListColumnConfigModal({ onClose }: Props) {
  const qc = useQueryClient()
  const { data: cfg, isLoading } = useQuery({ queryKey: ['config'], queryFn: getConfig })

  const [columns, setColumns] = useState<string[]>([])
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null)
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null)

  useEffect(() => {
    if (cfg?.oc_list_columns?.length) {
      setColumns(cfg.oc_list_columns)
      return
    }
    if (cfg) {
      setColumns([...DEFAULT_OC_LIST_COLUMNS])
    }
  }, [cfg])

  const saveMutation = useMutation({
    mutationFn: () => updateConfig({ oc_list_columns: columns }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] })
      onClose()
    },
  })

  if (isLoading) return null

  const toggleColumn = (id: string) => {
    if (columns.includes(id)) {
      setColumns(columns.filter((column) => column !== id))
      return
    }
    setColumns([...columns, id])
  }

  const handleDragOver = (event: DragEvent, idx: number) => {
    event.preventDefault()
    if (draggedIdx === null || draggedIdx === idx) return
    setDragOverIdx(idx)
  }

  const handleDrop = (idx: number) => {
    if (draggedIdx === null || draggedIdx === idx) {
      setDraggedIdx(null)
      setDragOverIdx(null)
      return
    }

    const next = [...columns]
    const [dragged] = next.splice(draggedIdx, 1)
    next.splice(idx, 0, dragged)
    setColumns(next)
    setDraggedIdx(null)
    setDragOverIdx(null)
  }

  const selectedColumns = columns
    .map((id) => OC_LIST_COLUMNS_AVAILABLE.find((column) => column.id === id))
    .filter(Boolean) as Array<{ id: string; name: string }>

  const hiddenColumns = OC_LIST_COLUMNS_AVAILABLE.filter((column) => !columns.includes(column.id))

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Configurar columnas de la bandeja"
        className="flex w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-gray-800 bg-gray-950 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-800 bg-gray-900/90 px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-gray-100">Configurar columnas de la bandeja</h2>
            <p className="mt-1 text-sm text-gray-500">
              Define el orden y las columnas visibles de la lista principal.
            </p>
          </div>
          <button className="btn-ghost px-3" onClick={onClose} aria-label="Cerrar configuracion de columnas de bandeja">
            <X size={16} />
          </button>
        </div>

        <div className="grid gap-5 p-5 lg:grid-cols-[1.2fr_0.9fr]">
          <div className="space-y-3">
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-500">
              Columnas activas
            </div>

            {selectedColumns.length === 0 && (
              <div className="rounded-xl border border-red-800/60 bg-red-950/25 px-4 py-3 text-sm text-red-200">
                No hay columnas activas. La bandeja quedaria vacia.
              </div>
            )}

            <div className="space-y-2">
              {selectedColumns.map((column, index) => (
                <div
                  key={column.id}
                  draggable
                  onDragStart={() => setDraggedIdx(index)}
                  onDragOver={(event) => handleDragOver(event, index)}
                  onDrop={() => handleDrop(index)}
                  onDragEnd={() => {
                    setDraggedIdx(null)
                    setDragOverIdx(null)
                  }}
                  className={`flex items-center justify-between rounded-xl border px-3 py-3 transition-all ${
                    dragOverIdx === index && draggedIdx !== index
                      ? 'border-accent'
                      : draggedIdx === index
                        ? 'border-gray-700 opacity-50'
                        : 'border-gray-800 bg-gray-900/70'
                  }`}
                  style={
                    dragOverIdx === index && draggedIdx !== index
                      ? { backgroundColor: 'rgba(var(--accent-900), 0.26)' }
                      : undefined
                  }
                >
                  <div className="flex items-center gap-3">
                    <GripVertical size={15} className="text-gray-500" />
                    <button
                      className="text-blue-300 transition-colors hover:text-blue-200"
                      onClick={() => toggleColumn(column.id)}
                      aria-label={`Ocultar columna ${column.name}`}
                    >
                      <Eye size={15} />
                    </button>
                    <div>
                      <div className="text-sm font-medium text-gray-100">{column.name}</div>
                      <div className="text-xs text-gray-500">Posicion {index + 1}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-500">
              Columnas ocultas
            </div>

            <div className="space-y-2">
              {hiddenColumns.map((column) => (
                <div key={column.id} className="flex items-center gap-3 rounded-xl border border-gray-800 bg-gray-900/40 px-3 py-3">
                  <button
                    className="text-gray-400 transition-colors hover:text-gray-200"
                    onClick={() => toggleColumn(column.id)}
                    aria-label={`Mostrar columna ${column.name}`}
                  >
                    <EyeOff size={15} />
                  </button>
                  <div>
                    <div className="text-sm text-gray-300">{column.name}</div>
                    <div className="text-xs text-gray-500">Disponible para agregar</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-900/50 px-4 py-3 text-sm text-gray-400">
              Este formato se guarda localmente en la configuracion de la aplicacion y afecta solo la bandeja principal.
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-gray-800 bg-gray-900/90 px-5 py-4">
          <span className="text-sm text-gray-500">
            {columns.length} de {OC_LIST_COLUMNS_AVAILABLE.length} columna(s) activas
          </span>
          <div className="flex items-center gap-3">
            <button className="btn-ghost" onClick={onClose}>
              Cancelar
            </button>
            <button className="btn-primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Guardando...' : 'Guardar formato'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
