import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'

const ROLES = [
  { value: 'customer', label: 'Покупатель', description: 'Покупать еду со скидкой' },
  { value: 'vendor', label: 'Продавец', description: 'Публиковать продукты и заказы' },
]

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    email: '',
    password: 'Secure123!',
    confirm: 'Secure123!',
    full_name: '',
    phone: '',
    role: 'customer',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const setField = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    if (form.password !== form.confirm) {
      setError('Пароли не совпадают')
      return
    }
    setLoading(true)
    try {
      await authApi.register({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        phone: form.phone || undefined,
        role: form.role,
      })
      navigate('/login')
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось создать аккаунт')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <div className="mb-6">
        <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">Новый аккаунт</p>
        <h1 className="mt-2 text-3xl font-bold text-gray-950">Регистрация</h1>
        <p className="mt-2 text-sm text-gray-500">
          В demo-режиме email подтверждается автоматически, поэтому после регистрации можно сразу войти.
        </p>
      </div>

      <form onSubmit={submit} className="card space-y-5 p-6">
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">Роль</label>
          <div className="grid grid-cols-2 gap-3">
            {ROLES.map((role) => (
              <button
                key={role.value}
                type="button"
                onClick={() => setForm((current) => ({ ...current, role: role.value }))}
                className={`rounded-lg border p-4 text-left transition ${
                  form.role === role.value
                    ? 'border-emerald-600 bg-emerald-50'
                    : 'border-gray-200 hover:border-emerald-300'
                }`}
              >
                <div className="font-semibold text-gray-950">{role.label}</div>
                <div className="mt-1 text-xs text-gray-500">{role.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Имя</label>
          <input type="text" required className="input" value={form.full_name} onChange={setField('full_name')} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <input type="email" required className="input" value={form.email} onChange={setField('email')} placeholder="new-user@test.kz" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Телефон</label>
          <input type="tel" className="input" value={form.phone} onChange={setField('phone')} placeholder="+77000000000" />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Пароль</label>
            <input type="password" required className="input" value={form.password} onChange={setField('password')} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Повтор пароля</label>
            <input type="password" required className="input" value={form.confirm} onChange={setField('confirm')} />
          </div>
        </div>

        {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? 'Создаем...' : 'Создать аккаунт'}
        </button>

        <p className="text-center text-sm text-gray-500">
          Уже есть аккаунт? <Link to="/login" className="text-emerald-700 hover:underline">Войти</Link>
        </p>
      </form>
    </div>
  )
}
