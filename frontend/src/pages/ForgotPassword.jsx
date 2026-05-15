import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await authApi.forgotPassword({ email })
      setSent(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при отправке письма')
    } finally {
      setLoading(false)
    }
  }

  if (sent) return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center">
        <span className="text-5xl">✉️</span>
        <h1 className="mt-3 text-2xl font-bold text-gray-900">Письмо отправлено!</h1>
        <p className="mt-2 text-gray-500 max-w-sm">
          Если email <strong>{email}</strong> зарегистрирован, на него придёт ссылка для сброса пароля.
        </p>
        <Link to="/login" className="mt-6 btn-primary inline-block">Вернуться к входу</Link>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-5xl">🔑</span>
          <h1 className="mt-3 text-2xl font-bold text-gray-900">Сброс пароля</h1>
          <p className="mt-1 text-sm text-gray-500">Введите email — пришлём ссылку для сброса</p>
        </div>
        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" required value={email}
              onChange={e => setEmail(e.target.value)}
              className="input" placeholder="you@example.com" />
          </div>
          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Отправляем...' : 'Отправить ссылку'}
          </button>
          <Link to="/login" className="block text-center text-sm text-brand-600 hover:underline">
            Вернуться к входу
          </Link>
        </form>
      </div>
    </div>
  )
}


export function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''
  const [form, setForm] = useState({ password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.confirm) { setError('Пароли не совпадают'); return }
    setLoading(true); setError('')
    try {
      await authApi.resetPassword({ token, new_password: form.password })
      navigate('/login', { state: { message: 'Пароль успешно изменён' } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Неверный или истёкший токен')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-5xl">🔐</span>
          <h1 className="mt-3 text-2xl font-bold text-gray-900">Новый пароль</h1>
        </div>
        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Новый пароль</label>
            <input type="password" required minLength={8}
              value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
              className="input" placeholder="Минимум 8 символов" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Повторите пароль</label>
            <input type="password" required
              value={form.confirm}
              onChange={e => setForm(p => ({ ...p, confirm: e.target.value }))}
              className="input" placeholder="••••••••" />
          </div>
          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Сохраняем...' : 'Сохранить пароль'}
          </button>
        </form>
      </div>
    </div>
  )
}
