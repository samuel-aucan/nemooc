import { useEffect, useRef, useState } from 'react'

export interface SyncLog {
  time: string
  message: string
  level: 'info' | 'success' | 'error'
}

export type SyncStatus = 'idle' | 'running' | 'done' | 'error' | 'reconnecting'

export function useSyncSSE(syncId: string | null, path: 'mercado-publico' | 'gmail' | 'mp-estados-ligero') {
  const [logs, setLogs] = useState<SyncLog[]>([])
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [status, setStatus] = useState<SyncStatus>('idle')
  const [retryCount, setRetryCount] = useState(0)
  const esRef = useRef<EventSource | null>(null)
  const retryTimeoutRef = useRef<number | null>(null)
  const maxRetries = 5
  const baseDelay = 1000 // 1s

  useEffect(() => {
    if (!syncId) return
    if (retryCount === 0) {
      setLogs([])
      setProgress({ current: 0, total: 0 })
    }
    setStatus('running')

    const addLog = (message: string, level: SyncLog['level']) => {
      const time = new Date().toLocaleTimeString('es-CL', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
      setLogs((previous) => [...previous, { time, message, level }])
    }

    const connectSSE = () => {
      const es = new EventSource(`/api/sync/${path}/${syncId}/progress`)
      esRef.current = es

      es.addEventListener('log', (event) => {
        const data = JSON.parse(event.data)
        addLog(data.message, 'info')
      })

      es.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data)
        setProgress({ current: data.current, total: data.total })
      })

      es.addEventListener('done', (event) => {
        const data = JSON.parse(event.data)
        addLog(data.message, 'success')
        setStatus('done')
        es.close()
        setRetryCount(0)
      })

      es.addEventListener('error', () => {
        es.close()
        if (retryCount < maxRetries) {
          // Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 30s)
          const delay = Math.min(baseDelay * Math.pow(2, retryCount), 30000)
          addLog(`Reconectando en ${Math.round(delay / 1000)}s... (intento ${retryCount + 1}/${maxRetries})`, 'error')
          setStatus('reconnecting')
          retryTimeoutRef.current = window.setTimeout(() => {
            setRetryCount((prev) => prev + 1)
          }, delay)
        } else {
          addLog(`Error de conexión. No se pudo reconectar después de ${maxRetries} intentos.`, 'error')
          setStatus('error')
          setRetryCount(0)
        }
      })
    }

    connectSSE()

    return () => {
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current)
      esRef.current?.close()
    }
  }, [path, syncId, retryCount, baseDelay, maxRetries])

  const reset = () => {
    esRef.current?.close()
    setLogs([])
    setProgress({ current: 0, total: 0 })
    setStatus('idle')
  }

  return { logs, progress, status, reset }
}
