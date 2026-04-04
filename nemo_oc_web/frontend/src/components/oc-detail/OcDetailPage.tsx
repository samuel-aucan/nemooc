import { useNavigate, useParams } from 'react-router-dom'

import OcDetailPanel from './OcDetailPanel'

export default function OcDetailPage() {
  const navigate = useNavigate()
  const { codigo } = useParams<{ codigo: string }>()

  if (!codigo) {
    return <div className="page-shell text-red-400">No se encontro el codigo de la OC.</div>
  }

  return <OcDetailPanel codigo={codigo} onClose={() => navigate('/')} />
}
