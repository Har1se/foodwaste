import { useCallback, useEffect, useMemo, useState } from 'react'
import { listingsApi } from '../api/client'
import ListingCard from '../components/ListingCard'

const FILTERS = [
  { value: '', label: 'Все' },
  { value: 'active', label: 'В продаже' },
  { value: 'discounted', label: 'Скидки' },
  { value: 'free', label: 'Бесплатно' },
]

export default function Home() {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [nextCursor, setNextCursor] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)

  const loadListings = useCallback(async (cursor = null) => {
    const append = Boolean(cursor)
    append ? setLoadingMore(true) : setLoading(true)
    setError('')
    try {
      const { data } = await listingsApi.list({ cursor: cursor || undefined, limit: 16 })
      setListings((current) => append ? [...current, ...data.data] : data.data)
      setNextCursor(data.pagination.next_cursor || null)
    } catch {
      setError('Не удалось загрузить продукты. Проверьте, что backend запущен на http://localhost:8000.')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [])

  useEffect(() => {
    loadListings()
  }, [loadListings])

  const filtered = useMemo(() => listings.filter((item) => {
    const matchesStatus = !status || item.status === status
    const q = search.trim().toLowerCase()
    const matchesSearch = !q ||
      item.title.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q)
    return matchesStatus && matchesSearch
  }), [listings, search, status])

  const stats = useMemo(() => ({
    total: listings.length,
    available: listings.reduce((sum, item) => sum + item.quantity_available, 0),
    saved: listings.reduce((sum, item) => sum + Math.max(item.original_price - item.current_price, 0), 0),
  }), [listings])

  return (
    <div>
      <section className="border-b border-gray-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1fr_420px] lg:px-8">
          <div className="flex flex-col justify-center">
            <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">RescueBite Marketplace</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-bold leading-tight text-gray-950 sm:text-5xl">
              Покупайте свежую еду со скидкой до закрытия заведений.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-gray-600">
              Продавцы выкладывают готовые блюда, выпечку и наборы на сегодня. Покупатель бронирует, оплачивает и забирает заказ в указанное окно.
            </p>
            <div className="mt-7 grid max-w-xl grid-cols-3 gap-3">
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="text-2xl font-bold text-gray-950">{stats.total}</div>
                <div className="text-xs text-gray-500">позиций</div>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="text-2xl font-bold text-gray-950">{stats.available}</div>
                <div className="text-xs text-gray-500">порций</div>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="text-2xl font-bold text-gray-950">{stats.saved.toLocaleString()} ₸</div>
                <div className="text-xs text-gray-500">экономия</div>
              </div>
            </div>
          </div>
          <div className="min-h-[260px] overflow-hidden rounded-lg bg-gray-100">
            <img
              src="https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=85"
              alt="Готовая еда на столе"
              className="h-full w-full object-cover"
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center">
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="input max-w-md"
            placeholder="Поиск: суши, выпечка, салат..."
          />
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={`rounded-lg border px-4 py-2 text-sm font-medium transition ${
                  status === filter.value
                    ? 'border-emerald-600 bg-emerald-600 text-white'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-emerald-300'
                }`}
                onClick={() => setStatus(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>
          <button type="button" className="btn-secondary lg:ml-auto" onClick={() => loadListings()}>
            Обновить
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={index} className="h-[430px] animate-pulse rounded-lg bg-gray-100" />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
            {error}
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-white p-10 text-center">
            <h2 className="text-lg font-semibold text-gray-950">Пока нет подходящих продуктов</h2>
            <p className="mt-2 text-sm text-gray-500">Запустите seed или создайте продукт в кабинете продавца.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map((listing) => (
              <ListingCard key={listing.id} listing={listing} onOrderPlaced={() => loadListings()} />
            ))}
          </div>
        )}

        {nextCursor && !loading && (
          <div className="mt-8 text-center">
            <button type="button" className="btn-secondary" disabled={loadingMore} onClick={() => loadListings(nextCursor)}>
              {loadingMore ? 'Загружаем...' : 'Показать еще'}
            </button>
          </div>
        )}
      </section>
    </div>
  )
}
