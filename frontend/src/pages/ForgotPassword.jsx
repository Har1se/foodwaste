import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [step, setStep] = useState(1) // 1 = enter email, 2 = enter code + new password
  const [form, setForm] = useState({ code: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSendCode = async (e) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await authApi.forgotPassword({ email })
      setStep(2)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при отправке письма')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) { setError('Пароли не совпадают'); return }
    setLoading(true); setError('')
    try {
      await authApi.resetPassword({ email, code: form.code, new_password: form.password })
      navigate('/login', { state: { message: 'Пароль успешно изменён! Войдите с новым паролем.' } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Неверный или истёкший код')
    } finally {
      setLoading(false)
    }
  }

  if (step === 1) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <span className="text-5xl">🔑</span>
            <h1 className="mt-3 text-2xl font-bold text-gray-900">Сброс пароля</h1>
            <p className="mt-1 text-sm text-gray-500">Введите email — пришлём 6-значный код на почту</p>
          </div>
          <form onSubmit={handleSendCode} className="card p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email" required value={email}
                onChange={e => setEmail(e.target.value)}
                className="input" placeholder="you@example.com"
              />
            </div>
            {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Отправляем...' : 'Отправить код'}
            </button>
            <Link to="/login" className="block text-center text-sm text-brand-600 hover:underline">
              Вернуться к входу
            </Link>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-5xl">📨</span>
          <h1 className="mt-3 text-2xl font-bold text-gray-900">Введите код</h1>
          <p className="mt-1 text-sm text-gray-500">
            Мы отправили 6-значный код на <strong>{email}</strong>
          </p>
        </div>
        <form onSubmit={handleReset} className="card p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Код из письма</label>
            <input
              type="text" required maxLength={6} inputMode="numeric"
              value={form.code}
              onChange={e => setForm(p => ({ ...p, code: e.target.value.replace(/\D/g, '') }))}
              className="input text-center text-2xl tracking-widest font-bold"
              placeholder="123456"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Новый пароль</label>
            <input
              type="password" required minLength={8}
              value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
              className="input" placeholder="Минимум 8 символов"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Повторите пароль</label>
            <input
              type="password" required
              value={form.confirm}
              onChange={e => setForm(p => ({ ...p, confirm: e.target.value }))}
              className="input" placeholder="••••••••"
            />
          </div>
          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Сохраняем...' : 'Сохранить новый пароль'}
          </button>
          <button
            type="button"
            onClick={() => { setStep(1); setError('') }}
            className="block w-full text-center text-sm text-brand-600 hover:underline"
          >
            Отправить код повторно
          </button>
        </form>
      </div>
    </div>
  )
}


export function ResetPassword() {
  const navigate = useNavigate()
  useEffect(() => { navigate('/forgot-password', { replace: true }) }, [])
  return null
}
