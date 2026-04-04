import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import ProtectedApp from './components/auth/ProtectedApp'
import LoginPage from './components/auth/LoginPage'
import OcListPage from './components/oc-list/OcListPage'
import OcDetailPage from './components/oc-detail/OcDetailPage'
import ImportPage from './components/import-page/ImportPage'
import ConfigPage from './components/config-page/ConfigPage'
import HoldingsPage from './components/holdings-page/HoldingsPage'
import StatisticsPage from './components/statistics-page/StatisticsPage'
import UsersPage from './components/users-page/UsersPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="login" element={<LoginPage />} />
        <Route element={<ProtectedApp />}>
          <Route element={<AppLayout />}>
            <Route index element={<OcListPage />} />
            <Route path="oc/:codigo" element={<OcDetailPage />} />
            <Route path="import" element={<ImportPage />} />
            <Route path="stats" element={<StatisticsPage />} />
            <Route path="holdings" element={<HoldingsPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="config" element={<ConfigPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
