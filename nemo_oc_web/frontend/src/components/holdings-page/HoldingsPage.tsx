import { useDeferredValue, useEffect, useMemo, useRef, useState, type ChangeEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Building2,
  Globe,
  Plus,
  Search,
  Save,
  Settings2,
  ShieldAlert,
  Trash2,
  Upload,
} from 'lucide-react'

import { searchCartera, type CarteraSearchResult, uploadPrivateHoldingCatalog } from '../../api/catalogs'
import {
  createHolding,
  createHoldingRule,
  deleteHoldingRule,
  deleteHoldingRut,
  getHoldings,
  type Holding,
  type HoldingPayload,
  type HoldingRule,
  type HoldingRulePayload,
  type HoldingRutPayload,
  updateHolding,
  updateHoldingRule,
  upsertHoldingRut,
} from '../../api/holdings'

type MessageState =
  | {
      kind: 'success' | 'error'
      text: string
    }
  | null

const EMPTY_HOLDING = {
  id: '',
  nombre: '',
  prefijo: '',
  parser_type: '',
  homo_file: '',
  activo: true,
}

const EMPTY_RUT = {
  rut: '',
  rut_display: '',
  nombre_sucursal: '',
}

const EMPTY_DOMAIN = {
  domain: '',
}

const EMPTY_RULE = {
  rule_type: 'pdf_contains',
  rule_value: '',
  prioridad: 100,
  activo: true,
  notas: '',
}

const ADVANCED_RULE_TYPES = [
  { value: 'pdf_contains', label: 'Texto dentro del PDF' },
  { value: 'subject_contains', label: 'Texto en el asunto' },
  { value: 'from_contains', label: 'Texto en el remitente' },
]

