import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { ordersApi } from '../api/client'
import { ALLERGEN_LABELS, LISTING_STATUS_COLORS, LISTING_STATUS_LABELS } from '../utils/constants'

const FALLBACK = [
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80',
  'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=900&q=80',
  'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=900&q=80',
  'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80',
]

const CartIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
  </svg>
)

const ClockIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 shrink-0">
    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
  </svg>
)

const CheckIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
)

const formatTime = (iso) => {
  const d = new Date(iso)
  const now = new Date()
  const sameYear = d.getFullYear() === now.getFullYear()
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: 'short',
    ...(sameYear ? {} : { year: 'numeric' }),
    hour: '2-digit', minute: '2-digit',
  })
}

export default function ListingCard({ listing, onOrderPlaced }) {
  const { user } = useAuth()
  const toast = useToast()
  const [qty, setQty] = useState(1)
  const [loading, setLoading] = useState(false)
  const [ordered, setOrdered] = useState(false)
  const [imgSrc, setImgSrc] = useState(listing.photo_url || FALLBACK[listing.id % FALLBACK.length])

  const image = imgSrc
  const canOrder = user?.role === 'customer' &&
    ['active', 'discounted', 'free'].includes(listing.status) &&
    listing.quantity_available > 0

  const discount = listing.original_price > 0
    ? Math.round((1 - listing.current_price / listing.original_price) * 100)
    : 0

  const allergens = (listing.allergens || []).filter((a) => a !== 'none')

  const placeOrder = async () => {
    setLoading(true)
    try {
      await ordersApi.create({ items: [{ listing_id: listing.id, quantity: qty }] })
      setOrdered(true)
      toast.success('Заказ оформлен! Смотрите в "Заказы".')
      onOrderPlaced?.()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось оформить заказ')
    } finally {
      setLoading(false)
    }
  }

  return (
    <article className="card group flex flex-col overflow-hidden transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5">
      {/* Image */}
      <div className="relative overflow-hidden bg-gray-100" style={{ paddingTop: '66%' }}>
        <img
          src={image}
          alt={listing.title}
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          loading="lazy"
          onError={() => setImgSrc(FALLBACK[listing.id % FALLBACK.length])}
        />
        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent" />

        {/* Status badge top-left */}
        <div className="absolute left-3 top-3">
          <span className={`badge shadow-sm ${LISTING_STATUS_COLORS[listing.status] || 'bg-gray-100 text-gray-700'}`}>
            {LISTING_STATUS_LABELS[listing.status] || listing.status}
          </span>
        </div>

        {/* Discount badge top-right */}
        {discount >= 10 && listing.current_price > 0 && (
          <div className="absolute right-3 top-3">
            <span className="badge bg-rose-500 text-white shadow-sm">-{discount}%</span>
          </div>
        )}

        {/* FREE badge */}
        {listing.status === 'free' && (
          <div className="absolute inset-x-0 bottom-0 bg-sky-500 py-1 text-center text-xs font-bold uppercase tracking-wider text-white">
            Бесплатно
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-1 flex-col gap-2.5 p-4">
        <div>
          <h3 className="line-clamp-1 text-[15px] font-semibold text-gray-900 leading-snug">{listing.title}</h3>
          <p className="mt-1 line-clamp-2 text-sm text-gray-700 leading-relaxed min-h-[40px]">{listing.description}</p>
        </div>

        {/* Price */}
        <div className="flex items-baseline gap-2">
          <span className={`text-xl font-bold ${listing.current_price === 0 ? 'text-sky-600' : 'text-brand-600'}`}>
            {listing.current_price === 0 ? 'Бесплатно' : `${listing.current_price.toLocaleString()} ₸`}
          </span>
          {listing.current_price !== listing.original_price && listing.current_price > 0 && (
            <span className="text-sm text-gray-500 line-through">{listing.original_price.toLocaleString()} ₸</span>
          )}
          <span className="ml-auto text-xs font-semibold text-gray-600">
            осталось {listing.quantity_available}
          </span>
        </div>

        {/* Allergens */}
        {allergens.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {allergens.slice(0, 4).map((code) => (
              <span key={code} className="badge border border-amber-200 bg-amber-50 text-amber-700 text-[10px]">
                ⚠ {ALLERGEN_LABELS[code] || code}
              </span>
            ))}
            {allergens.length > 4 && (
              <span className="badge border border-gray-200 bg-gray-50 text-gray-500 text-[10px]">+{allergens.length - 4}</span>
            )}
          </div>
        )}

        {/* Pickup window */}
        <div className="flex items-center gap-1.5 text-xs text-gray-600 border-t border-gray-100 pt-2.5">
          <ClockIcon />
          <span>{formatTime(listing.pickup_window_start)} — {formatTime(listing.pickup_window_end)}</span>
        </div>

        {/* Order action */}
        {canOrder && !ordered && (
          <div className="flex gap-2 pt-0.5">
            <input
              type="number"
              min="1"
              max={Math.min(listing.quantity_available, 20)}
              value={qty}
              onChange={(e) => {
                const v = Number(e.target.value)
                setQty(Math.max(1, Math.min(listing.quantity_available, v || 1)))
              }}
              className="input w-16 text-center px-2 py-2"
            />
            <button
              type="button"
              className="btn-primary flex-1"
              disabled={loading}
              onClick={placeOrder}
            >
              {loading ? (
                <span className="flex items-center gap-1.5">
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Оформляем...
                </span>
              ) : (
                <span className="flex items-center gap-1.5"><CartIcon /> Заказать</span>
              )}
            </button>
          </div>
        )}

        {ordered && (
          <div className="flex items-center justify-center gap-2 rounded-xl bg-brand-50 border border-brand-100 py-2.5 text-sm font-semibold text-brand-700">
            <CheckIcon /> Заказ оформлен
          </div>
        )}

        {!user && (
          <Link to="/login" className="btn-secondary w-full text-center">
            Войти, чтобы заказать
          </Link>
        )}

        {user?.role === 'vendor' && (
          <div className="flex items-center justify-center rounded-xl bg-gray-50 border border-gray-100 py-2 text-xs text-gray-600">
            Просмотр продавца
          </div>
        )}
      </div>
    </article>
  )
}
