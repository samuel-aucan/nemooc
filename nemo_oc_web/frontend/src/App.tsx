import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import AppLayout from './components/layout/AppLayout'
import ProtectedApp from './components/auth/ProtectedApp'
import LoginPage from './components/auth/LoginPage'

const OcListPage     = lazy(() => import('./components/oc-list/OcListPage'))
const OcDetailPage   = lazy(() => import('./components/oc-detail/OcDetailPage'))
const ImportPage     = lazy(() => import('./components/import-page/ImportPage'))
const ConfigPage     = lazy(() => import('./components/config-page/ConfigPage'))
const HoldingsPage   = lazy(() => import('./components/holdings-page/HoldingsPage'))
const StatisticsPage = lazy(() => import('./components/statistics-page/StatisticsPage'))
const UsersPage      = lazy(() => import('./components/users-page/UsersPage'))
const AuditoriaPage  = lazy(() => import('./components/auditoria-page/AuditoriaPage'))

function PageLoader() {
  return (
    <div className="flex h-full items-center justify-center py-20 text-sm text-gray-500">
      Cargando...
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="login" element={<LoginPage />} />
          <Route element={<ProtectedApp />}>
            <Route element={<AppLayout />}>
              <Route index element={<Suspense fallback={<PageLoader />}><OcListPage /></Suspense>} />
              <Route path="oc/:codigo" element={<Suspense fallback={<PageLoader />}><OcDetailPage /></Suspense>} />
              <Route path="import" element={<Suspense fallback={<PageLoader />}><ImportPage /></Suspense>} />
              <Route path="stats" element={<Suspense fallback={<PageLoader />}><StatisticsPage /></Suspense>} />
              <Route path="holdings" element={<Suspense fallback={<PageLoader />}><HoldingsPage /></Suspense>} />
              <Route path="users" element={<Suspense fallback={<PageLoader />}><UsersPage /></Suspense>} />
              <Route path="config" element={<Suspense fallback={<PageLoader />}><ConfigPage /></Suspense>} />
              <Route path="auditoria" element={<Suspense fallback={<PageLoader />}><AuditoriaPage /></Suspense>} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
