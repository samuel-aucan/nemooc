import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ShieldAlert, UserPlus } from 'lucide-react'

import { createUser, getCurrentUser, getUsers, resetUserPassword, restartUserAccess, updateUser } from '../../api/auth'
import type { AuthUser, ResetAccessToken } from '../../types/auth'

const roleOptions = [
  { value: 'operador', label: 'Operador' },
  { value: 'admin', label: 'Administrador' },
]

export default function UsersPage() {
  const qc = useQueryClient()
  const [username, setUsername] = useState('')
  const [nombreCompleto, setNombreCompleto] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [rol, setRol] = useState('operador')
  const [message, setMessage] = useState('')

  const authQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 60_000,
  })

  const usersQuery = useQuery({
    queryKey: ['auth', 'users'],
    queryFn: getUsers,
    staleTime: 30_000,
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createUser({
        username,
        nombre_completo: nombreCompleto,
        password,
        password_confirm: passwordConfirm,
        rol,
      }),
    onSuccess: () => {
      setUsername('')
      setNombreCompleto('')
      setPassword('')
      setPasswordConfirm('')
      setRol('operador')
      setMessage('Usuario creado correctamente.')
      qc.invalidateQueries({ queryKey: ['auth', 'users'] })
    },
  })

  const isAdmin = authQuery.data?.rol === 'admin'
  const authDisabled = authQuery.data?.auth_disabled ?? false
  const users = usersQuery.data ?? []

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setMessage('')
    createMutation.mutate()
  }

  if (authQuery.isLoading || usersQuery.isLoading) {
    return (
      <div className="page-shell">
        <section className="card">
          <div className="card-body text-sm text-gray-400">Cargando administración de usuarios...</div>
        </section>
      </div>
    )
  }

  if (!isAdmin) {
    return (
      <div className="page-shell">
        <section className="card">
          <div className="card-body flex items-start gap-3 text-sm text-amber-200">
            <ShieldAlert size={18} className="mt-0.5 text-amber-300" />
            <div>
              <div className="font-medium text-gray-100">Acceso restringido</div>
              <div className="mt-1 text-gray-400">
                Solo un usuario administrador puede crear o gestionar cuentas.
              </div>
            </div>
          </div>
        </section>
      </div>
    )
  }

  if (authDisabled) {
    return (
      <div className="page-shell">
        <section className="card">
          <div className="card-body flex items-start gap-3 text-sm text-gray-300">
            <ShieldAlert size={18} className="mt-0.5 text-accent" />
            <div>
              <div className="font-medium text-gray-100">Modo local sin contraseñas</div>
              <div className="mt-1 text-gray-400">
                La gestion de usuarios esta deshabilitada porque esta instalacion entra directo y no pide login.
              </div>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Usuarios</h1>
          <p className="page-subtitle">
            Crea y controla quién puede entrar a NemoOC. No existe registro público: solo un administrador puede dar accesos.
          </p>
        </div>
      </div>

      <section className="card">
        <div className="card-header">
          <UserPlus size={15} className="text-accent" />
          Crear usuario
        </div>
        <div className="card-body">
          <form className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.2fr_1fr_1fr_180px_auto]" onSubmit={submit}>
            <label className="block">
              <span className="label">Usuario</span>
              <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="mlopez" />
            </label>
            <label className="block">
              <span className="label">Nombre completo</span>
              <input
                className="input"
                value={nombreCompleto}
                onChange={(e) => setNombreCompleto(e.target.value)}
                placeholder="Manuel Lopez"
              />
            </label>
            <label className="block">
              <span className="label">Contraseña</span>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimo 8 caracteres"
              />
            </label>
            <label className="block">
              <span className="label">Confirmar contraseña</span>
              <input
                className="input"
                type="password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="Repite la contraseña"
              />
            </label>
            <label className="block">
              <span className="label">Rol</span>
              <select className="select" value={rol} onChange={(e) => setRol(e.target.value)}>
                {roleOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex items-end">
              <button
                className="btn-primary w-full justify-center"
                disabled={
                  createMutation.isPending ||
                  !username.trim() ||
                  !password.trim() ||
                  password.length < 8 ||
                  password !== passwordConfirm
                }
                type="submit"
              >
                {createMutation.isPending ? 'Creando...' : 'Crear'}
              </button>
            </div>
          </form>

          {(message || createMutation.isError) && (
            <div className={`mt-4 text-sm ${createMutation.isError ? 'text-red-300' : 'text-emerald-300'}`}>
              {createMutation.isError ? createMutation.error.message : message}
            </div>
          )}
        </div>
      </section>

      <section className="card">
        <div className="card-header">Usuarios existentes</div>
        <div className="card-body">
          <div className="overflow-auto rounded-2xl border border-gray-800 bg-gray-950/60">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Nombre</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th>Ultimo acceso</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <UserRow key={user.id} user={user} currentUserId={authQuery.data?.id ?? 0} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  )
}

