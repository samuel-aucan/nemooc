import { useMemo, useState } from 'react'
import { format, subDays } from 'date-fns'
import { Mail, Play, ShieldCheck, Wifi } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

import { getGlobalLogs, startSyncGmail, startSyncMp, testApi } from '../../api/sync'
import { useSyncSSE } from '../../hooks/useSyncSSE'

const today = () => format(new Date(), 'yyyy-MM-dd')
const ago = (days: number) => format(subDays(new Date(), days), 'yyyy-MM-dd')

type TestState = {
  kind: 'success' | 'error' | 'info'
  message: string
} | null

export default function ImportPage() {
  const [fechaDesde, setFechaDesde] = useState(ago(7))
  const [fechaHasta, setFechaHasta] = useState(today())
  const [cm, setCm] = useState(true)
  const [otras, setOtras] = useState(true)
  const [syncId, setSyncId] = useState<string | null>(null)
  const [syncPath, setSyncPath] = useState<'mercado-publico' | 'gmail'>('mercado-publico')
  const [testState, setTestState] = useState<TestState>(null)
  const [formError, setFormError] = useState('')

  const { logs, progress, status, reset } = useSyncSSE(syncId, syncPath)

  const { data: globalLogs = [] } = useQuery({
    queryKey: ['global-logs'],
    queryFn: getGlobalLogs,
    refetchInterval: 5000,
  })

  const running = status === 'running'
  const percentage = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0

  const progressTone = useMemo(() => {
    if (status === 'done') return 'text-emerald-300 bg-emerald-500/15'
    if (status === 'error') return 'text-red-300 bg-red-500/15'
    if (status === 'running') return 'text-blue-300 bg-blue-500/15'
    return 'text-gray-300 bg-gray-800'
  }, [status])

  const startMp = async () => {
    if (!cm && !otras) {
      setFormError('Debes seleccionar al menos un tipo de OC para sincronizar.')
      return
    }

    setFormError('')
    reset()
    setSyncPath('mercado-publico')
    const id = await startSyncMp(fechaDesde, fechaHasta, cm && !otras)
    setSyncId(id)
  }

  const startGmail = async () => {
    setFormError('')
    reset()
    setSyncPath('gmail')
    const id = await startSyncGmail()
    setSyncId(id)
  }

  const handleTest = async () => {
    setTestState({ kind: 'info', message: 'Probando conectividad y ticket...' })
    try {
      const response = await testApi()
      setTestState({
        kind: response.ok ? 'success' : 'error',
        message: response.message,
      })
    } catch (error: unknown) {
      setTestState({
        kind: 'error',
        message: error instanceof Error ? error.message : 'No fue posible probar la API.',
      })
    }
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Importaciones</h1>
          <p className="page-subtitle">
            Usa esta pantalla para traer OCs desde Mercado Publico o desde la casilla de automatizacion
            de privados. La prueba rapida verifica si la API esta respondiendo con la configuracion actual.
          </p>
        </div>
      </div>

      {formError && (
        <div className="rounded-xl border border-red-800/60 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {formError}
        </div>
      )}

      <section className="card">
        <div className="card-header">
          <Wifi size={15} className="text-accent" />
          Mercado Publico
        </div>
        <div className="card-body space-y-5">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_1.2fr_auto]">
            <div>
              <label className="label">Fecha desde</label>
              <input type="date" className="input" value={fechaDesde} onChange={(event) => setFechaDesde(event.target.value)} />
            </div>
            <div>
              <label className="label">Fecha hasta</label>
              <input type="date" className="input" value={fechaHasta} onChange={(event) => setFechaHasta(event.target.value)} />
            </div>
            <div className="flex flex-wrap items-end gap-2">
              {[
                ['Hoy', 0],
                ['7 dias', 7],
                ['30 dias', 30],
                ['90 dias', 90],
              ].map(([label, days]) => (
                <button
                  key={label}
                  className="btn-ghost px-3 py-2 text-xs"
                  onClick={() => {
                    setFechaDesde(ago(days as number))
                    setFechaHasta(today())
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-3 py-2 text-sm text-gray-300">
              <input type="checkbox" checked={cm} onChange={(event) => setCm(event.target.checked)} />
              Convenio Marco
            </label>
            <label className="flex items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-3 py-2 text-sm text-gray-300">
              <input type="checkbox" checked={otras} onChange={(event) => setOtras(event.target.checked)} />
              Otras compras
            </label>
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-950/60 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-sm font-medium text-gray-100">Salud de la API</div>
                <div className="mt-1 text-sm text-gray-500">
                  Si esta lenta o sin respuesta, veras el problema real antes de lanzar una descarga larga.
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button className="btn-secondary" onClick={handleTest} disabled={running}>
                  <ShieldCheck size={14} />
                  Prueba rapida API
                </button>
                <button className="btn-primary" onClick={startMp} disabled={running}>
                  <Play size={14} />
                  {running && syncPath === 'mercado-publico' ? 'Sincronizando...' : 'Descargar OCs'}
                </button>
              </div>
            </div>

            {testState && (
              <div
                className={`mt-4 rounded-xl border px-4 py-3 text-sm ${
                  testState.kind === 'success'
                    ? 'border-emerald-800/60 bg-emerald-950/25 text-emerald-200'
                    : testState.kind === 'error'
                      ? 'border-red-800/60 bg-red-950/25 text-red-200'
                      : 'border-gray-800 bg-gray-900 text-gray-300'
                }`}
              >
                {testState.message}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <Mail size={15} className="text-accent" />
          OCs privadas
        </div>
        <div className="card-body">
          <div className="section-note">
            Esta sincronizacion lee la casilla de automatizacion, toma correos reenviados con adjuntos PDF
            y clasifica el holding segun RUT, correo y formato del documento.
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-gray-400">
              Recomendado cuando ya esta configurado el reenvio automatico hacia Gmail.
            </div>
            <button className="btn-secondary" onClick={startGmail} disabled={running}>
              <Play size={14} />
              {running && syncPath === 'gmail' ? 'Procesando...' : 'Sincronizar Gmail'}
            </button>
          </div>
        </div>
      </section>

      {(status !== 'idle' || logs.length > 0) && (
        <section className="card">
          <div className="card-header flex items-center justify-between">
            <span>Actividad actual</span>
            <span className={`rounded-full px-3 py-1 text-xs font-medium ${progressTone}`}>{status}</span>
          </div>
          <div className="card-body space-y-4">
            {progress.total > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-300">
                    {progress.current} de {progress.total} OCs procesadas
                  </span>
                  <span className="text-gray-500">{percentage}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-gray-800">
                  <div className="h-full bg-accent transition-all" style={{ width: `${percentage}%` }} />
                </div>
              </div>
            )}

            <div className="rounded-2xl border border-gray-800 bg-gray-950/70 p-3">
              <div className="mb-3 text-xs uppercase tracking-[0.12em] text-gray-500">Bitacora</div>
              <div className="max-h-64 space-y-2 overflow-y-auto">
                {logs.map((entry, index) => (
                  <div key={`${entry.time}-${index}`} className="flex gap-3 rounded-lg border border-gray-800/70 bg-gray-950/70 px-3 py-2 text-sm">
                    <span className="w-20 shrink-0 text-xs text-gray-500">[{entry.time}]</span>
                    <span
                      className={
                        entry.level === 'success'
                          ? 'text-emerald-300'
                          : entry.level === 'error'
                            ? 'text-red-300'
                            : 'text-gray-300'
                      }
                    >
                      {entry.message}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {status === 'idle' && logs.length === 0 && globalLogs.length > 0 && (
        <section className="card">
          <div className="card-header">Actividad reciente</div>
          <div className="card-body">
            <div className="rounded-2xl border border-gray-800 bg-gray-950/70 p-3">
              <div className="max-h-52 space-y-2 overflow-y-auto">
                {[...globalLogs].reverse().slice(0, 12).map((entry, index) => (
                  <div key={`${entry.time}-${index}`} className="flex gap-3 rounded-lg border border-gray-800/70 bg-gray-950/70 px-3 py-2 text-sm">
                    <span className="w-20 shrink-0 text-xs text-gray-500">[{entry.time}]</span>
                    <span className={entry.message.includes('ERROR') ? 'text-red-300' : 'text-gray-300'}>
                      {entry.message}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
