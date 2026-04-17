import { useState } from 'react'
import { AlertCircle, X } from 'lucide-react'

export interface ConfirmDialogProps {
  isOpen: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  isDangerous?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  isDangerous = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-xl border border-gray-800 bg-gray-950 shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-800 px-6 py-4">
          <div className="flex items-center gap-3">
            {isDangerous && <AlertCircle size={18} className="text-red-400" />}
            <h2 className="text-base font-semibold text-gray-100">{title}</h2>
          </div>
          <button
            onClick={onCancel}
            className="text-gray-500 transition-colors hover:text-gray-300"
            aria-label="Cerrar diálogo"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-4">
          <p className="text-sm text-gray-300">{message}</p>
        </div>

        <div className="flex gap-2 border-t border-gray-800 px-6 py-4">
          <button className="flex-1 btn-ghost rounded-lg" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            className={`flex-1 rounded-lg ${isDangerous ? 'btn-danger' : 'btn-primary'}`}
            onClick={() => {
              onConfirm()
              onCancel()
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

export function useConfirmDialog() {
  const [state, setState] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmLabel: 'Confirmar',
    cancelLabel: 'Cancelar',
    isDangerous: false,
    onConfirm: () => {},
  })

  const confirm = (config: {
    title: string
    message: string
    confirmLabel?: string
    cancelLabel?: string
    isDangerous?: boolean
  }) => {
    return new Promise<boolean>((resolve) => {
      setState({
        isOpen: true,
        title: config.title,
        message: config.message,
        confirmLabel: config.confirmLabel || 'Confirmar',
        cancelLabel: config.cancelLabel || 'Cancelar',
        isDangerous: config.isDangerous || false,
        onConfirm: () => resolve(true),
      })
    })
  }

  const close = () => {
    setState((prev) => ({ ...prev, isOpen: false }))
  }

  const Dialog = () => (
    <ConfirmDialog
      isOpen={state.isOpen}
      title={state.title}
      message={state.message}
      confirmLabel={state.confirmLabel}
      cancelLabel={state.cancelLabel}
      isDangerous={state.isDangerous}
      onConfirm={state.onConfirm}
      onCancel={close}
    />
  )

  return { confirm, Dialog, close }
}
