import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { ordersApi } from '../api/client'
import { ALLERGEN_LABELS, LISTING_STATUS_COLORS, LISTING_STATUS_LABELS } from '../utils/constants'

const FALLBACK_IMAGES = [
  'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=900&q=80',
  'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=900&q=80',
  'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80',
  'https://images.unsplash.com/photo-1482049016688-2d3e1b311543?auto=format&fit=crop&w=900&q=80',
]

export default function ListingCard({ listing, onOrderPlaced }) {
  const { user } = useAuth()
  const toast = useToast()
  const [quantity, setQuantity] = useState(1)
  const [loading, setLoading] = useState(false)
  const [ordered, setOrdered] = useState(false)

  const image = listing.photo_url || FALLBACK_IMAGES[listing.id % FALLBACK_IMAGES.length]
  const canOrder = user?.role === 'customer' &&
    ['active', 'discounted', 'free'].includes(listing.status) &&
    listing.quantity_available > 0
  const discount = listing.original_price > 0
    ? Math.round((1 - listing.current_price / listing.original_price) * 100)
    : 0

  const placeOrder = async () => {
    setLoading(true)
    try {
      await ordersApi.create({ items: [{ listing_id: listing.id, quantity }] })
      setOrdered(true)
      toast.success('Заказ создан. Он появился в разделе "Мои заказы".')
      onOrderPlaced?.()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Не удалось оформить заказ')
    } finally {
      setLoading(false)
    }
  }

  return (
    <article className="card flex min-h-[430px] flex-col overflow-hidden">
      <div className="relative aspect-[4/3] bg-gray-100">
        <img src={image} alt={listing.title} className="h-full w-full object-cover" />
        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          <span className={`badge ${LISTING_STATUS_COLORS[listing.status] || 'bg-gray-100 text-gray-700'}`}>
            {LISTING_STATUS_LABELS[listing.status] || listing.status}
          </span>
          {discount > 0 && listing.current_price > 0 && (
            <span className="badge bg-red-600 text-white">-{discount}%</span>
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3 className="line-clamp-1 text-base font-semibold text-gray-950">{listing.title}</h3>
          <p className="mt-1 line-clamp-2 min-h-[40px] text-sm text-gray-500">{listing.description}</p>
        </div>

        <div className="flex items-end gap-2">
          <span className="text-2xl font-bold text-emerald-700">
            {listing.current_price === 0 ? '0 ₸' : `${listing.current_price.toLocaleString()} ₸`}
          </span>
          {listing.current_price !== listing.original_price && (
            <span className="pb-1 text-sm text-gray-400 line-through">
              {listing.original_price.toLocaleString()} ₸
            </span>
          )}
          <span className="ml-auto pb-1 text-xs text-gray-500">
            осталось {listing.quantity_available}
          </span>
        </div>

        {listing.allergens?.length > 0 && !listing.allergens.includes('none') && (
          <div className="flex flex-wrap gap-1">
            {listing.allergens.map((code) => (
              <span key={code} className="badge border border-amber-200 bg-amber-50 text-amber-700">
                {ALLERGEN_LABELS[code] || code}
              </span>
            ))}
          </div>
        )}

        <div className="mt-auto border-t border-gray-100 pt-3 text-xs text-gray-500">
          Забрать: {new Date(listing.pickup_window_start).toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
          {' - '}
          {new Date(listing.pickup_window_end).toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
        </div>

        {canOrder && !ordered && (
          <div className="grid grid-cols-[82px_1fr] gap-2">
            <input
              type="number"
              min="1"
              max={listing.quantity_available}
              value={quantity}
              onChange={(event) => {
                const next = Number(event.target.value)
                setQuantity(Math.max(1, Math.min(listing.quantity_available, next || 1)))
              }}
              className="input text-center"
            />
            <button type="button" className="btn-primary" disabled={loading} onClick={placeOrder}>
              {loading ? 'Оформляем...' : 'Заказать'}
            </button>
          </div>
        )}

        {ordered && (
          <div className="rounded-lg bg-emerald-50 px-3 py-2 text-center text-sm font-medium text-emerald-700">
            Заказ оформлен
          </div>
        )}

        {!user && (
          <Link to="/login" className="btn-secondary w-full">
            Войти, чтобы заказать
          </Link>
        )}
      </div>
    </article>
  )
}
