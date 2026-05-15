import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const DEMO_USERS = [
  { label: 'Покупатель', email: 'customer@test.kz', password: 'Secure123!' },
  { label: 'Продавец', email: 'vendor@test.kz', password: 'Secure123!' },
  { label: 'Админ', email: 'admin@test.kz', password: 'Secure123!' },
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: 'customer@test.kz', password: 'Secure123!' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(form.email, form.password)
      if (user.role === 'admin') navigate('/admin')
      else if (user.role === 'vendor') navigate('/vendor')
      else navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось войти. Проверьте email и пароль.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto grid min-h-[calc(100vh-64px)] max-w-6xl items-center gap-8 px-4 py-10 lg:grid-cols-[1fr_420px]">
      <div className="hidden lg:block">
        <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">Demo access</p>
        <h1 className="mt-3 text-4xl font-bold text-gray-950">Войдите и проверьте весь путь покупки.</h1>
        <p className="mt-4 max-w-xl text-gray-600">
          Для демо доступны роли покупателя, продавца и администратора. В development-режиме email уже подтверждается автоматически.
        </p>
      </div>

      <form onSubmit={submit} className="card p-6">
        <h2 className="text-xl font-bold text-gray-950">Вход</h2>
        <p className="mt-1 text-sm text-gray-500">Выберите demo-пользователя или введите свои данные.</p>

        <div className="mt-5 grid grid-cols-3 gap-2">
          {DEMO_USERS.map((user) => (
            <button
              key={user.email}
              type="button"
              className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-medium hover:border-emerald-300 hover:bg-emerald-50"
              onClick={() => setForm({ email: user.email, password: user.password })}
            >
              {user.label}
            </button>
          ))}
        </div>

        <div className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              required
              className="input"
              value={form.email}
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Пароль</label>
            <input
              type="password"
              required
              className="input"
              value={form.password}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            />
          </div>
        </div>

        {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        <button type="submit" className="btn-primary mt-5 w-full" disabled={loading}>
          {loading ? 'Входим...' : 'Войти'}
        </button>

        <div className="mt-4 flex justify-between text-sm">
          <Link to="/forgot-password" className="text-emerald-700 hover:underline">Забыли пароль?</Link>
          <Link to="/register" className="text-emerald-700 hover:underline">Создать аккаунт</Link>
        </div>
      </form>
    </div>
  )
}
