import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef({})

  const remove = useCallback((id) => {
    setToasts((cur) => cur.filter((t) => t.id !== id))
    if (timers.current[id]) {
      clearTimeout(timers.current[id])
      delete timers.current[id]
    }
  }, [])

  const add = useCallback((message, type = 'info') => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts((cur) => [...cur, { id, message, type }])
    timers.current[id] = setTimeout(() => remove(id), 4200)
  }, [remove])

  // Clear all timers on unmount to prevent memory leaks
  useEffect(() => {
    const t = timers.current
    return () => { Object.values(t).forEach(clearTimeout) }
  }, [])

  const toast = {
    success: (msg) => add(msg, 'success'),
    error:   (msg) => add(msg, 'error'),
    info:    (msg) => add(msg, 'info'),
  }

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="pointer-events-none fixed right-4 top-20 z-[200] flex w-full max-w-[340px] flex-col gap-2">
        {toasts.map((item) => (
          <div
            key={item.id}
            className={`pointer-events-auto flex items-start gap-3 rounded-2xl px-4 py-3.5 text-sm font-medium shadow-lg border animate-fade-in ${
              item.type === 'success'
                ? 'bg-brand-600 border-brand-700 text-white'
                : item.type === 'error'
                  ? 'bg-red-600 border-red-700 text-white'
                  : 'bg-gray-900 border-gray-800 text-white'
            }`}
          >
            <span className="text-base leading-none mt-0.5">
              {item.type === 'success' ? '✓' : item.type === 'error' ? '✕' : 'ℹ'}
            </span>
            <span className="flex-1 leading-snug">{item.message}</span>
            <button
              type="button"
              className="text-white/60 hover:text-white leading-none text-base ml-1"
              onClick={() => remove(item.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
