import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { auctionsApi } from '../api/client'

function timeLeft(endsAt) {
  const diff = new Date(endsAt) - new Date()
  if (diff <= 0) return 'Завершён'
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  if (h > 0) return `${h}ч ${m}м`
  if (m > 0) return `${m}м ${s}с`
  return `${s}с`
}

function AuctionCard({ auction, onBidPlaced }) {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [bidAmount, setBidAmount] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [timeStr, setTimeStr] = useState(timeLeft(auction.ends_at))

  useEffect(() => {
    const id = setInterval(() => setTimeStr(timeLeft(auction.ends_at)), 1000)
    return () => clearInterval(id)
  }, [auction.ends_at])

  const isEnded = auction.status !== 'active'
  const isExpired = new Date(auction.ends_at) <= new Date()

  const handleBid = async (e) => {
    e.preventDefault()
    const amount = parseInt(bidAmount, 10)
    if (!amount || amount < auction.reserve_price) {
      showToast(`Минимальная ставка: ${auction.reserve_price.toLocaleString('ru')} ₸`, 'error')
      return
    }
    if (amount > auction.start_price) {
      showToast(`Максимальная ставка: ${auction.start_price.toLocaleString('ru')} ₸`, 'error')
      return
    }
    setSubmitting(true)
    try {
      await auctionsApi.bid(auction.id, { amount })
      showToast(`Ставка ${amount.toLocaleString('ru')} ₸ принята!`, 'success')
      setBidAmount('')
      onBidPlaced?.()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Ошибка при ставке', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const statusColor = {
    active: 'bg-green-100 text-green-700',
    ended: 'bg-gray-100 text-gray-600',
    cancelled: 'bg-red-100 text-red-600',
    pending: 'bg-yellow-100 text-yellow-700',
  }[auction.status] || 'bg-gray-100 text-gray-600'

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <h3 className="font-bold text-gray-900 text-sm">Лот #{auction.listing_id}</h3>
          <p className="text-xs text-gray-500 mt-0.5">Аукцион #{auction.id}</p>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusColor}`}>
          {auction.status === 'active' ? 'Активен' :
           auction.status === 'ended' ? 'Завершён' :
           auction.status === 'pending' ? 'Ожидание' : 'Отменён'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="rounded-xl bg-gray-50 p-3">
          <div className="text-xs text-gray-500 mb-1">Стартовая цена</div>
          <div className="font-bold text-gray-900">{auction.start_price.toLocaleString('ru')} ₸</div>
        </div>
        <div className="rounded-xl bg-gray-50 p-3">
          <div className="text-xs text-gray-500 mb-1">Резервная цена</div>
          <div className="font-bold text-brand-600">{auction.reserve_price.toLocaleString('ru')} ₸</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm mb-4">
        <span className="flex items-center gap-1.5 text-gray-600">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          {auction.bid_count} ставок
        </span>
        {!isEnded && !isExpired && (
          <span className={`font-mono font-bold ${parseInt(timeStr) < 60 ? 'text-red-600 animate-pulse' : 'text-orange-500'}`}>
            ⏱ {timeStr}
          </span>
        )}
      </div>

      {auction.status === 'ended' && auction.winner_user_id && (
        <div className="rounded-xl bg-brand-50 border border-brand-200 p-3 mb-4 text-center">
          <div className="text-xs text-brand-600 font-semibold mb-1">Победитель</div>
          <div className="text-lg font-bold text-brand-700">
            {auction.winning_bid_amount?.toLocaleString('ru')} ₸
          </div>
        </div>
      )}

      {user && !isEnded && !isExpired && (
        <form onSubmit={handleBid} className="flex gap-2">
          <input
            type="number"
            value={bidAmount}
            onChange={(e) => setBidAmount(e.target.value)}
            min={auction.reserve_price}
            max={auction.start_price}
            placeholder={`Ставка (мин. ${auction.reserve_price.toLocaleString('ru')} ₸)`}
            className="input flex-1 text-sm"
            required
          />
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary text-sm px-4 whitespace-nowrap"
          >
            {submitting ? '...' : 'Ставка'}
          </button>
        </form>
      )}

      {!user && !isEnded && (
        <p className="text-center text-sm text-gray-500">
          <a href="/login" className="text-brand-600 font-semibold hover:underline">Войдите</a>, чтобы сделать ставку
        </p>
      )}
    </div>
  )
}

export default function Auctions() {
  const [auctions, setAuctions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAll, setShowAll] = useState(false)

  const loadAuctions = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await auctionsApi.list({ active_only: !showAll })
      setAuctions(data)
    } catch {
      setError('Не удалось загрузить аукционы. Проверьте, что backend запущен.')
    } finally {
      setLoading(false)
    }
  }, [showAll])

  useEffect(() => { loadAuctions() }, [loadAuctions])

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900">Аукционы</h1>
            <p className="mt-1 text-gray-500">
              Обратный аукцион — побеждает самая низкая уникальная ставка
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={showAll}
                onChange={(e) => setShowAll(e.target.checked)}
                className="rounded"
              />
              Показать завершённые
            </label>
            <button
              type="button"
              onClick={loadAuctions}
              className="btn-secondary text-sm"
            >
              Обновить
            </button>
          </div>
        </div>

        {/* How it works */}
        <div className="mt-6 rounded-2xl border border-brand-200 bg-brand-50 p-5">
          <h3 className="font-bold text-brand-800 mb-3">Как работает обратный аукцион?</h3>
          <div className="grid gap-3 sm:grid-cols-3 text-sm text-brand-700">
            <div className="flex gap-2.5">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white text-xs font-bold">1</span>
              <p>Продавец создаёт аукцион с начальной ценой и резервной ценой</p>
            </div>
            <div className="flex gap-2.5">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white text-xs font-bold">2</span>
              <p>Покупатели делают ставки — чем ниже ставка, тем лучше</p>
            </div>
            <div className="flex gap-2.5">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white text-xs font-bold">3</span>
              <p>Побеждает самая низкая <strong>уникальная</strong> ставка (которую сделал только один участник)</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-64 rounded-2xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
          <div className="text-3xl mb-3">⚠️</div>
          <p className="font-semibold text-red-700">{error}</p>
        </div>
      ) : auctions.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-white p-16 text-center">
          <div className="text-5xl mb-4">🔨</div>
          <h3 className="text-lg font-semibold text-gray-900">Нет активных аукционов</h3>
          <p className="mt-2 text-sm text-gray-500">Продавцы ещё не создали аукционы</p>
          {!showAll && (
            <button
              type="button"
              className="btn-secondary mt-4 text-sm"
              onClick={() => setShowAll(true)}
            >
              Показать завершённые
            </button>
          )}
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {auctions.map((auction) => (
            <AuctionCard key={auction.id} auction={auction} onBidPlaced={loadAuctions} />
          ))}
        </div>
      )}

      {!loading && auctions.length > 0 && (
        <p className="mt-6 text-center text-sm text-gray-400">
          {auctions.length} аукцион{auctions.length !== 1 ? 'а' : ''}
        </p>
      )}
    </div>
  )
}
