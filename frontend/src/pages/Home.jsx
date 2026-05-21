import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listingsApi } from '../api/client'
import ListingCard from '../components/ListingCard'

const CATEGORIES = [
  { value: '',           label: 'Всё меню',   emoji: '🍽' },
  { value: 'sushi',     label: 'Суши',        emoji: '🍣' },
  { value: 'hot',       label: 'Горячее',     emoji: '🍜' },
  { value: 'burger',    label: 'Бургеры',     emoji: '🍔' },
  { value: 'asian',     label: 'Азия',        emoji: '🥢' },
  { value: 'bakery',    label: 'Выпечка',     emoji: '🥐' },
  { value: 'dessert',   label: 'Десерты',     emoji: '🎂' },
  { value: 'salad',     label: 'Боулы',       emoji: '🥗' },
  { value: 'drinks',    label: 'Напитки',     emoji: '🥤' },
  { value: 'free',      label: 'Бесплатно',   emoji: '🎁' },
]


const SparkleIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
    <path d="M12 2l1.68 5.17L19 9l-5.32 1.83L12 16l-1.68-5.17L5 9l5.32-1.83L12 2z"/>
  </svg>
)

const LeafIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
    <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/>
    <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
  </svg>
)

const RefreshIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
    <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
)

export default function Home() {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [nextCursor, setNextCursor] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)

  const loadListings = useCallback(async (cursor = null) => {
    const append = Boolean(cursor)
    append ? setLoadingMore(true) : setLoading(true)
    setError('')
    try {
      const { data } = await listingsApi.list({ cursor: cursor || undefined, limit: 20, category: category || undefined })
      setListings((cur) => append ? [...cur, ...data.data] : data.data)
      setNextCursor(data.pagination.next_cursor || null)
    } catch {
      setError('Не удалось загрузить продукты. Проверьте, что backend запущен на http://localhost:8000.')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [category])

  useEffect(() => { loadListings() }, [loadListings])

  const filtered = useMemo(() => listings.filter((item) => {
    const q = search.trim().toLowerCase()
    return !q || item.title.toLowerCase().includes(q) || item.description.toLowerCase().includes(q)
  }), [listings, search])

  const stats = useMemo(() => ({
    total: listings.length,
    available: listings.filter((i) => i.quantity_available > 0).length,
    saving: listings.reduce((s, i) => s + Math.max(i.original_price - i.current_price, 0), 0),
  }), [listings])

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #052e16 0%, #14532d 50%, #15803d 100%)' }}>
        <div className="absolute inset-0 opacity-10"
          style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }}
        />
        <div className="relative mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
          <div className="grid gap-10 lg:grid-cols-[1fr_460px] lg:gap-16 items-center">
            <div className="animate-fade-in">
              <div className="inline-flex items-center gap-2 rounded-full border border-brand-700/40 bg-brand-900/50 px-4 py-1.5 text-sm font-semibold text-brand-300 mb-6">
                <SparkleIcon /> Спасаем еду — экономим деньги
              </div>
              <h1 className="text-4xl font-extrabold leading-tight text-white sm:text-5xl lg:text-[3.5rem]">
                Свежая еда<br />
                <span className="text-brand-400">со скидкой до 70%</span><br />
                у вас поблизости
              </h1>
              <p className="mt-5 max-w-lg text-[16px] leading-7 text-brand-200/90">
                Рестораны и кафе выкладывают готовые блюда по сниженным ценам до закрытия.
                Бронируйте, оплачивайте и забирайте — без лишней еды в мусоре.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/register" className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-brand-800 shadow-lg hover:bg-brand-50 transition-all duration-150 active:scale-95">
                  Начать покупать →
                </Link>
                <a href="#listings" className="inline-flex items-center gap-2 rounded-xl border border-brand-600/50 bg-brand-900/40 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-800/50 transition-all duration-150">
                  <LeafIcon /> Смотреть продукты
                </a>
              </div>

              {/* Stats */}
              {!loading && (
                <div className="mt-10 grid grid-cols-3 gap-3 max-w-sm">
                  {[
                    { value: stats.total, label: 'позиций' },
                    { value: stats.available, label: 'доступно' },
                    { value: `${Math.round(stats.saving / 1000)}k ₸`, label: 'экономия' },
                  ].map(({ value, label }) => (
                    <div key={label} className="rounded-xl bg-white/10 border border-white/10 p-3 backdrop-blur-sm text-center">
                      <div className="text-xl font-extrabold text-white">{value}</div>
                      <div className="text-xs text-brand-300 mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Hero image */}
            <div className="hidden lg:block">
              <div className="relative rounded-2xl overflow-hidden shadow-2xl border border-white/10">
                <img
                  src="https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=85"
                  alt="Вкусная еда"
                  className="w-full object-cover aspect-[4/3]"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-brand-950/40 to-transparent" />
                <div className="absolute bottom-4 left-4 right-4">
                  <div className="flex items-center gap-3 rounded-xl bg-white/95 backdrop-blur-sm p-3 shadow-lg">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600">
                      <LeafIcon />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-gray-900">Green Cafe</div>
                      <div className="text-xs text-gray-500">Свежие продукты со скидкой 40%</div>
                    </div>
                    <div className="ml-auto text-base font-bold text-brand-600">-40%</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Listings */}
      <section id="listings" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        {/* Category tabs */}
        <div className="mb-6 flex flex-wrap gap-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setCategory(cat.value)}
              className={`flex items-center gap-1.5 rounded-xl border px-4 py-2 text-sm font-semibold transition-all duration-150 ${
                category === cat.value
                  ? 'border-brand-600 bg-brand-600 text-white shadow-sm'
                  : 'border-gray-300 bg-white text-gray-800 hover:border-brand-400 hover:text-brand-700'
              }`}
            >
              <span>{cat.emoji}</span> {cat.label}
            </button>
          ))}
        </div>

        {/* Search + refresh */}
        <div className="mb-6 flex gap-3">
          <div className="relative flex-1 max-w-md">
            <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
              placeholder="Суши, выпечка, бургер..."
            />
          </div>
          <button type="button" className="btn-secondary" onClick={() => loadListings()}>
            <RefreshIcon /> Обновить
          </button>
        </div>

        {/* Section header */}
        <div className="mb-5 flex items-center justify-between">
          <h2 className="section-title">
            {category ? CATEGORIES.find((c) => c.value === category)?.label : 'Все продукты'}
            {!loading && <span className="ml-2 text-base font-normal text-gray-500">({filtered.length})</span>}
          </h2>
        </div>

        {/* Grid */}
        {loading ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="rounded-2xl bg-gray-100 animate-pulse" style={{ height: 420 }} />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
            <div className="text-3xl mb-3">⚠️</div>
            <p className="font-semibold text-red-700">{error}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-gray-200 bg-white p-16 text-center">
            <div className="text-5xl mb-4">🍽</div>
            <h3 className="text-lg font-semibold text-gray-900">Нет продуктов в этой категории</h3>
            <p className="mt-2 text-sm text-gray-600">Попробуйте другой фильтр или запустите seed</p>
            {category && (
              <button type="button" className="btn-secondary mt-4" onClick={() => setCategory('')}>
                Показать всё
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 animate-fade-in">
            {filtered.map((listing) => (
              <ListingCard key={listing.id} listing={listing} onOrderPlaced={() => loadListings()} />
            ))}
          </div>
        )}

        {nextCursor && !loading && (
          <div className="mt-10 text-center">
            <button
              type="button"
              className="btn-secondary px-8"
              disabled={loadingMore}
              onClick={() => loadListings(nextCursor)}
            >
              {loadingMore ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-300 border-t-brand-600" />
                  Загружаем...
                </span>
              ) : 'Показать ещё'}
            </button>
          </div>
        )}
      </section>

      {/* Bottom CTA */}
      <section className="bg-white border-t border-gray-100 mt-8">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="grid gap-8 lg:grid-cols-3 text-center lg:text-left">
            {[
              { emoji: '🌱', title: 'Меньше пищевых отходов', desc: 'Спасаем готовую еду от утилизации каждый день' },
              { emoji: '💰', title: 'Экономия до 70%', desc: 'Цены снижаются ближе к закрытию заведения' },
              { emoji: '⚡', title: 'Быстро и удобно', desc: 'Заказ за 30 секунд, забираете в удобное время' },
            ].map(({ emoji, title, desc }) => (
              <div key={title} className="flex flex-col items-center lg:items-start gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-2xl">{emoji}</div>
                <div>
                  <h3 className="font-bold text-gray-900">{title}</h3>
                  <p className="mt-1 text-sm text-gray-600">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
