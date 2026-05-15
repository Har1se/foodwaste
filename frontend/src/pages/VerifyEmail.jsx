import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'

export default function VerifyEmail() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const [code, setCode] = useState('')
  const [email, setEmail] = useState(state?.email || '')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const handleVerify = async (e) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await authApi.verifyEmail({ email, code: code.trim() })
      setSuccess('Email подтверждён! Теперь вы можете войти.')
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Неверный или истёкший код')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    setError(''); setSuccess('')
    try {
      await authApi.resendVerification({ email })
      setSuccess('Код повторно отправлен на ' + email)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при отправке кода')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-5xl">📧</span>
          <h1 className="mt-3 text-2xl font-bold text-gray-900">Подтверждение email</h1>
          <p className="mt-1 text-sm text-gray-500">Введите 6-значный код из письма</p>
        </div>

        <form onSubmit={handleVerify} className="card p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" required value={email}
              onChange={e => setEmail(e.target.value)}
              className="input" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Код подтверждения</label>
            <input
              type="text" required maxLength={6} pattern="\d{6}"
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className="input text-center text-2xl tracking-widest font-mono"
              placeholder="123456"
            />
          </div>

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</p>}
          {success && <p className="text-sm text-brand-600 bg-brand-50 rounded-lg p-3">{success}</p>}

          <button type="submit" disabled={loading || code.length !== 6} className="btn-primary w-full">
            {loading ? 'Проверяем...' : 'Подтвердить'}
          </button>

          <button type="button" onClick={handleResend} className="btn-secondary w-full">
            Отправить код повторно
          </button>
        </form>
      </div>
    </div>
  )
}
