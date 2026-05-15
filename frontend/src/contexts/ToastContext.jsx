import { createContext, useCallback, useContext, useState } from 'react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const remove = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const add = useCallback((message, type = 'info') => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts((current) => [...current, { id, message, type }])
    setTimeout(() => remove(id), 4200)
  }, [remove])

  const toast = {
    success: (message) => add(message, 'success'),
    error: (message) => add(message, 'error'),
    info: (message) => add(message, 'info'),
  }

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-[200] flex w-full max-w-sm flex-col gap-2">
        {toasts.map((item) => (
          <div
            key={item.id}
            className={`pointer-events-auto rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${
              item.type === 'success'
                ? 'bg-emerald-600 text-white'
                : item.type === 'error'
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-900 text-white'
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="flex-1">{item.message}</span>
              <button type="button" className="text-white/70 hover:text-white" onClick={() => remove(item.id)}>
                x
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}
