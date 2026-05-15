import { useState } from 'react'

export function useConfirm() {
  const [state, setState] = useState(null)

  const confirm = (message, { title = 'Подтверждение', danger = false } = {}) =>
    new Promise((resolve) => setState({ message, title, danger, resolve }))

  const close = (result) => {
    state?.resolve(result)
    setState(null)
  }

  const dialog = state ? (
    <div className="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h3 className="text-lg font-semibold mb-2">{state.title}</h3>
        <p className="text-gray-600 mb-6 text-sm leading-relaxed">{state.message}</p>
        <div className="flex gap-3">
          <button
            onClick={() => close(true)}
            className={`flex-1 ${state.danger ? 'btn-danger' : 'btn-primary'}`}
          >
            Подтвердить
          </button>
          <button onClick={() => close(false)} className="btn-secondary flex-1">
            Отмена
          </button>
        </div>
      </div>
    </div>
  ) : null

  return { confirm, dialog }
}
