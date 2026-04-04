import { useRef, useCallback, useState, useEffect, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react'

interface Column {
  id: string
  label: string
  align?: 'left' | 'right'
  minWidth?: number
  defaultWidth?: number
}

interface Props {
  columns: Column[]
  children: ReactNode
  storageKey?: string
}

/**
 * A table with resizable column headers.
 * Drag the right edge of any header to resize that column.
 * Column widths are persisted to localStorage if storageKey is provided.
 */
export default function ResizableTable({ columns, children, storageKey }: Props) {
  const [widths, setWidths] = useState<Record<string, number>>(() => {
    if (storageKey) {
      try {
        const saved = localStorage.getItem(`col-widths-${storageKey}`)
        if (saved) return JSON.parse(saved)
      } catch { /* ignore */ }
    }
    const init: Record<string, number> = {}
    columns.forEach(c => { init[c.id] = c.defaultWidth || 0 })
    return init
  })

  const activeRef = useRef<{ colId: string; startX: number; startW: number } | null>(null)

  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(`col-widths-${storageKey}`, JSON.stringify(widths))
    }
  }, [widths, storageKey])

  const onMouseDown = useCallback((e: ReactMouseEvent, colId: string, thEl: HTMLTableCellElement) => {
    e.preventDefault()
    e.stopPropagation()
    const startW = thEl.offsetWidth
    activeRef.current = { colId, startX: e.clientX, startW }

    const onMouseMove = (ev: MouseEvent) => {
      if (!activeRef.current) return
      const diff = ev.clientX - activeRef.current.startX
      const min = columns.find(c => c.id === activeRef.current!.colId)?.minWidth || 40
      const newW = Math.max(min, activeRef.current.startW + diff)
      setWidths(prev => ({ ...prev, [activeRef.current!.colId]: newW }))
    }

    const onMouseUp = () => {
      activeRef.current = null
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [columns])

  return (
    <table className="tbl" style={{ tableLayout: 'fixed', width: '100%' }}>
      <colgroup>
        {columns.map(c => (
          <col key={c.id} style={widths[c.id] ? { width: widths[c.id] } : undefined} />
        ))}
      </colgroup>
      <thead>
        <tr>
          {columns.map((c, index) => (
            <th
              key={c.id}
              className={c.align === 'right' ? 'text-right' : ''}
              style={{ position: 'relative', overflow: 'hidden' }}
            >
              {c.label}
              {index < columns.length - 1 && (
                <div
                  aria-hidden="true"
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: 8,
                    bottom: 8,
                    width: 1,
                    background: 'rgba(148, 163, 184, 0.22)',
                    pointerEvents: 'none',
                  }}
                />
              )}
              <div
                onMouseDown={(e) => {
                  const th = (e.target as HTMLElement).parentElement as HTMLTableCellElement
                  onMouseDown(e, c.id, th)
                }}
                style={{
                  position: 'absolute',
                  right: 0,
                  top: 0,
                  bottom: 0,
                  width: 5,
                  cursor: 'col-resize',
                  zIndex: 1,
                }}
                className="hover:bg-blue-500/20 transition-colors"
              />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {children}
      </tbody>
    </table>
  )
}
