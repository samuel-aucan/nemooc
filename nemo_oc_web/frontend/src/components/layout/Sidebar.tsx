import { NavLink, useNavigate } from 'react-router-dom'
import { BarChart3, Building2, Download, LayoutList, LogOut, RefreshCw, Settings, Shield, Users } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getCurrentUser, logout } from '../../api/auth'
import api from '../../api/client'

const links = [
  { to: '/', icon: LayoutList, label: 'Ordenes de compra', description: 'Bandeja principal y detalle' },
  { to: '/import', icon: Download, label: 'Importaciones', description: 'Mercado Publico y privados' },
  { to: '/stats', icon: BarChart3, label: 'Estadisticas', description: 'Cobertura, sugerencias y cola experta' },
  { to: '/holdings', icon: Building2, label: 'Holdings', description: 'Clientes, correos y catalogos' },
  { to: '/users', icon: Users, label: 'Usuarios', description: 'Accesos, roles y contraseñas' },
  { to: '/config', icon: Settings, label: 'Configuracion', description: 'Credenciales y automatizacion' },
]

export default function Sidebar() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: syncStatus } = useQuery({
    queryKey: ['sync-status'],
    queryFn: () => api.get<{ running: boolean; active_tasks: string[] }>('/sync/status').then((r) => r.data),
    refetchInterval: 5000,
  })
  const { data: currentUser } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 60_000,
  })

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      qc.removeQueries({ queryKey: ['auth', 'me'] })
      navigate('/login', { replace: true })
    },
  })

  const running = syncStatus?.running ?? false
  const activeTasks = syncStatus?.active_tasks.length ?? 0

  return (
    <aside className="flex w-64 flex-shrink-0 flex-col border-r border-gray-800 bg-gray-950">
      <div className="border-b border-gray-800 px-5 py-5">
        <img
          src="/branding/logo-nemo-dark.png"
          alt="Nemo Insumos Medicos"
          className="h-auto w-full opacity-95"
        />
        <p className="mt-3 text-xs leading-5 text-gray-500">
          Centro de control para ordenes de compra publicas y privadas.
        </p>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Navegacion principal">
        {links
          .filter((link) => (link.to === '/users' ? currentUser?.rol === 'admin' : true))
          .map(({ to, icon: Icon, label, description }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `block rounded-xl border px-3 py-3 transition-all ${
                isActive
                  ? 'border-transparent'
                  : 'border-transparent text-gray-300 hover:border-gray-800 hover:bg-gray-900'
              }`
            }
            style={({ isActive }) =>
              isActive
                ? {
                    backgroundColor: 'rgba(var(--accent-900), 0.34)',
                    color: 'rgb(var(--accent-400))',
                    borderColor: 'rgba(var(--accent-500), 0.28)',
                  }
                : undefined
            }
          >
            {({ isActive }) => (
              <div className="flex items-start gap-3">
                <span
                  className="mt-0.5 rounded-lg p-2"
                  style={
                    isActive
                      ? {
                          backgroundColor: 'rgba(var(--accent-500), 0.16)',
                          color: 'rgb(var(--accent-400))',
                        }
                      : undefined
                  }
                >
                  <Icon size={16} />
                </span>
                <div className="min-w-0">
                  <div className={`text-sm font-medium ${isActive ? 'text-accent' : 'text-gray-100'}`}>
                    {label}
                  </div>
                  <div className="mt-0.5 text-xs leading-5 text-gray-500">{description}</div>
                </div>
              </div>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-gray-800 px-4 py-4">
        <div className="rounded-xl border border-gray-800 bg-gray-900/70 px-3 py-3">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-500">
            Estado del sistema
          </div>
          {running ? (
            <div className="flex items-start gap-3">
              <RefreshCw size={14} className="mt-0.5 animate-spin text-accent" />
              <div>
                <div className="text-sm font-medium text-gray-100">Sincronizacion en curso</div>
                <div className="text-xs leading-5 text-gray-500">
                  {activeTasks > 0
                    ? `${activeTasks} tarea(s) activas`
                    : 'Procesando importacion en segundo plano'}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3">
              <span className="mt-1 inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(74,222,128,0.5)]" />
              <div>
                <div className="text-sm font-medium text-gray-100">Sistema disponible</div>
                <div className="text-xs leading-5 text-gray-500">Sin procesos activos en este momento</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-gray-800 px-4 py-4">
        <div className="rounded-xl border border-gray-800 bg-gray-900/70 px-3 py-3">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-500">
            <Shield size={12} />
            Sesion
          </div>
          <div className="text-sm font-medium text-gray-100">
            {currentUser?.nombre_completo || currentUser?.username || 'Usuario autenticado'}
          </div>
          <div className="mt-1 text-xs leading-5 text-gray-500">
            {currentUser?.rol ? `Rol ${currentUser.rol}` : 'Acceso protegido con cookie de sesión'}
          </div>
          <button
            className="btn-secondary mt-3 w-full justify-center"
            disabled={logoutMutation.isPending}
            onClick={() => logoutMutation.mutate()}
          >
            <LogOut size={14} />
            {logoutMutation.isPending ? 'Cerrando...' : 'Cerrar sesion'}
          </button>
        </div>
      </div>

      <div className="space-y-1 border-t border-gray-800 px-4 py-4 text-xs text-gray-500">
        <div>v2.0 - Web</div>
        <div className="text-[11px] text-gray-600">Desarrollado por Samuel Belmar</div>
      </div>
    </aside>
  )
}
