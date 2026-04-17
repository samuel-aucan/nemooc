import { memo } from 'react'
import { CheckSquare, Copy, ExternalLink, FileDown, RefreshCw, Settings, X } from 'lucide-react'
import type { OrdenCompra } from '../../types/oc'

interface OcDetailActionsProps {
  oc: OrdenCompra
  esCM: boolean
  isRehomologating: boolean
  isIngresando: boolean
  onRehomologar: () => void
  onCopySap: () => void
  onOpenSapConfig: () => void
  onExport: () => void
  onIngresar: () => void
  onClose: () => void
}

const OcDetailActions = memo(function OcDetailActions({
  oc,
  esCM,
  isRehomologating,
  isIngresando,
  onRehomologar,
  onCopySap,
  onOpenSapConfig,
  onExport,
  onIngresar,
  onClose,
}: OcDetailActionsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {!esCM && (
        <button
          className="btn-secondary px-3 py-2 text-xs"
          onClick={onRehomologar}
          disabled={isRehomologating}
          title="Re-ejecuta el catalogo privado sobre las lineas sin itemcode"
        >
          <RefreshCw size={14} className={isRehomologating ? 'animate-spin' : ''} />
          {isRehomologating ? 'Homologando...' : 'Re-homologar'}
        </button>
      )}
      <button className="btn-primary px-3 py-2 text-xs" onClick={onCopySap}>
        <Copy size={14} />
        Copiar a SAP
      </button>
      <button className="btn-secondary px-3 py-2 text-xs" onClick={onOpenSapConfig}>
        <Settings size={14} />
        Ajustes SAP
      </button>
      <button className="btn-secondary px-3 py-2 text-xs" onClick={onExport}>
        <FileDown size={14} />
        Exportar Excel
      </button>
      <a
        href={`https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?codigoOC=${oc.codigo_oc}`}
        target="_blank"
        rel="noreferrer"
        className="btn-secondary px-3 py-2 text-xs"
        aria-label="Abrir OC en Mercado Publico"
      >
        <ExternalLink size={14} />
        Ver portal
      </a>
      <button
        className="btn-success px-3 py-2 text-xs"
        onClick={onIngresar}
        disabled={oc.estado_interno === 'Ingresada' || isIngresando}
      >
        <CheckSquare size={14} />
        {isIngresando ? 'Ingresando...' : 'Ingresar en SAP'}
      </button>
      <button className="btn-ghost px-3" onClick={onClose} aria-label="Cerrar panel">
        <X size={16} />
      </button>
    </div>
  )
})

export default OcDetailActions
