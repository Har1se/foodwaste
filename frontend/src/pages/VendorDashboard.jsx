import { useCallback, useEffect, useMemo, useState } from 'react'
import { listingsApi, ordersApi, vendorsApi } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import { ALLERGEN_LABELS, LISTING_STATUS_COLORS, LISTING_STATUS_LABELS, ORDER_STATUS_COLORS, ORDER_STATUS_LABELS } from '../utils/constants'

const ALLERGENS = ['none', 'gluten', 'dairy', 'eggs', 'nuts', 'soy', 'fish', 'shellfish', 'sesame']

const pickupDate = (hoursAhead = 1) => {
  const d = new Date(Date.now() + hoursAhead * 3600_000)
  d.setMinutes(0, 0, 0)
  return d.toISOString().slice(0, 16)
}

// Catalog of 30+ pre-made food templates for quick add
const FOOD_CATALOG = [
  { title: 'Суши-сет с лососем', description: '24 ролла: Филадельфия, Калифорния, Спайси.', original_price: 6500, discount_percentage: 40, allergens: ['fish','gluten','sesame'], photo_url: 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=900&q=80', category: '🍣' },
  { title: 'Рамен Тонкоцу', description: 'Насыщенный бульон, яйцо пашот, ростки бамбука, нори.', original_price: 4200, discount_percentage: 40, allergens: ['gluten','eggs'], photo_url: 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=900&q=80', category: '🍜' },
  { title: 'Пицца Маргарита', description: 'Томатный соус, моцарелла, свежий базилик. 32 см.', original_price: 3800, discount_percentage: 50, allergens: ['gluten','dairy'], photo_url: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=900&q=80', category: '🍕' },
  { title: 'Паста Карбонара', description: 'Спагетти, панчетта, пармезан, яично-сливочный соус.', original_price: 3600, discount_percentage: 50, allergens: ['gluten','dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1612874742237-6526221588e3?auto=format&fit=crop&w=900&q=80', category: '🍝' },
  { title: 'Двойной чизбургер', description: 'Говяжья котлета 200г, двойной чеддер, карамелизованный лук.', original_price: 4200, discount_percentage: 40, allergens: ['gluten','dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80', category: '🍔' },
  { title: 'Плов по-казахски', description: 'Рис с бараниной, морковью, нутом и изюмом.', original_price: 3200, discount_percentage: 40, allergens: ['none'], photo_url: 'https://images.unsplash.com/photo-1596797882870-8c33c55c473b?auto=format&fit=crop&w=900&q=80', category: '🍛' },
  { title: 'Манты с говядиной', description: '8 штук, паровые, со сметаной.', original_price: 2500, discount_percentage: 40, allergens: ['gluten','eggs'], photo_url: 'https://images.unsplash.com/photo-1625220194771-7ebdea0b70b9?auto=format&fit=crop&w=900&q=80', category: '🥟' },
  { title: 'Шаурма с курицей', description: 'Лаваш, курица гриль, овощи, чесночный соус.', original_price: 2200, discount_percentage: 50, allergens: ['gluten','dairy'], photo_url: 'https://images.unsplash.com/photo-1529006557810-274b9b2fc783?auto=format&fit=crop&w=900&q=80', category: '🌯' },
  { title: 'Корзинка выпечки', description: 'Круассан, синнабон, маффин черника, слойка.', original_price: 2800, discount_percentage: 50, allergens: ['gluten','dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=900&q=80', category: '🥐' },
  { title: 'Шоколадный торт (2 куска)', description: 'Тройной шоколад, ганаш, малиновое кули.', original_price: 1800, discount_percentage: 50, allergens: ['gluten','dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=900&q=80', category: '🎂' },
  { title: 'Чизкейк Нью-Йорк', description: 'Классический, ягодный соус. Порция 180г.', original_price: 1600, discount_percentage: 50, allergens: ['gluten','dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1508737027454-e6454ef45afd?auto=format&fit=crop&w=900&q=80', category: '🍰' },
  { title: 'Смузи-пак (4 бутылки)', description: 'Манго-банан, ягодный, зелёный, тропический.', original_price: 2400, discount_percentage: 50, allergens: ['none'], photo_url: 'https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=900&q=80', category: '🥤' },
  { title: 'Боул с нутом', description: 'Шпинат, нут, томаты черри, авокадо, кедровые орешки.', original_price: 3000, discount_percentage: 40, allergens: ['nuts','sesame'], photo_url: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80', category: '🥗' },
  { title: 'Поке с лососем', description: 'Рис, лосось, авокадо, манго, огурец, эдамаме.', original_price: 4500, discount_percentage: 40, allergens: ['fish','soy','sesame'], photo_url: 'https://images.unsplash.com/photo-1546069901-d5bfd2cbfb1f?auto=format&fit=crop&w=900&q=80', category: '🍱' },
  { title: 'Фалафель-тарелка', description: '6 шариков фалафеля, хумус, питта, табуле, тахини.', original_price: 2600, discount_percentage: 40, allergens: ['gluten','sesame'], photo_url: 'https://images.unsplash.com/photo-1499488112611-3df45cc95ef0?auto=format&fit=crop&w=900&q=80', category: '🧆' },
  { title: 'Стейк Рибай (250г)', description: 'Мраморная говядина Medium, запечённые овощи, беарнез.', original_price: 8500, discount_percentage: 40, allergens: ['dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=900&q=80', category: '🥩' },
  { title: 'Клубный сэндвич', description: 'Тройной сэндвич с курицей, беконом, авокадо.', original_price: 2800, discount_percentage: 50, allergens: ['gluten','dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=900&q=80', category: '🥪' },
  { title: 'Панкейки с сиропом', description: 'Стек из 4 пышных панкейков, масло, кленовый сироп.', original_price: 2200, discount_percentage: 50, allergens: ['gluten','dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=900&q=80', category: '🥞' },
  { title: 'Пончики ассорти (6 шт)', description: 'Глазурованные, с клубникой, шоколадные.', original_price: 1400, discount_percentage: 50, allergens: ['gluten','dairy','eggs'], photo_url: 'https://images.unsplash.com/photo-1551024601-bec78aea704b?auto=format&fit=crop&w=900&q=80', category: '🍩' },
  { title: 'Грибной крем-суп', description: 'Белые грибы, трюфельное масло, сливки, гренки.', original_price: 2400, discount_percentage: 40, allergens: ['dairy','gluten'], photo_url: 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=900&q=80', category: '🍲' },
  { title: 'Рыба с картошкой-фри', description: 'Хрустящий батер, треска, картофель фри, тартар.', original_price: 3800, discount_percentage: 40, allergens: ['fish','gluten','eggs'], photo_url: 'https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=900&q=80', category: '🐟' },
  { title: 'Джелато (3 шарика)', description: 'Фисташка, шоколад, клубника. Свежеприготовленное.', original_price: 1200, discount_percentage: 50, allergens: ['dairy','nuts'], photo_url: 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?auto=format&fit=crop&w=900&q=80', category: '🍦' },
  { title: 'Бизнес-ланч', description: 'Суп дня + горячее + салат + напиток.', original_price: 3500, discount_percentage: 50, allergens: ['gluten','dairy'], photo_url: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80', category: '🍱' },
  { title: 'Веганский бокс', description: 'Темпе, фалафель, хумус, табуле, питта.', original_price: 4000, discount_percentage: 50, allergens: ['gluten','sesame','soy'], photo_url: 'https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=900&q=80', category: '🌿' },
  { title: 'Сырная тарелка', description: '5 видов сыра, крекеры, виноград, мёд, орехи.', original_price: 5500, discount_percentage: 50, allergens: ['dairy','gluten','nuts'], photo_url: 'https://images.unsplash.com/photo-1464500422302-6188776dcbf7?auto=format&fit=crop&w=900&q=80', category: '🧀' },
]

const BLANK_LISTING = {
  title: '', description: '', original_price: 3000, discount_percentage: 40,
  quantity_total: 9999, pickup_window_start: pickupDate(1), pickup_window_end: pickupDate(8),
  allergens: ['none'], latitude: 43.238, longitude: 76.945, photo_url: '',
}

const BLANK_VENDOR = {
  business_name: '', bin_number: String(Date.now()).slice(-12).padStart(12,'1'),
  address: 'Алматы', latitude: 43.238, longitude: 76.945,
}

// Icons
const PlusIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="h-4 w-4">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
)
const RefreshIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
    <path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
)

export default function VendorDashboard() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [vendor, setVendor] = useState(null)
  const [listings, setListings] = useState([])
  const [orders, setOrders] = useState([])
  const [vendorForm, setVendorForm] = useState(BLANK_VENDOR)
  const [listingForm, setListingForm] = useState(BLANK_LISTING)
  const [savingVendor, setSavingVendor] = useState(false)
  const [savingListing, setSavingListing] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('add')
  const [catalogSearch, setCatalogSearch] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const vRes = await vendorsApi.me()
      setVendor(vRes.data)
      const [lRes, oRes] = await Promise.all([
        listingsApi.myListings({ limit: 100 }),
        ordersApi.list({ limit: 100 }),
      ])
      setListings(lRes.data.data)
      setOrders(oRes.data.data)
    } catch (err) {
      if (err.response?.status === 404) setVendor(null)
      else setError(err.response?.data?.detail || 'Не удалось загрузить кабинет')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const stats = useMemo(() => ({
    listings: listings.length,
    active: listings.filter((i) => i.status === 'active').length,
    stock: listings.reduce((s, i) => s + i.quantity_available, 0),
    orders: orders.filter((o) => o.status === 'pending').length,
  }), [listings, orders])

  const registerVendor = async (e) => {
    e.preventDefault(); setSavingVendor(true)
    try {
      await vendorsApi.register({
        ...vendorForm,
        latitude: Number(vendorForm.latitude),
        longitude: Number(vendorForm.longitude),
      })
      toast.success('Профиль продавца создан и сразу одобрен!')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось создать профиль')
    } finally { setSavingVendor(false) }
  }

  const createListing = async (e) => {
    e.preventDefault(); setSavingListing(true)
    try {
      await listingsApi.create({
        ...listingForm,
        original_price: Number(listingForm.original_price),
        discount_percentage: Number(listingForm.discount_percentage),
        quantity_total: Number(listingForm.quantity_total),
        latitude: Number(listingForm.latitude),
        longitude: Number(listingForm.longitude),
        pickup_window_start: new Date(listingForm.pickup_window_start).toISOString(),
        pickup_window_end: new Date(listingForm.pickup_window_end).toISOString(),
        photo_url: listingForm.photo_url || null,
      })
      toast.success('Продукт добавлен на маркет!')
      setListingForm({ ...BLANK_LISTING, pickup_window_start: pickupDate(1), pickup_window_end: pickupDate(8) })
      await load()
    } catch (err) {
      const detail = err.response?.data?.detail
      toast.error(Array.isArray(detail) ? detail.map((i) => i.msg).join(', ') : detail || 'Ошибка')
    } finally { setSavingListing(false) }
  }

  const updateOrder = async (id, status) => {
    try {
      await ordersApi.updateStatus(id, { status })
      toast.success('Статус обновлён')
      await load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Ошибка') }
  }

  const toggleAllergen = (code) => {
    setListingForm((cur) => {
      if (code === 'none') return { ...cur, allergens: ['none'] }
      const without = cur.allergens.filter((a) => a !== 'none')
      const next = without.includes(code) ? without.filter((a) => a !== code) : [...without, code]
      return { ...cur, allergens: next.length ? next : ['none'] }
    })
  }

  const applyTemplate = (tpl) => {
    setListingForm({
      ...BLANK_LISTING,
      title: tpl.title,
      description: tpl.description,
      original_price: tpl.original_price,
      discount_percentage: tpl.discount_percentage,
      allergens: tpl.allergens,
      photo_url: tpl.photo_url,
      latitude: vendor?.latitude || 43.238,
      longitude: vendor?.longitude || 76.945,
      pickup_window_start: pickupDate(1),
      pickup_window_end: pickupDate(8),
      quantity_total: 9999,
    })
    setActiveTab('add')
    toast.success(`Шаблон «${tpl.title}» применён`)
  }

  const filteredCatalog = useMemo(() =>
    FOOD_CATALOG.filter((t) =>
      !catalogSearch || t.title.toLowerCase().includes(catalogSearch.toLowerCase())
    ), [catalogSearch])

  if (loading) return (
    <div className="flex h-64 items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
    </div>
  )

  if (error) return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-700">{error}</div>
    </div>
  )

  // Register vendor form
  if (!vendor) return (
    <div className="mx-auto max-w-lg px-4 py-12">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl bg-brand-100 text-brand-600 text-3xl mb-4">🏪</div>
        <h1 className="text-2xl font-bold text-gray-900">Стать продавцом</h1>
        <p className="mt-2 text-gray-500 text-sm">Заполните профиль заведения. Одобрение происходит автоматически.</p>
      </div>
      <form onSubmit={registerVendor} className="card p-6 space-y-4">
        {[
          ['business_name', 'Название заведения', 'Кафе «Алма»'],
          ['bin_number', 'БИН (12 цифр)', '123456789012'],
          ['address', 'Адрес', 'Алматы, ул. Абая 1'],
        ].map(([field, label, placeholder]) => (
          <label key={field} className="block">
            <span className="label">{label}</span>
            <input className="input" required placeholder={placeholder}
              value={vendorForm[field]}
              onChange={(e) => setVendorForm((c) => ({ ...c, [field]: e.target.value }))} />
          </label>
        ))}
        <div className="grid grid-cols-2 gap-3">
          {[['latitude','Широта'], ['longitude','Долгота']].map(([f, l]) => (
            <label key={f}>
              <span className="label">{l}</span>
              <input className="input" type="number" step="0.0001" value={vendorForm[f]}
                onChange={(e) => setVendorForm((c) => ({ ...c, [f]: e.target.value }))} />
            </label>
          ))}
        </div>
        <button className="btn-primary w-full" disabled={savingVendor}>
          {savingVendor ? 'Создаём...' : '🏪 Создать профиль'}
        </button>
      </form>
    </div>
  )

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-brand-600 mb-1">Кабинет продавца</p>
          <h1 className="text-2xl font-bold text-gray-900">{vendor.business_name}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{vendor.address}</p>
        </div>
        <button type="button" className="btn-secondary self-start sm:self-auto" onClick={load}>
          <RefreshIcon /> Обновить
        </button>
      </div>

      {/* Stats */}
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: 'Продуктов',  value: stats.listings, color: 'bg-violet-50 text-violet-600',  emoji: '📦' },
          { label: 'Активных',   value: stats.active,   color: 'bg-brand-50 text-brand-600',    emoji: '✅' },
          { label: 'Порций',     value: stats.stock, color: 'bg-sky-50 text-sky-600', emoji: '🍽' },
          { label: 'Новых зак.', value: stats.orders,   color: 'bg-amber-50 text-amber-600',    emoji: '🛒' },
        ].map(({ label, value, color, emoji }) => (
          <div key={label} className="card p-4 flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-xl text-lg ${color}`}>{emoji}</div>
            <div>
              <div className="text-xl font-bold text-gray-900">{value}</div>
              <div className="text-xs text-gray-500">{label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
        {/* Left panel: add product + catalog */}
        <div className="space-y-4">
          {/* Tab switcher */}
          <div className="flex rounded-xl border border-gray-200 bg-gray-50 p-1">
            <button
              type="button"
              className={`flex-1 rounded-lg py-2 text-sm font-semibold transition-all ${activeTab === 'add' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
              onClick={() => setActiveTab('add')}
            >
              ✏️ Добавить
            </button>
            <button
              type="button"
              className={`flex-1 rounded-lg py-2 text-sm font-semibold transition-all ${activeTab === 'catalog' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
              onClick={() => setActiveTab('catalog')}
            >
              📋 Каталог ({FOOD_CATALOG.length})
            </button>
          </div>

          {activeTab === 'add' ? (
            <form onSubmit={createListing} className="card p-5 space-y-3.5">
              <h2 className="font-semibold text-gray-900">Новый продукт</h2>

              <input className="input" required placeholder="Название блюда"
                value={listingForm.title}
                onChange={(e) => setListingForm((c) => ({ ...c, title: e.target.value }))} />

              <textarea className="input min-h-[72px] resize-none" required placeholder="Описание: состав, особенности"
                value={listingForm.description}
                onChange={(e) => setListingForm((c) => ({ ...c, description: e.target.value }))} />

              <div className="grid grid-cols-2 gap-3">
                <label>
                  <span className="label text-xs">Цена (₸)</span>
                  <input className="input" type="number" min="500" required value={listingForm.original_price}
                    onChange={(e) => setListingForm((c) => ({ ...c, original_price: e.target.value }))} />
                </label>
                <label>
                  <span className="label text-xs">Скидка (%)</span>
                  <input className="input" type="number" min="1" max="90" required value={listingForm.discount_percentage}
                    onChange={(e) => setListingForm((c) => ({ ...c, discount_percentage: e.target.value }))} />
                </label>
              </div>

              {listingForm.original_price && listingForm.discount_percentage && (
                <div className="rounded-xl bg-brand-50 border border-brand-100 px-3 py-2 text-sm font-semibold text-brand-700">
                  Цена со скидкой: {Math.max(Math.round(listingForm.original_price * (1 - listingForm.discount_percentage / 100)), 500).toLocaleString()} ₸
                </div>
              )}

              <input className="input" type="url" placeholder="URL фото (Unsplash или другой)"
                value={listingForm.photo_url}
                onChange={(e) => setListingForm((c) => ({ ...c, photo_url: e.target.value }))} />

              <div className="grid grid-cols-2 gap-3">
                <label>
                  <span className="label text-xs">Забрать с</span>
                  <input className="input" type="datetime-local" required value={listingForm.pickup_window_start}
                    onChange={(e) => setListingForm((c) => ({ ...c, pickup_window_start: e.target.value }))} />
                </label>
                <label>
                  <span className="label text-xs">Забрать до</span>
                  <input className="input" type="datetime-local" required value={listingForm.pickup_window_end}
                    onChange={(e) => setListingForm((c) => ({ ...c, pickup_window_end: e.target.value }))} />
                </label>
              </div>

              <div>
                <span className="label text-xs">Аллергены</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {ALLERGENS.map((code) => (
                    <button key={code} type="button"
                      className={`rounded-full border px-3 py-1 text-xs font-medium transition-all ${
                        listingForm.allergens.includes(code)
                          ? 'border-amber-400 bg-amber-100 text-amber-800'
                          : 'border-gray-200 bg-white text-gray-500 hover:border-gray-300'
                      }`}
                      onClick={() => toggleAllergen(code)}>
                      {ALLERGEN_LABELS[code]}
                    </button>
                  ))}
                </div>
              </div>

              <button className="btn-primary w-full" disabled={savingListing}>
                {savingListing ? 'Добавляем...' : <><PlusIcon /> Добавить продукт</>}
              </button>
            </form>
          ) : (
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-gray-100">
                <h2 className="font-semibold text-gray-900 mb-3">Быстрый выбор блюда</h2>
                <input className="input text-sm" placeholder="Поиск шаблона..."
                  value={catalogSearch}
                  onChange={(e) => setCatalogSearch(e.target.value)} />
              </div>
              <div className="divide-y divide-gray-50 max-h-[520px] overflow-y-auto">
                {filteredCatalog.map((tpl) => (
                  <button key={tpl.title} type="button"
                    className="w-full flex items-center gap-3 p-3.5 text-left hover:bg-brand-50/50 transition-colors"
                    onClick={() => applyTemplate(tpl)}>
                    <img src={tpl.photo_url} alt={tpl.title} className="h-12 w-14 rounded-lg object-cover shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-base">{tpl.category}</span>
                        <span className="text-sm font-semibold text-gray-900 truncate">{tpl.title}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-gray-400 line-through">{tpl.original_price.toLocaleString()} ₸</span>
                        <span className="text-xs font-bold text-brand-600">
                          -{tpl.discount_percentage}% → {Math.round(tpl.original_price * (1 - tpl.discount_percentage/100)).toLocaleString()} ₸
                        </span>
                      </div>
                    </div>
                    <span className="text-xs text-brand-600 font-semibold shrink-0">Выбрать →</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right panel: listings + orders */}
        <div className="space-y-6">
          {/* Listings */}
          <section className="card overflow-hidden">
            <div className="border-b border-gray-100 px-5 py-4 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Ваши продукты ({listings.length})</h2>
            </div>
            {listings.length === 0 ? (
              <div className="p-10 text-center">
                <div className="text-4xl mb-3">📦</div>
                <p className="text-gray-500 text-sm">Добавьте первый продукт через форму слева</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {listings.map((item) => (
                  <div key={item.id} className="flex items-center gap-4 p-4 hover:bg-gray-50/50 transition-colors">
                    <img
                      src={item.photo_url || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=200&q=80'}
                      alt={item.title}
                      className="h-14 w-16 rounded-xl object-cover shrink-0"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-0.5">
                        <h3 className="font-semibold text-gray-900 text-sm truncate">{item.title}</h3>
                        <span className={`badge text-[10px] ${LISTING_STATUS_COLORS[item.status] || 'bg-gray-100'}`}>
                          {LISTING_STATUS_LABELS[item.status] || item.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500">
                        <span className="font-semibold text-brand-600">{item.current_price.toLocaleString()} ₸</span>
                        <span className="text-gray-300 mx-1.5">·</span>
                        <span className="text-gray-400">{item.original_price.toLocaleString()} ₸</span>
                        <span className="text-gray-300 mx-1.5">·</span>
                        осталось {item.quantity_available}/{item.quantity_total}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Orders */}
          <section className="card overflow-hidden">
            <div className="border-b border-gray-100 px-5 py-4">
              <h2 className="font-semibold text-gray-900">Заказы ({orders.length})</h2>
            </div>
            {orders.length === 0 ? (
              <div className="p-10 text-center">
                <div className="text-4xl mb-3">🛒</div>
                <p className="text-gray-500 text-sm">Заказов пока нет</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {orders.map((order) => (
                  <div key={order.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center hover:bg-gray-50/50 transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-gray-900">Заказ #{order.id}</span>
                        <span className={`badge text-[10px] ${ORDER_STATUS_COLORS[order.status] || 'bg-gray-100'}`}>
                          {ORDER_STATUS_LABELS[order.status] || order.status}
                        </span>
                        <span className="ml-auto font-bold text-brand-600">{order.total_amount.toLocaleString()} ₸</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-1 font-mono">
                        Код: {order.pickup_token.slice(0, 12)}...
                      </p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      {order.status === 'pending' && (
                        <button className="btn-secondary text-xs py-1.5" onClick={() => updateOrder(order.id, 'confirmed')}>Подтвердить</button>
                      )}
                      {order.status === 'confirmed' && (
                        <button className="btn-secondary text-xs py-1.5" onClick={() => updateOrder(order.id, 'ready_for_pickup')}>Готов</button>
                      )}
                      {order.status === 'ready_for_pickup' && (
                        <button className="btn-primary text-xs py-1.5" onClick={() => updateOrder(order.id, 'picked_up')}>✓ Выдан</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
