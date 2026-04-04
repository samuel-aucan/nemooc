import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { ChevronDown, ListFilter } from 'lucide-react'

interface Props {
  options: string[]
  value: string[]
  onChange: (v: string[]) => void
  placeholder?: string
  className?: string
}

export default function MultiSelect({
  options,
  value,
  onChange,
  placeholder = 'Todos',
  className = '',
}: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const checkboxRefs = useRef<Array<HTMLInputElement | null>>([])
  const buttonId = useId()
  const panelId = useId()

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onEscape)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onEscape)
    }
  }, [])

  const summary = useMemo(() => {
    if (value.length === 0) return placeholder
    if (value.length === 1) return value[0]
    return `${value.length} seleccionados`
  }, [placeholder, value])

  const toggle = (option: string) => {
    const next = value.includes(option)
      ? value.filter((entry) => entry !== option)
      : [...value, option]
    onChange(next)
  }

  const focusFirstOption = () => {
    window.requestAnimationFrame(() => checkboxRefs.current[0]?.focus())
  }

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        id={buttonId}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' && !open) {
            event.preventDefault()
            setOpen(true)
            focusFirstOption()
          }
        }}
        className="select flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="flex min-w-0 items-center gap-2">
          <ListFilter size={14} className="shrink-0 text-gray-500" />
          <span className={value.length === 0 ? 'truncate text-gray-500' : 'truncate text-gray-100'}>
            {summary}
          </span>
        </span>
        <ChevronDown
          size={14}
          className={`shrink-0 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-labelledby={buttonId}
          className="absolute z-50 mt-2 min-w-full rounded-xl border border-gray-700 bg-gray-950 shadow-2xl"
        >
          <div className="border-b border-gray-800 px-3 py-2 text-xs text-gray-400">
            {options.length > 0
              ? 'Selecciona una o varias opciones'
              : 'No hay opciones disponibles'}
          </div>

          <div className="max-h-64 overflow-y-auto p-2">
            {options.map((option, index) => (
              <label
                key={option}
                className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-sm text-gray-200 transition-colors hover:bg-gray-900"
              >
                <input
                  ref={(element) => {
                    checkboxRefs.current[index] = element
                  }}
                  type="checkbox"
                  checked={value.includes(option)}
                  onChange={() => toggle(option)}
                  className="rounded border-gray-600 bg-gray-900 accent-[rgb(var(--accent-500))]"
                />
                <span className="truncate">{option}</span>
              </label>
            ))}
          </div>

          <div className="flex items-center justify-between border-t border-gray-800 px-3 py-2">
            <span className="text-xs text-gray-500">
              {value.length === 0 ? 'Sin filtros activos' : `${value.length} filtro(s) activos`}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="text-xs text-gray-500 transition-colors hover:text-gray-300"
                onClick={() => onChange(options)}
              >
                Todos
              </button>
              <button
                type="button"
                className="text-xs text-gray-500 transition-colors hover:text-gray-300"
                onClick={() => {
                  onChange([])
                  setOpen(false)
                }}
              >
                Limpiar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
