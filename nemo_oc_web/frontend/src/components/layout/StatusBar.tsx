import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Clock3, Layers3 } from 'lucide-react'

import { getStats } from '../../api/ocs'

function StatChip({
  label,
  value,
  icon,
  tone,
}: {
  label: string
  value: number | string
  icon: ReactNode
  tone: string
}) {
  return (
    <div className="flex min-w-[160px] items-center gap-3 rounded-xl border border-gray-800 bg-gray-900/80 px-3 py-2">
      <span className={`rounded-lg p-2 ${tone}`}>{icon}</span>
      <div>
        <div className="text-[11px] uppercase tracking-[0.12em] text-gray-500">{label}</div>
        <div className="text-sm font-semibold text-gray-100">{value}</div>
      </div>
    </div>
  )
}

export default function StatusBar() {
  const { data } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: 30_000,
  })

  return (
    <div className="border-t border-gray-800 bg-gray-950/95 px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <StatChip
          label="Total OCs"
          value={data?.total ?? '-'}
          icon={<Layers3 size={14} className="text-blue-300" />}
          tone="bg-blue-500/15"
        />
        <StatChip
          label="Sin homologar"
          value={data?.sin_homolog ?? '-'}
          icon={<Clock3 size={14} className="text-amber-300" />}
          tone="bg-amber-500/15"
        />
        <StatChip
          label="Ingresadas"
          value={data?.ingresadas ?? '-'}
          icon={<CheckCircle2 size={14} className="text-emerald-300" />}
          tone="bg-emerald-500/15"
        />
      </div>
    </div>
  )
}