export default function HoldingsPage() {
  const qc = useQueryClient()
  const { data: holdings = [], isLoading } = useQuery({
    queryKey: ['holdings'],
    queryFn: getHoldings,
  })

  const [message, setMessage] = useState<MessageState>(null)
  const [createDraft, setCreateDraft] = useState(EMPTY_HOLDING)

  const createMutation = useMutation({
    mutationFn: createHolding,
    onSuccess: () => {
      setMessage({ kind: 'success', text: 'Holding creado correctamente.' })
      setCreateDraft(EMPTY_HOLDING)
      qc.invalidateQueries({ queryKey: ['holdings'] })
      qc.invalidateQueries({ queryKey: ['private-holdings'] })
    },
    onError: (error: Error) => {
      setMessage({ kind: 'error', text: error.message })
    },
  })

  const totalCatalogItems = holdings.reduce((total, holding) => total + holding.catalog_count, 0)
  const totalRuts = holdings.reduce((total, holding) => total + holding.ruts.length, 0)

  const submitCreate = () => {
    createMutation.mutate({
      id: createDraft.id,
      nombre: createDraft.nombre,
      prefijo: createDraft.prefijo,
      parser_type: createDraft.parser_type || createDraft.id,
      homo_file: createDraft.homo_file,
      activo: createDraft.activo,
    })
  }

  if (isLoading) {
    return <div className="page-shell text-gray-500">Cargando holdings...</div>
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Holdings</h1>
          <p className="page-subtitle">
            Aqui se concentra la configuracion de privados: identidad del holding, RUTs compradores, correos esperados,
            catalogo del holding y ayudas avanzadas de reconocimiento.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SummaryPill label="Holdings" value={holdings.length} />
          <SummaryPill label="RUTs cargados" value={totalRuts} />
          <SummaryPill label="Items catalogados" value={totalCatalogItems} />
        </div>
      </div>

      <div className="section-note">
        En la mayoria de los casos basta con cuatro cosas: crear el holding, cargar sus RUTs compradores,
        registrar los correos o dominios esperados y subir su catalogo Excel.
      </div>

      {message && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm ${
            message.kind === 'success'
              ? 'border-emerald-800/60 bg-emerald-950/25 text-emerald-200'
              : 'border-red-800/60 bg-red-950/25 text-red-200'
          }`}
        >
          {message.text}
        </div>
      )}

      <section className="card">
        <div className="card-header">
          <Plus size={15} />
          Nuevo holding
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            <Field label="ID interno" helper="Ejemplo: banmedica">
              <input
                className="input"
                placeholder="banmedica"
                value={createDraft.id}
                onChange={(event) => setCreateDraft((previous) => ({ ...previous, id: event.target.value }))}
              />
            </Field>
            <Field label="Nombre visible">
              <input
                className="input"
                placeholder="Banmedica"
                value={createDraft.nombre}
                onChange={(event) => setCreateDraft((previous) => ({ ...previous, nombre: event.target.value }))}
              />
            </Field>
            <Field label="Prefijo OC" helper="Ejemplo: BM">
              <input
                className="input"
                placeholder="BM"
                value={createDraft.prefijo}
                onChange={(event) => setCreateDraft((previous) => ({ ...previous, prefijo: event.target.value }))}
              />
            </Field>
            <div className="flex items-end justify-between gap-3">
              <label className="flex items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-3 py-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={createDraft.activo}
                  onChange={(event) => setCreateDraft((previous) => ({ ...previous, activo: event.target.checked }))}
                />
                Activo
              </label>
              <button className="btn-primary" onClick={submitCreate} disabled={createMutation.isPending}>
                <Plus size={14} />
                Crear
              </button>
            </div>
          </div>

          <details className="rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3">
            <summary className="cursor-pointer text-sm text-gray-300">Opciones avanzadas del holding</summary>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              <Field label="Formato PDF interno" helper="Si lo dejas vacio, se usa el mismo ID interno.">
                <input
                  className="input"
                  value={createDraft.parser_type}
                  onChange={(event) => setCreateDraft((previous) => ({ ...previous, parser_type: event.target.value }))}
                />
              </Field>
              <Field label="Nombre de archivo catalogo" helper="Ejemplo: HOMO_BANMEDICA.xlsx">
                <input
                  className="input"
                  value={createDraft.homo_file}
                  onChange={(event) => setCreateDraft((previous) => ({ ...previous, homo_file: event.target.value }))}
                />
              </Field>
            </div>
          </details>
        </div>
      </section>

      <div className="space-y-5">
        {holdings.map((holding) => (
          <HoldingCard key={holding.id} holding={holding} onMessage={setMessage} />
        ))}

        {holdings.length === 0 && (
          <div className="card">
            <div className="card-body text-sm text-gray-500">Todavia no hay holdings creados.</div>
          </div>
        )}
      </div>
    </div>
  )
}

function HoldingCard({
  holding,
  onMessage,
}: {
  holding: Holding
  onMessage: (message: MessageState) => void
}) {
  const qc = useQueryClient()
  const catalogInputRef = useRef<HTMLInputElement>(null)

  const [draft, setDraft] = useState<HoldingPayload>({
    nombre: holding.nombre,
    prefijo: holding.prefijo,
    parser_type: holding.parser_type,
    homo_file: holding.homo_file,
    activo: holding.activo,
  })
  const [rutDraft, setRutDraft] = useState<HoldingRutPayload>(EMPTY_RUT)
  const [carteraSearch, setCarteraSearch] = useState('')
  const [showCarteraResults, setShowCarteraResults] = useState(false)
  const [domainDraft, setDomainDraft] = useState(EMPTY_DOMAIN)
  const [newRule, setNewRule] = useState<HoldingRulePayload>(EMPTY_RULE)
  const [catalogStatus, setCatalogStatus] = useState('')
  const deferredCarteraSearch = useDeferredValue(carteraSearch.trim())

  const domainRules = useMemo(
    () => holding.rules.filter((rule) => rule.rule_type === 'email_domain'),
    [holding.rules]
  )
  const advancedRules = useMemo(
    () => holding.rules.filter((rule) => rule.rule_type !== 'email_domain'),
    [holding.rules]
  )

  const { data: carteraMatches = [], isFetching: searchingCartera } = useQuery({
    queryKey: ['cartera-search', deferredCarteraSearch],
    queryFn: () => searchCartera(deferredCarteraSearch),
    enabled: showCarteraResults && deferredCarteraSearch.length >= 2,
    staleTime: 60_000,
  })

  useEffect(() => {
    setDraft({
      nombre: holding.nombre,
      prefijo: holding.prefijo,
      parser_type: holding.parser_type,
      homo_file: holding.homo_file,
      activo: holding.activo,
    })
  }, [holding])

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['holdings'] })
    qc.invalidateQueries({ queryKey: ['private-holdings'] })
  }

  const saveMutation = useMutation({
    mutationFn: (payload: HoldingPayload) => updateHolding(holding.id, payload),
    onSuccess: () => {
      onMessage({ kind: 'success', text: `Holding ${holding.nombre} actualizado.` })
      invalidate()
    },
    onError: (error: Error) => onMessage({ kind: 'error', text: error.message }),
  })

  const rutMutation = useMutation({
    mutationFn: (payload: HoldingRutPayload) => upsertHoldingRut(holding.id, payload),
    onSuccess: () => {
      onMessage({ kind: 'success', text: `RUT agregado en ${holding.nombre}.` })
      setRutDraft(EMPTY_RUT)
      setCarteraSearch('')
      setShowCarteraResults(false)
      invalidate()
    },
    onError: (error: Error) => onMessage({ kind: 'error', text: error.message }),
  })

  const domainMutation = useMutation({
    mutationFn: (domain: string) =>
      createHoldingRule(holding.id, {
        rule_type: 'email_domain',
        rule_value: domain,
        prioridad: 50,
        activo: true,
        notas: 'Creada desde modo simple',
      }),
    onSuccess: () => {
      onMessage({ kind: 'success', text: `Correo o dominio agregado en ${holding.nombre}.` })
      setDomainDraft(EMPTY_DOMAIN)
      invalidate()
    },
    onError: (error: Error) => onMessage({ kind: 'error', text: error.message }),
  })

  const createRuleMutation = useMutation({
    mutationFn: (payload: HoldingRulePayload) => createHoldingRule(holding.id, payload),
    onSuccess: () => {
      onMessage({ kind: 'success', text: `Ayuda avanzada agregada en ${holding.nombre}.` })
      setNewRule(EMPTY_RULE)
      invalidate()
    },
    onError: (error: Error) => onMessage({ kind: 'error', text: error.message }),
  })

  const handleCatalogUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setCatalogStatus('Cargando catalogo...')
    try {
      const response = await uploadPrivateHoldingCatalog(holding.id, file)
      setCatalogStatus(
        response.errors.length > 0 ? response.errors[0] : `${response.imported} item(s) importados`
      )
      invalidate()
    } catch (error: unknown) {
      setCatalogStatus(error instanceof Error ? error.message : 'No fue posible subir el catalogo')
    }

    setTimeout(() => setCatalogStatus(''), 5000)
  }

  const applyCarteraMatch = (cliente: CarteraSearchResult) => {
    setRutDraft({
      rut: cliente.rut || '',
      rut_display: cliente.razon || '',
      nombre_sucursal: cliente.comuna || '',
    })
    setCarteraSearch(cliente.razon || cliente.rut || cliente.cod_cliente)
    setShowCarteraResults(false)
  }

  return (
    <section className="card">
      <div className="card-header flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-gray-950/70 p-2 text-gray-300">
            <Building2 size={16} />
          </span>
          <div>
            <div className="text-sm font-semibold text-gray-100">{holding.nombre}</div>
            <div className="text-xs text-gray-500">
              {holding.id} | Prefijo {holding.prefijo}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <SummaryPill label="Catalogo" value={holding.catalog_count} />
          <SummaryPill label="RUTs" value={holding.ruts.length} />
          <SummaryPill label="Correos" value={domainRules.length} />
        </div>
      </div>

      <div className="card-body space-y-6">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <Field label="Nombre visible">
            <input
              className="input"
              value={draft.nombre}
              onChange={(event) => setDraft((previous) => ({ ...previous, nombre: event.target.value }))}
            />
          </Field>
          <Field label="Prefijo OC">
            <input
              className="input"
              value={draft.prefijo}
              onChange={(event) => setDraft((previous) => ({ ...previous, prefijo: event.target.value }))}
            />
          </Field>
          <Field label="Archivo catalogo sugerido">
            <input
              className="input"
              value={draft.homo_file || ''}
              onChange={(event) => setDraft((previous) => ({ ...previous, homo_file: event.target.value }))}
            />
          </Field>
          <div className="flex items-end justify-between gap-3">
            <label className="flex items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-3 py-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={draft.activo}
                onChange={(event) => setDraft((previous) => ({ ...previous, activo: event.target.checked }))}
              />
              Activo
            </label>
            <button className="btn-primary" onClick={() => saveMutation.mutate(draft)} disabled={saveMutation.isPending}>
              <Save size={14} />
              Guardar
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-800 bg-gray-950/50 px-4 py-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm font-medium text-gray-100">Catalogo del holding</div>
              <div className="mt-1 text-sm text-gray-500">
                Sube aqui el Excel de homologacion y precios de este holding.
              </div>
            </div>
            <div className="flex items-center gap-3">
              {catalogStatus && <span className="text-sm text-gray-400">{catalogStatus}</span>}
              <input
                ref={catalogInputRef}
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={handleCatalogUpload}
              />
              <button className="btn-secondary" onClick={() => catalogInputRef.current?.click()}>
                <Upload size={14} />
                {holding.homo_file || 'Subir catalogo'}
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div className="rounded-2xl border border-gray-800 bg-gray-950/50 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-100">RUTs compradores</h3>
                <p className="mt-1 text-sm text-gray-500">La senal principal para identificar el holding.</p>
              </div>
            </div>

            <div className="space-y-2">
              {holding.ruts.map((rut) => (
                <div key={rut.rut_norm} className="flex items-center justify-between gap-3 rounded-xl border border-gray-800 px-3 py-3">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-100">{rut.rut_display || rut.rut_norm}</div>
                    <div className="text-xs text-gray-500">
                      {rut.rut_norm}
                      {rut.nombre_sucursal ? ` | ${rut.nombre_sucursal}` : ''}
                    </div>
                  </div>
                  <button
                    className="btn-secondary px-3 py-1.5 text-xs"
                    onClick={() => {
                      deleteHoldingRut(holding.id, rut.rut_norm)
                        .then(() => {
                          onMessage({ kind: 'success', text: `RUT eliminado de ${holding.nombre}.` })
                          invalidate()
                        })
                        .catch((error: Error) => onMessage({ kind: 'error', text: error.message }))
                    }}
                  >
                    <Trash2 size={12} />
                    Quitar
                  </button>
                </div>
              ))}

              {holding.ruts.length === 0 && (
                <div className="rounded-xl border border-amber-800/40 bg-amber-950/20 px-3 py-3 text-sm text-amber-200">
                  Este holding aun no tiene RUTs compradores. Sin eso la deteccion sera mucho mas fragil.
                </div>
              )}
            </div>

            <div className="mt-4 border-t border-gray-800 pt-4">
              <Field
                label="Buscar en cartera maestra"
                helper="Busca por razon social, codigo cliente o RUT. Al seleccionar una sugerencia se completan los campos de abajo."
              >
                <div className="relative">
                  <Search size={15} className="pointer-events-none absolute left-3 top-2.5 text-gray-500" />
                  <input
                    className="input pl-9"
                    placeholder="Ejemplo: Clinica Santa Maria, CN..., 90.753.000-0"
                    value={carteraSearch}
                    onChange={(event) => {
                      setCarteraSearch(event.target.value)
                      setShowCarteraResults(true)
                    }}
                    onFocus={() => setShowCarteraResults(true)}
                    onBlur={() => setTimeout(() => setShowCarteraResults(false), 150)}
                  />

                  {showCarteraResults && deferredCarteraSearch.length >= 2 && (
                    <div className="absolute z-20 mt-2 max-h-64 w-full overflow-y-auto rounded-xl border border-gray-700 bg-gray-950 shadow-2xl">
                      {searchingCartera ? (
                        <div className="px-3 py-2 text-sm text-gray-400">Buscando en cartera...</div>
                      ) : carteraMatches.length > 0 ? (
                        carteraMatches.map((cliente) => (
                          <button
                            key={`${cliente.cod_cliente}-${cliente.rut}`}
                            type="button"
                            className="flex w-full flex-col gap-1 border-b border-gray-800 px-3 py-3 text-left transition-colors last:border-b-0 hover:bg-gray-900"
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => applyCarteraMatch(cliente)}
                          >
                            <span className="text-sm font-medium text-gray-100">{cliente.razon || cliente.cod_cliente}</span>
                            <span className="text-xs text-gray-500">
                              {cliente.rut || 'Sin RUT'} | {cliente.cod_cliente}
                              {cliente.cartera ? ` | Cartera ${cliente.cartera}` : ''}
                            </span>
                            <span className="text-xs text-gray-500">
                              {[cliente.comuna, cliente.region_nombre, cliente.vendedor].filter(Boolean).join(' | ') || 'Sin detalle adicional'}
                            </span>
                          </button>
                        ))
                      ) : (
                        <div className="px-3 py-2 text-sm text-gray-400">No se encontraron clientes en cartera.</div>
                      )}
                    </div>
                  )}
                </div>
              </Field>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-2 border-t border-gray-800 pt-4 md:grid-cols-3">
              <Field label="RUT">
                <input
                  className="input"
                  value={rutDraft.rut || ''}
                  onChange={(event) => setRutDraft((previous) => ({ ...previous, rut: event.target.value }))}
                />
              </Field>
              <Field label="Nombre visible">
                <input
                  className="input"
                  value={rutDraft.rut_display || ''}
                  onChange={(event) => setRutDraft((previous) => ({ ...previous, rut_display: event.target.value }))}
                />
              </Field>
              <Field label="Sucursal">
                <div className="flex gap-2">
                  <input
                    className="input"
                    value={rutDraft.nombre_sucursal || ''}
                    onChange={(event) => setRutDraft((previous) => ({ ...previous, nombre_sucursal: event.target.value }))}
                  />
                  <button className="btn-secondary shrink-0 px-3 py-2 text-xs" onClick={() => rutMutation.mutate(rutDraft)} disabled={rutMutation.isPending}>
                    <Plus size={12} />
                    Agregar
                  </button>
                </div>
              </Field>
            </div>
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-950/50 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe size={15} className="text-gray-400" />
                <div>
                  <h3 className="text-sm font-medium text-gray-100">Correos esperados</h3>
                  <p className="mt-1 text-sm text-gray-500">Ayudan cuando el correo original viene reenviado.</p>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              {domainRules.map((rule) => (
                <div key={rule.id} className="flex items-center justify-between gap-3 rounded-xl border border-gray-800 px-3 py-3">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-100">{rule.rule_value}</div>
                    <div className="text-xs text-gray-500">Dominio o pista de correo reenviado</div>
                  </div>
                  <button
                    className="btn-secondary px-3 py-1.5 text-xs"
                    onClick={() => {
                      deleteHoldingRule(holding.id, rule.id)
                        .then(() => {
                          onMessage({ kind: 'success', text: `Dominio eliminado de ${holding.nombre}.` })
                          invalidate()
                        })
                        .catch((error: Error) => onMessage({ kind: 'error', text: error.message }))
                    }}
                  >
                    <Trash2 size={12} />
                    Quitar
                  </button>
                </div>
              ))}

              {domainRules.length === 0 && (
                <div className="rounded-xl border border-gray-800 bg-gray-950/60 px-3 py-3 text-sm text-gray-400">
                  Este holding no tiene correos esperados. El sistema seguira intentando reconocerlo por RUT y contenido del PDF.
                </div>
              )}
            </div>

            <div className="mt-4 border-t border-gray-800 pt-4">
              <Field label="Correo o dominio" helper="Puedes pegar un correo completo o solo el dominio.">
                <div className="flex gap-2">
                  <input
                    className="input"
                    placeholder="fastudillo@clinicasantamaria.cl o clinicasantamaria.cl"
                    value={domainDraft.domain}
                    onChange={(event) => setDomainDraft({ domain: event.target.value })}
                  />
                  <button
                    className="btn-secondary shrink-0 px-3 py-2 text-xs"
                    onClick={() => {
                      const normalized = normalizeEmailHint(domainDraft.domain)
                      if (!normalized) {
                        onMessage({ kind: 'error', text: 'Ingresa un correo o dominio antes de agregarlo.' })
                        return
                      }
                      domainMutation.mutate(normalized)
                    }}
                    disabled={domainMutation.isPending}
                  >
                    <Plus size={12} />
                    Agregar
                  </button>
                </div>
              </Field>
            </div>
          </div>
        </div>

        <details className="rounded-2xl border border-gray-800 bg-gray-950/40 px-4 py-3">
          <summary className="flex cursor-pointer items-center gap-2 text-sm text-gray-300">
            <Settings2 size={15} />
            Opciones avanzadas
          </summary>

          <div className="mt-5 space-y-5">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Field label="Formato PDF interno" helper="Solo cambialo si el holding requiere un parser distinto.">
                <input
                  className="input"
                  value={draft.parser_type}
                  onChange={(event) => setDraft((previous) => ({ ...previous, parser_type: event.target.value }))}
                />
              </Field>
              <div className="rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-sm text-gray-400">
                Usa estas ayudas solo si el holding no se reconoce bien con RUTs y correos esperados.
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-100">Ayudas avanzadas</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Textos del PDF, asunto o remitente que ayuden a reforzar la deteccion.
                  </p>
                </div>
              </div>

              {advancedRules.length > 0 ? (
                <div className="space-y-3">
                  {advancedRules.map((rule) => (
                    <RuleEditor
                      key={rule.id}
                      holdingId={holding.id}
                      holdingNombre={holding.nombre}
                      rule={rule}
                      onMessage={onMessage}
                      onDone={invalidate}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex items-start gap-2 rounded-xl border border-amber-800/40 bg-amber-950/20 px-3 py-3 text-sm text-amber-200">
                  <ShieldAlert size={14} className="mt-0.5 shrink-0" />
                  No hay ayudas avanzadas cargadas. Eso esta bien si el holding ya se detecta correctamente.
                </div>
              )}

              <div className="grid grid-cols-1 gap-2 border-t border-gray-800 pt-4 md:grid-cols-4">
                <Field label="Tipo de ayuda">
                  <select
                    className="input"
                    value={newRule.rule_type}
                    onChange={(event) => setNewRule((previous) => ({ ...previous, rule_type: event.target.value }))}
                  >
                    {ADVANCED_RULE_TYPES.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Valor">
                  <input
                    className="input"
                    value={newRule.rule_value}
                    onChange={(event) => setNewRule((previous) => ({ ...previous, rule_value: event.target.value }))}
                  />
                </Field>
                <Field label="Prioridad">
                  <input
                    className="input"
                    type="number"
                    value={newRule.prioridad}
                    onChange={(event) => setNewRule((previous) => ({ ...previous, prioridad: Number(event.target.value) || 0 }))}
                  />
                </Field>
                <Field label="Notas">
                  <div className="flex gap-2">
                    <input
                      className="input"
                      value={newRule.notas || ''}
                      onChange={(event) => setNewRule((previous) => ({ ...previous, notas: event.target.value }))}
                    />
                    <button
                      className="btn-secondary shrink-0 px-3 py-2 text-xs"
                      onClick={() => createRuleMutation.mutate(newRule)}
                      disabled={createRuleMutation.isPending}
                    >
                      <Plus size={12} />
                      Agregar
                    </button>
                  </div>
                </Field>
              </div>

              <label className="flex items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-3 py-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={newRule.activo}
                  onChange={(event) => setNewRule((previous) => ({ ...previous, activo: event.target.checked }))}
                />
                Regla activa
              </label>
            </div>
          </div>
        </details>
      </div>
    </section>
  )
}

function RuleEditor({
  holdingId,
  holdingNombre,
  rule,
  onMessage,
  onDone,
}: {
  holdingId: string
  holdingNombre: string
  rule: HoldingRule
  onMessage: (message: MessageState) => void
  onDone: () => void
}) {
  const [draft, setDraft] = useState<HoldingRulePayload>({
    rule_type: rule.rule_type,
    rule_value: rule.rule_value,
    prioridad: rule.prioridad,
    activo: rule.activo,
    notas: rule.notas,
  })

  useEffect(() => {
    setDraft({
      rule_type: rule.rule_type,
      rule_value: rule.rule_value,
      prioridad: rule.prioridad,
      activo: rule.activo,
      notas: rule.notas,
    })
  }, [rule])

  const saveMutation = useMutation({
    mutationFn: (payload: HoldingRulePayload) => updateHoldingRule(holdingId, rule.id, payload),
    onSuccess: () => {
      onMessage({ kind: 'success', text: `Regla ${rule.id} actualizada en ${holdingNombre}.` })
      onDone()
    },
    onError: (error: Error) => onMessage({ kind: 'error', text: error.message }),
  })

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-950/50 px-3 py-3">
      <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
        <Field label="Tipo">
          <input className="input" value={draft.rule_type} onChange={(event) => setDraft((previous) => ({ ...previous, rule_type: event.target.value }))} />
        </Field>
        <Field label="Valor">
          <input className="input" value={draft.rule_value} onChange={(event) => setDraft((previous) => ({ ...previous, rule_value: event.target.value }))} />
        </Field>
        <Field label="Prioridad">
          <input
            className="input"
            type="number"
            value={draft.prioridad}
            onChange={(event) => setDraft((previous) => ({ ...previous, prioridad: Number(event.target.value) || 0 }))}
          />
        </Field>
        <Field label="Notas">
          <input className="input" value={draft.notas || ''} onChange={(event) => setDraft((previous) => ({ ...previous, notas: event.target.value }))} />
        </Field>
      </div>

      <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <label className="flex items-center gap-2 rounded-xl border border-gray-800 bg-gray-950/60 px-3 py-2 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={draft.activo}
            onChange={(event) => setDraft((previous) => ({ ...previous, activo: event.target.checked }))}
          />
          Regla activa
        </label>
        <div className="flex items-center gap-2">
          <button
            className="btn-secondary px-3 py-2 text-xs"
            onClick={() => {
              deleteHoldingRule(holdingId, rule.id)
                .then(() => {
                  onMessage({ kind: 'success', text: `Regla ${rule.id} eliminada.` })
                  onDone()
                })
                .catch((error: Error) => onMessage({ kind: 'error', text: error.message }))
            }}
          >
            <Trash2 size={12} />
            Quitar
          </button>
          <button className="btn-primary px-3 py-2 text-xs" onClick={() => saveMutation.mutate(draft)} disabled={saveMutation.isPending}>
            <Save size={12} />
            Guardar
          </button>
        </div>
      </div>
    </div>
  )
}

function normalizeEmailHint(value: string) {
  const cleaned = value
    .trim()
    .toLowerCase()
    .replace(/^mailto:/, '')
    .replace(/[<>]/g, '')
    .replace(/^@+/, '')

  if (!cleaned) return ''
  const atIndex = cleaned.lastIndexOf('@')
  if (atIndex >= 0) {
    return cleaned.slice(atIndex + 1).trim()
  }
  return cleaned
}

function SummaryPill({ label, value }: { label: string; value: number }) {
  return (
    <span className="rounded-full border border-gray-800 bg-gray-950/70 px-3 py-1 text-sm text-gray-300">
      {label}: {value.toLocaleString()}
    </span>
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
