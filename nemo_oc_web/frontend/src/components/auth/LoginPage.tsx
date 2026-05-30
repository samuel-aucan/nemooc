import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { bootstrapAdmin, completeReset, getBootstrapStatus, getCurrentUser, login } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useAppearanceSettings } from '../../hooks/useAppearance'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const qc = useQueryClient()
  const { logoSrc } = useAppearanceSettings()

  const authQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 60_000,
  })

  const bootstrapQuery = useQuery({
    queryKey: ['auth', 'bootstrap-status'],
    queryFn: getBootstrapStatus,
    staleTime: 60_000,
  })

  const [username, setUsername] = useState('')
  const [nombreCompleto, setNombreCompleto] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [mode, setMode] = useState<'login' | 'reset'>('login')
  const [localError, setLocalError] = useState('')

  const from = useMemo(() => {
    const state = location.state as { from?: { pathname?: string } } | null
    return state?.from?.pathname || '/'
  }, [location.state])

  const requiresSetup = bootstrapQuery.data?.requires_setup ?? false

  const authMutation = useMutation({
    mutationFn: async () => {
      if (requiresSetup) {
        if (password !== passwordConfirm) {
          throw new Error('Las contraseñas no coinciden.')
        }
        return bootstrapAdmin(username, nombreCompleto, password, passwordConfirm)
      }
      return login(username, password)
    },
    onSuccess: (user) => {
      qc.setQueryData(['auth', 'me'], user)
      navigate(from, { replace: true })
    },
  })

  const resetMutation = useMutation({
    mutationFn: () => completeReset(username, resetToken, password, passwordConfirm),
    onSuccess: (user) => {
      qc.setQueryData(['auth', 'me'], user)
      navigate(from, { replace: true })
    },
  })

  useEffect(() => {
    if (authMutation.isError) {
      setLocalError(authMutation.error.message)
    }
  }, [authMutation.error, authMutation.isError])

  useEffect(() => {
    if (resetMutation.isError) {
      setLocalError(resetMutation.error.message)
    }
  }, [resetMutation.error, resetMutation.isError])

  if (authQuery.data) {
    return <Navigate to={from} replace />
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setLocalError('')
    if (!requiresSetup && mode === 'reset') {
      resetMutation.mutate()
      return
    }
    authMutation.mutate()
  }

  const authStatus = authQuery.isError ? (authQuery.error as ApiError).status : undefined
  const loading = authQuery.isLoading || bootstrapQuery.isLoading

  return (
    <div className="min-h-screen bg-gray-950 px-6 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8">
        <div className="auth-hero-panel hidden rounded-[32px] border border-gray-800 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.18),transparent_40%),linear-gradient(180deg,rgba(17,24,39,0.98),rgba(3,7,18,0.96))] p-10 shadow-2xl lg:block">
          <img src={logoSrc} alt="NEMONKEY" className="w-56 opacity-95" />
          <div className="mt-10 max-w-lg space-y-4">
            <p className="text-sm uppercase tracking-[0.18em] text-accent">Acceso protegido</p>
            <h1 className="text-4xl font-semibold tracking-tight text-gray-50">
              Centro de control para ordenes de compra publicas y privadas.
            </h1>
            <p className="text-base leading-7 text-gray-300">
              La sesión queda protegida por cookie segura y todas las rutas operativas requieren autenticación.
            </p>
            <div className="rounded-2xl border border-gray-800 bg-gray-950/55 px-5 py-4 text-sm leading-6 text-gray-400">
              {requiresSetup
                ? 'Primera vez: crea el usuario administrador inicial para dejar la aplicación lista para producción.'
                : mode === 'reset'
                  ? 'Usa el token temporal que te entregó un administrador para definir tu nueva contraseña.'
                  : 'Ingresa con tu usuario y contrasena para continuar trabajando en NEMONKEY.'}
            </div>
          </div>
        </div>

        <div className="mx-auto w-full max-w-md">
          <div className="rounded-[28px] border border-gray-800 bg-gray-900/90 p-7 shadow-2xl">
            <div className="mb-6">
              <p className="text-sm uppercase tracking-[0.18em] text-gray-500">
                {requiresSetup ? 'Configuracion inicial' : mode === 'reset' ? 'Activacion de acceso' : 'Inicio de sesion'}
              </p>
              <h2 className="mt-3 text-2xl font-semibold text-gray-50">
                {requiresSetup ? 'Crear administrador' : mode === 'reset' ? 'Definir nueva contrasena' : 'Entrar a NEMONKEY'}
              </h2>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                {requiresSetup
                  ? 'Este será el primer usuario con acceso completo a la aplicación.'
                  : mode === 'reset'
                    ? 'Este flujo solo funciona si un administrador reinició tu acceso y te entregó un token.'
                    : 'Usa tu cuenta autorizada para acceder al sistema.'}
              </p>
            </div>

            {loading ? (
              <div className="rounded-2xl border border-gray-800 bg-gray-950/60 px-4 py-6 text-sm text-gray-400">
                Revisando el estado de seguridad de la aplicacion...
              </div>
            ) : (
              <form className="space-y-4" onSubmit={submit}>
                {requiresSetup && (
                  <label className="block">
                    <span className="label">Nombre completo</span>
                    <input
                      className="input"
                      value={nombreCompleto}
                      onChange={(event) => setNombreCompleto(event.target.value)}
                      placeholder="Samuel Belmar"
                    />
                  </label>
                )}

                <label className="block">
                  <span className="label">{requiresSetup ? 'Usuario' : 'Email'}</span>
                  <input
                    className="input"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    placeholder={requiresSetup ? 'admin' : 'usuario@nemochile.cl'}
                    autoComplete={requiresSetup ? 'username' : 'email'}
                  />
                </label>

                <label className="block">
                  <span className="label">Contraseña</span>
                  <input
                    className="input"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Ingresa tu contraseña"
                    autoComplete={requiresSetup ? 'new-password' : 'current-password'}
                  />
                </label>

                {!requiresSetup && mode === 'reset' && (
                  <label className="block">
                    <span className="label">Token temporal</span>
                    <input
                      className="input"
                      value={resetToken}
                      onChange={(event) => setResetToken(event.target.value)}
                      placeholder="Pega aqui el token entregado"
                    />
                  </label>
                )}

                {(requiresSetup || mode === 'reset') && (
                  <label className="block">
                    <span className="label">Confirmar contraseña</span>
                    <input
                      className="input"
                      type="password"
                      value={passwordConfirm}
                      onChange={(event) => setPasswordConfirm(event.target.value)}
                      placeholder="Repite la contraseña"
                      autoComplete="new-password"
                    />
                  </label>
                )}

                {(localError || (authQuery.isError && authStatus && authStatus !== 401) || bootstrapQuery.isError) && (
                  <div className="rounded-2xl border border-red-900/40 bg-red-950/15 px-4 py-3 text-sm text-red-200">
                    {localError ||
                      (authQuery.isError && authStatus !== 401 ? authQuery.error.message : '') ||
                      (bootstrapQuery.error as Error | undefined)?.message}
                  </div>
                )}

                {!requiresSetup && (
                  <div className="grid grid-cols-2 gap-2 rounded-2xl border border-gray-800 bg-gray-950/40 p-1">
                    <button
                      type="button"
                      className={`rounded-xl px-3 py-2 text-sm transition-colors ${
                        mode === 'login' ? 'bg-gray-800 text-gray-100' : 'text-gray-400 hover:text-gray-200'
                      }`}
                      onClick={() => {
                        setLocalError('')
                        setMode('login')
                      }}
                    >
                      Iniciar sesión
                    </button>
                    <button
                      type="button"
                      className={`rounded-xl px-3 py-2 text-sm transition-colors ${
                        mode === 'reset' ? 'bg-gray-800 text-gray-100' : 'text-gray-400 hover:text-gray-200'
                      }`}
                      onClick={() => {
                        setLocalError('')
                        setMode('reset')
                      }}
                    >
                      Activar acceso
                    </button>
                  </div>
                )}

                <button
                  className="btn-primary w-full justify-center"
                  disabled={
                    authMutation.isPending ||
                    resetMutation.isPending ||
                    bootstrapQuery.isLoading ||
                    !username.trim() ||
                    !password.trim() ||
                    password.length < 8 ||
                    (!requiresSetup && mode === 'reset' && (!resetToken.trim() || password !== passwordConfirm)) ||
                    (requiresSetup && password !== passwordConfirm)
                  }
                  type="submit"
                >
                  {(authMutation.isPending || resetMutation.isPending)
                    ? 'Validando acceso...'
                    : requiresSetup
                      ? 'Crear administrador'
                      : mode === 'reset'
                        ? 'Guardar nueva contraseña'
                        : 'Entrar'}
                </button>

                <p className="text-xs leading-5 text-gray-500">
                  {requiresSetup
                    ? 'La contraseña debe tener al menos 8 caracteres.'
                    : mode === 'reset'
                      ? 'Usa el token temporal que te entregó un administrador para definir tu nueva clave.'
                      : 'Si el acceso falla, revisa que tu navegador mantenga cookies habilitadas para este sitio.'}
                </p>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
