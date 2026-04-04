import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Sidebar from './Sidebar'
import StatusBar from './StatusBar'
import { getConfig } from '../../api/config'

export default function AppLayout() {
  const { data: cfg } = useQuery({ queryKey: ['config'], queryFn: getConfig })

  useEffect(() => {
    const accent = cfg?.color_theme || 'blue'
    document.documentElement.setAttribute('data-accent', accent)
  }, [cfg?.color_theme])

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
        <StatusBar />
      </div>
    </div>
  )
}
