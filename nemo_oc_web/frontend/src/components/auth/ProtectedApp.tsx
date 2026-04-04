import { useQuery } from '@tanstack/react-query'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { getCurrentUser } from '../../api/auth'
import { ApiError } from '../../api/client'

export default function ProtectedApp() {
  const location = useLocation()
  const authQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 60_000,
  })

  if (authQuery.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950 px-6">
        <div className="w-full max-w-md rounded-3xl border border-gray-800 bg-gray-900/85 p-8 text-center shadow-2xl">
          <p className="text-sm uppercase tracking-[0.18em] text-gray-500">NemoOC</p>
          <h1 className="mt-3 text-2xl font-semibold text-gray-50">Verificando sesion</h1>
          <p className="mt-3 text-sm leading-6 text-gray-400">
            Estamos confirmando tu acceso antes de cargar la aplicacion.
          </p>
        </div>
      </div>
    )
  }

  if (authQuery.isError) {
    const status = (authQuery.error as ApiError).status
    if (status === 401) {
      return <Navigate to="/login" replace state={{ from: location }} />
    }

    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950 px-6">
        <div className="w-full max-w-md rounded-3xl border border-red-900/40 bg-gray-900/85 p-8 shadow-2xl">
          <p className="text-sm uppercase tracking-[0.18em] text-red-300">Acceso no disponible</p>
          <h1 className="mt-3 text-2xl font-semibold text-gray-50">No pudimos validar la sesión</h1>
          <p className="mt-3 text-sm leading-6 text-gray-400">{authQuery.error.message}</p>
        </div>
      </div>
    )
  }

  return <Outlet />
}
