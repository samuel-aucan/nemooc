import { useRef, useState, type ChangeEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye, EyeOff, FileText, Palette, Save, Upload } from 'lucide-react'

import {
  getCatalogStats,
  uploadCartera,
  uploadCorreos,
  uploadHomologacion,
  uploadLicitaciones,
  uploadMaestra,
  uploadRedsalud,
} from '../../api/catalogs'
import { getConfig, updateConfig, type AppConfig } from '../../api/config'
import api from '../../api/client'

type SectionId = 'mercado' | 'correo' | 'automatizacion' | 'catalogos' | 'apariencia' | 'ayuda'

const sections: Array<{ id: SectionId; label: string }> = [
  { id: 'mercado', label: 'Mercado Publico' },
  { id: 'correo', label: 'Correo' },
  { id: 'automatizacion', label: 'Automatizacion' },
  { id: 'catalogos', label: 'Catalogos' },
  { id: 'apariencia', label: 'Apariencia' },
  { id: 'ayuda', label: 'Ayuda' },
]

export default function ConfigPage() {
  const qc = useQueryClient()
  const [activeSection, setActiveSection] = useState<SectionId>('mercado')
  const [draft, setDraft] = useState<Partial<AppConfig>>({})
  const [saved, setSaved] = useState(false)
  const [showApiTicket, setShowApiTicket] = useState(false)
  const [showSmtpPassword, setShowSmtpPassword] = useState(false)
  const [pdfStatus, setPdfStatus] = useState('')

  const { data: cfg, isLoading } = useQuery({ queryKey: ['config'], queryFn: getConfig })
  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['catalog-stats'],
    queryFn: getCatalogStats,
  })

  const ACCENT_COLORS = [
    { id: 'blue', label: 'Azul', color: 'bg-blue-500' },
    { id: 'emerald', label: 'Verde', color: 'bg-emerald-500' },
    { id: 'violet', label: 'Violeta', color: 'bg-violet-500' },
    { id: 'rose', label: 'Rosa', color: 'bg-rose-500' },
    { id: 'amber', label: 'Ambar', color: 'bg-amber-500' },
    { id: 'cyan', label: 'Cyan', color: 'bg-cyan-500' },
  ]

  const saveMutation = useMutation({
    mutationFn: () => updateConfig(draft),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
      qc.invalidateQueries({ queryKey: ['config'] })
    },
  })

  const set = (key: string, value: unknown) => setDraft((previous) => ({ ...previous, [key]: value }))

  const get = (key: string) =>
    (key in draft ? draft[key as keyof AppConfig] : cfg?.[key as keyof AppConfig]) as
      | string
      | number
      | boolean
      | undefined

  if (isLoading) {
    return <div className="page-shell text-gray-500">Cargando configuracion...</div>
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Configuracion</h1>
          <p className="page-subtitle">
            Separa aqui las credenciales, automatizaciones y archivos maestros del sistema. Los catalogos por holding
            ahora se administran directamente en el modulo Holdings.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {saved && <span className="text-sm text-emerald-300">Cambios guardados</span>}
          <button className="btn-primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            <Save size={14} />
            {saveMutation.isPending ? 'Guardando...' : 'Guardar cambios'}
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-6 xl:flex-row">
        <aside className="xl:w-64 xl:flex-shrink-0">
          <div className="card">
            <div className="card-header">Secciones</div>
            <div className="card-body space-y-2">
              {sections.map((section) => (
                <button
                  key={section.id}
                    className={`w-full rounded-xl border px-3 py-2 text-left text-sm transition-colors ${
                      activeSection === section.id
                      ? 'border-accent text-accent'
                      : 'border-gray-800 bg-gray-950/50 text-gray-300 hover:border-gray-700 hover:bg-gray-900'
                    }`}
                    style={
                      activeSection === section.id
                        ? { backgroundColor: 'rgba(var(--accent-900), 0.28)' }
                        : undefined
                    }
                    onClick={() => setActiveSection(section.id)}
                  >
                  {section.label}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1 space-y-6">
          {activeSection === 'mercado' && (
            <section className="card">
              <div className="card-header">Mercado Publico</div>
              <div className="card-body grid grid-cols-1 gap-4 md:grid-cols-2">
                <Field label="Ticket API" helper="Se usa para consultar OCs en Mercado Publico.">
                  <div className="relative">
                    <input
                      className="input pr-10"
                      type={showApiTicket ? 'text' : 'password'}
                      value={(get('api_ticket') as string) || ''}
                      onChange={(event) => set('api_ticket', event.target.value)}
                    />
                    <button
                      className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-300"
                      onClick={() => setShowApiTicket((current) => !current)}
                      aria-label={showApiTicket ? 'Ocultar ticket API' : 'Mostrar ticket API'}
                    >
                      {showApiTicket ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </Field>

                <Field label="Codigo empresa" helper="Identificador de Nemo en la API.">
                  <input
                    className="input"
                    value={(get('codigo_empresa') as string) || ''}
                    onChange={(event) => set('codigo_empresa', event.target.value)}
                  />
                </Field>

                <Field label="RUT proveedor" helper="Se usa para cruces y validaciones.">
                  <input
                    className="input"
                    value={(get('rut_proveedor') as string) || ''}
                    onChange={(event) => set('rut_proveedor', event.target.value)}
                  />
                </Field>
              </div>
            </section>
          )}

          {activeSection === 'correo' && (
            <>
              <section className="card">
                <div className="card-header">Notificaciones SMTP</div>
                <div className="card-body grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field label="Servidor SMTP">
                    <input
                      className="input"
                      value={(get('smtp_host') as string) || ''}
                      onChange={(event) => set('smtp_host', event.target.value)}
                    />
                  </Field>
                  <Field label="Puerto">
                    <input
                      className="input"
                      type="number"
                      value={(get('smtp_port') as number) || 587}
                      onChange={(event) => set('smtp_port', Number(event.target.value))}
                    />
                  </Field>
                  <Field label="Usuario">
                    <input
                      className="input"
                      value={(get('smtp_user') as string) || ''}
                      onChange={(event) => set('smtp_user', event.target.value)}
                    />
                  </Field>
                  <Field label="Contrasena de aplicacion">
                    <div className="relative">
                      <input
                        className="input pr-10"
                        type={showSmtpPassword ? 'text' : 'password'}
                        value={(get('smtp_password') as string) || ''}
                        onChange={(event) => set('smtp_password', event.target.value)}
                      />
                      <button
                        className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-300"
                        onClick={() => setShowSmtpPassword((current) => !current)}
                        aria-label={showSmtpPassword ? 'Ocultar contrasena SMTP' : 'Mostrar contrasena SMTP'}
                      >
                        {showSmtpPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                  </Field>

                  <div className="md:col-span-2">
                    <label className="flex items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-4 py-3 text-sm text-gray-300">
                      <input
                        type="checkbox"
                        checked={(get('smtp_enabled') as boolean) || false}
                        onChange={(event) => set('smtp_enabled', event.target.checked)}
                      />
                      Enviar notificaciones por correo al importar
                    </label>
                  </div>
                </div>
              </section>

              <section className="card">
                <div className="card-header">Gmail IMAP para OCs privadas</div>
                <div className="card-body grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field label="Servidor IMAP">
                    <input
                      className="input"
                      value={(get('imap_server') as string) || ''}
                      onChange={(event) => set('imap_server', event.target.value)}
                    />
                  </Field>
                  <Field label="Puerto">
                    <input
                      className="input"
                      type="number"
                      value={(get('imap_port') as number) || 993}
                      onChange={(event) => set('imap_port', Number(event.target.value))}
                    />
                  </Field>
                  <Field label="Carpeta">
                    <input
                      className="input"
                      value={(get('imap_folder') as string) || ''}
                      onChange={(event) => set('imap_folder', event.target.value)}
                    />
                  </Field>
                  <Field label="Filtro por asunto" helper="Ejemplo: ORDEN DE COMPRA">
                    <input
                      className="input"
                      value={(get('imap_filter_subject') as string) || ''}
                      onChange={(event) => set('imap_filter_subject', event.target.value)}
                    />
                  </Field>
                </div>
              </section>
            </>
          )}

          {activeSection === 'automatizacion' && (
            <section className="card">
              <div className="card-header">Sincronizacion automatica</div>
              <div className="card-body space-y-4">
                <label className="flex items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-4 py-3 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={(get('auto_sync') as boolean) || false}
                    onChange={(event) => set('auto_sync', event.target.checked)}
                  />
                  Ejecutar sincronizacion automatica de Mercado Publico al iniciar el servidor
                </label>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field label="Dias hacia atras al iniciar">
                    <input
                      className="input"
                      type="number"
                      value={(get('auto_sync_days') as number) || 7}
                      onChange={(event) => set('auto_sync_days', Number(event.target.value))}
                    />
                  </Field>
                  <Field
                    label="Intervalo periodico en minutos"
                    helper="Usa 0 para dejar solo la sincronizacion manual."
                  >
                    <input
                      className="input"
                      type="number"
                      value={(get('auto_sync_interval') as number) || 15}
                      onChange={(event) => set('auto_sync_interval', Number(event.target.value))}
                    />
                  </Field>
                </div>
              </div>
            </section>
          )}

          {activeSection === 'catalogos' && (
            <>
              <section className="card">
                <div className="card-header">Catalogos generales</div>
                <div className="card-body space-y-2">
                  <CatalogRow label="Homologacion CM" count={stats?.homologacion_cm} uploadFn={uploadHomologacion} onDone={refetchStats} />
                  <CatalogRow label="Maestra SAP" count={stats?.homologacion_sap} uploadFn={uploadMaestra} onDone={refetchStats} />
                  <CatalogRow label="Cartera de clientes" count={stats?.cartera} uploadFn={uploadCartera} onDone={refetchStats} />
                  <CatalogRow label="Correos de vendedores" uploadFn={uploadCorreos} onDone={refetchStats} />
                  <CatalogRow label="Homo RedSalud legacy" count={stats?.redsalud} uploadFn={uploadRedsalud} onDone={refetchStats} />
                  <CatalogRow label="Licitaciones (lic.xlsx)" count={stats?.licitaciones} uploadFn={uploadLicitaciones} onDone={refetchStats} />
                </div>
              </section>

              <div className="section-note">
                Los catalogos por holding ya no se cargan aqui. Ahora se suben directamente dentro del modulo Holdings,
                junto a los RUTs y correos esperados de cada grupo.
              </div>
            </>
          )}

          {activeSection === 'apariencia' && (
            <section className="card">
              <div className="card-header">
                <Palette size={15} />
                Apariencia
              </div>
              <div className="card-body">
                <label className="label mb-3">Color principal</label>
                <div className="flex flex-wrap gap-3">
                  {ACCENT_COLORS.map((accent) => (
                    <button
                      key={accent.id}
                      onClick={() => set('color_theme', accent.id)}
                      className={`h-11 w-11 rounded-full ${accent.color} transition-all ring-offset-2 ring-offset-gray-950 ${
                        (get('color_theme') || 'blue') === accent.id
                          ? 'scale-110 ring-2 ring-white'
                          : 'opacity-70 hover:opacity-100'
                      }`}
                      title={accent.label}
                      aria-label={`Usar color ${accent.label}`}
                    />
                  ))}
                </div>
                <span className="helper">Afecta botones, indicadores y resaltados principales.</span>
              </div>
            </section>
          )}

          {activeSection === 'ayuda' && (
            <section className="card">
              <div className="card-header">
                <FileText size={15} />
                Ayuda y manuales
              </div>
              <div className="card-body flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="text-sm font-medium text-gray-100">Manual de instalacion y uso</div>
                  <div className="mt-1 text-sm text-gray-500">
                    Descarga el PDF de apoyo para nuevos usuarios o para soporte interno.
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      setPdfStatus('Generando PDF...')
                      try {
                        const response = await api.get('/config/manual', { responseType: 'blob' })
                        const url = URL.createObjectURL(response.data as Blob)
                        const link = document.createElement('a')
                        link.href = url
                        link.download = 'Manual_NemoOC.pdf'
                        link.click()
                        URL.revokeObjectURL(url)
                        setPdfStatus('Manual descargado')
                      } catch {
                        setPdfStatus('No fue posible generar el manual')
                      }
                      setTimeout(() => setPdfStatus(''), 4000)
                    }}
                  >
                    <FileText size={14} />
                    Descargar PDF
                  </button>
                  {pdfStatus && <span className="text-sm text-gray-400">{pdfStatus}</span>}
                </div>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

function CatalogRow({
  label,
  count,
  uploadFn,
  onDone,
}: {
  label: string
  count?: number
  uploadFn: (file: File) => Promise<{ imported: number; errors: string[] }>
  onDone: () => void
}) {
  const ref = useRef<HTMLInputElement>(null)
  const [status, setStatus] = useState('')

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setStatus('Cargando archivo...')
    try {
      const response = await uploadFn(file)
      setStatus(response.errors.length ? response.errors[0] : `${response.imported} registro(s) importados`)
      onDone()
    } catch (error: unknown) {
      setStatus(error instanceof Error ? error.message : 'Error al subir archivo')
    }

    setTimeout(() => setStatus(''), 5000)
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-4 md:flex-row md:items-center md:justify-between">
      <div>
        <div className="text-sm font-medium text-gray-100">{label}</div>
        {count !== undefined && <div className="mt-1 text-sm text-gray-500">{count.toLocaleString()} registro(s)</div>}
      </div>

      <div className="flex items-center gap-3">
        {status && <span className="text-sm text-gray-400">{status}</span>}
        <input ref={ref} type="file" accept=".xlsx" className="hidden" onChange={handleFile} />
        <button className="btn-secondary" onClick={() => ref.current?.click()}>
          <Upload size={14} />
          Subir .xlsx
        </button>
      </div>
    </div>
  )
}

function Field({
  label,
  helper,
  children,
}: {
  label: string
  helper?: string
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {helper && <span className="helper">{helper}</span>}
    </label>
  )
}
