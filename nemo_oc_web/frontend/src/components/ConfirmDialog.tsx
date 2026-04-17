import { AlertCircle } from 'lucide-react'

export function ConfirmDialog({
  title,
  message,
  onConfirm,
  onCancel,
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  isDangerous = false,
}: {
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  confirmText?: string
  cancelText?: string
  isDangerous?: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-sm rounded-xl border border-gray-800 bg-gray-950 p-6 shadow-xl">
        <div className="mb-4 flex items-start gap-3">
          {isDangerous && <AlertCircle size={20} className="mt-0.5 text-red-400" />}
          <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
        </div>
        <p className="mb-6 text-sm text-gray-400">{message}</p>
        <div className="flex gap-3">
          <button
            className="flex-1 rounded-lg border border-gray-700 bg-gray-900 px-4 py-2 text-sm font-medium text-gray-300 transition-colors hover:bg-gray-800"
            onClick={onCancel}
          >
            {cancelText}
          </button>
          <button
            className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors ${
              isDangerous
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-accent hover:bg-accent/90'
            }`}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
