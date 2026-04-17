import { useState } from 'react'

export function useConfirmDialog() {
  const [dialog, setDialog] = useState<{
    title: string
    message: string
    onConfirm: () => void | Promise<void>
    confirmText?: string
    isDangerous?: boolean
  } | null>(null)

  const confirm = (config: {
    title: string
    message: string
    onConfirm: () => void | Promise<void>
    confirmText?: string
    isDangerous?: boolean
  }) => {
    setDialog(config)
  }

  const handleConfirm = async () => {
    if (dialog?.onConfirm) {
      await dialog.onConfirm()
    }
    setDialog(null)
  }

  const handleCancel = () => {
    setDialog(null)
  }

  return { dialog, confirm, handleConfirm, handleCancel }
}
