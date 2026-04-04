import { useEffect, useRef, useState } from 'react'

export interface SyncLog {
  time: string
  message: string
  level: 'info' | 'success' | 'error'
}

export type SyncStatus = 'idle' | 'running' | 'done' | 'error'

export function useSyncSSE(syncId: string | null, path: 'mercado-publico' | 'gmail') {
  const [logs, setLogs] = useState<SyncLog[]>([])
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [status, setStatus] = useState<SyncStatus>('idle')
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!syncId) return

    setLogs([])
    setProgress({ current: 0, total: 0 })
    setStatus('running')

    const es = new EventSource(`/api/sync/${path}/${syncId}/progress`)
    esRef.current = es

    const addLog = (message: string, level: SyncLog['level']) => {
      const time = new Date().toLocaleTimeString('es-CL', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
      setLogs((previous) => [...previous, { time, message, level }])
    }

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
    })

    es.addEventListener('error', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data)
        addLog(data.message, 'error')
      } catch {
        addLog('Error de conexion con el canal de progreso.', 'error')
      }
      setStatus('error')
      es.close()
    })

    return () => {
      es.close()
    }
  }, [path, syncId])

  const reset = () => {
    esRef.current?.close()
    setLogs([])
    setProgress({ current: 0, total: 0 })
    setStatus('idle')
  }

  return { logs, progress, status, reset }
}