function UserRow({ user, currentUserId }: { user: AuthUser; currentUserId: number }) {
  const qc = useQueryClient()
  const [nombreCompleto, setNombreCompleto] = useState(user.nombre_completo)
  const [rol, setRol] = useState(user.rol)
  const [activo, setActivo] = useState(user.activo)
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [resetAccessToken, setResetAccessToken] = useState<ResetAccessToken | null>(null)
  const [message, setMessage] = useState('')

  const hasChanges = useMemo(
    () => nombreCompleto !== user.nombre_completo || rol !== user.rol || activo !== user.activo,
    [activo, nombreCompleto, rol, user.activo, user.nombre_completo, user.rol],
  )

  const saveMutation = useMutation({
    mutationFn: () =>
      updateUser(user.id, {
        nombre_completo: nombreCompleto,
        rol,
        activo,
      }),
    onSuccess: () => {
      setMessage('Usuario actualizado.')
      qc.invalidateQueries({ queryKey: ['auth', 'users'] })
      if (user.id === currentUserId) {
        qc.invalidateQueries({ queryKey: ['auth', 'me'] })
      }
    },
  })

  const passwordMutation = useMutation({
    mutationFn: () => resetUserPassword(user.id, password, passwordConfirm),
    onSuccess: () => {
      setMessage('Contraseña actualizada.')
      setPassword('')
      setPasswordConfirm('')
      setShowPasswordForm(false)
    },
  })

  const restartAccessMutation = useMutation({
    mutationFn: () => restartUserAccess(user.id),
    onSuccess: (tokenData) => {
      setResetAccessToken(tokenData)
      setMessage('Acceso reiniciado. Comparte el token temporal con este usuario.')
      qc.invalidateQueries({ queryKey: ['auth', 'users'] })
    },
  })

  return (
    <>
      <tr>
        <td className="min-w-[150px]">
          <div className="font-medium text-gray-100">{user.username}</div>
          {user.id === currentUserId && <div className="text-xs text-gray-500">Tu sesión actual</div>}
        </td>
        <td className="min-w-[220px]">
          <input className="input h-9" value={nombreCompleto} onChange={(e) => setNombreCompleto(e.target.value)} />
        </td>
        <td className="min-w-[160px]">
          <select className="select h-9" value={rol} onChange={(e) => setRol(e.target.value)}>
            {roleOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </td>
        <td className="min-w-[150px]">
          <button
            className={activo ? 'btn-secondary w-full justify-center' : 'btn-danger w-full justify-center'}
            onClick={() => setActivo((value) => !value)}
          >
            {activo ? 'Activo' : 'Desactivado'}
          </button>
        </td>
        <td className="min-w-[180px] text-sm text-gray-400">
          {user.last_login_at ? new Date(user.last_login_at).toLocaleString('es-CL') : 'Sin ingresos'}
        </td>
        <td className="min-w-[260px]">
          <div className="flex flex-wrap gap-2">
            <button
              className="btn-primary"
              disabled={!hasChanges || saveMutation.isPending}
              onClick={() => {
                setMessage('')
                saveMutation.mutate()
              }}
            >
              {saveMutation.isPending ? 'Guardando...' : 'Guardar'}
            </button>
            <button className="btn-secondary" onClick={() => setShowPasswordForm((value) => !value)}>
              {showPasswordForm ? 'Cancelar clave' : 'Resetear clave'}
            </button>
            <button
              className="btn-secondary"
              disabled={restartAccessMutation.isPending || user.id === currentUserId}
              onClick={() => {
                setMessage('')
                setResetAccessToken(null)
                restartAccessMutation.mutate()
              }}
              title={user.id === currentUserId ? 'No puedes reiniciar tu propio acceso desde aquí.' : undefined}
            >
              {restartAccessMutation.isPending ? 'Generando token...' : 'Reiniciar acceso'}
            </button>
          </div>
          {(message || saveMutation.isError || passwordMutation.isError || restartAccessMutation.isError) && (
            <div className={`mt-2 text-xs ${saveMutation.isError || passwordMutation.isError || restartAccessMutation.isError ? 'text-red-300' : 'text-emerald-300'}`}>
              {saveMutation.isError
                ? saveMutation.error.message
                : passwordMutation.isError
                  ? passwordMutation.error.message
                  : restartAccessMutation.isError
                    ? restartAccessMutation.error.message
                  : message}
            </div>
          )}
        </td>
      </tr>
      {resetAccessToken && (
        <tr className="bg-blue-950/10">
          <td colSpan={6}>
            <div className="space-y-2 px-3 py-3">
              <div className="text-sm font-medium text-blue-200">Token temporal generado</div>
              <div className="rounded-xl border border-blue-800/40 bg-gray-950/70 px-3 py-3">
                <div className="text-xs uppercase tracking-[0.14em] text-gray-500">Token</div>
                <div className="mt-1 break-all font-mono text-sm text-gray-100">{resetAccessToken.reset_token}</div>
                <div className="mt-3 text-xs text-gray-400">
                  Vence: {new Date(resetAccessToken.expires_at).toLocaleString('es-CL')}
                </div>
                <div className="mt-2 text-xs text-amber-300">
                  Entrega este token de forma segura. El usuario lo usará en la opción “Activar acceso”.
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
      {showPasswordForm && (
        <tr className="bg-gray-950/40">
          <td colSpan={6}>
            <div className="grid grid-cols-1 gap-3 px-3 py-3 xl:grid-cols-[1fr_1fr_auto]">
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nueva contraseña"
              />
              <input
                className="input"
                type="password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="Confirmar nueva contraseña"
              />
              <button
                className="btn-primary justify-center"
                disabled={passwordMutation.isPending || password.length < 8 || password !== passwordConfirm}
                onClick={() => {
                  setMessage('')
                  passwordMutation.mutate()
                }}
              >
                {passwordMutation.isPending ? 'Actualizando...' : 'Guardar contraseña'}
              </button>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
