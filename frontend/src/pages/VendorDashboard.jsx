import { useCallback, useEffect, useMemo, useState } from 'react'
import { listingsApi, ordersApi, vendorsApi } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import { ALLERGEN_LABELS, LISTING_STATUS_COLORS, LISTING_STATUS_LABELS, ORDER_STATUS_COLORS, ORDER_STATUS_LABELS } from '../utils/constants'

const ALLERGENS = ['none', 'gluten', 'dairy', 'eggs', 'nuts', 'soy', 'fish', 'shellfish', 'sesame']

const nowForInput = (hours = 1) => {
  const date = new Date(Date.now() + hours * 60 * 60 * 1000)
  date.setMinutes(0, 0, 0)
  return date.toISOString().slice(0, 16)
}

const DEFAULT_VENDOR = {
  business_name: 'Green Cafe',
  bin_number: String(Date.now()).slice(-12).padStart(12, '1'),
  address: 'Almaty, Abaya 1',
  latitude: 43.238,
  longitude: 76.945,
}

const DEFAULT_LISTING = {
  title: 'Fresh Sushi Box',
  description: 'Набор свежих роллов, приготовлен сегодня. Забрать до закрытия.',
  original_price: 5000,
  discount_percentage: 40,
  quantity_total: 10,
  pickup_window_start: nowForInput(1),
  pickup_window_end: nowForInput(5),
  allergens: ['fish', 'gluten'],
  latitude: 43.238,
  longitude: 76.945,
  photo_url: 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=900&q=80',
}

export default function VendorDashboard() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [vendor, setVendor] = useState(null)
  const [listings, setListings] = useState([])
  const [orders, setOrders] = useState([])
  const [vendorForm, setVendorForm] = useState(DEFAULT_VENDOR)
  const [listingForm, setListingForm] = useState(DEFAULT_LISTING)
  const [savingVendor, setSavingVendor] = useState(false)
  const [savingListing, setSavingListing] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const vendorResponse = await vendorsApi.me()
      setVendor(vendorResponse.data)
      const [listingsResponse, ordersResponse] = await Promise.all([
        listingsApi.myListings({ limit: 100 }),
        ordersApi.list({ limit: 100 }),
      ])
      setListings(listingsResponse.data.data)
      setOrders(ordersResponse.data.data)
    } catch (err) {
      if (err.response?.status === 404) {
        setVendor(null)
      } else {
        setError(err.response?.data?.detail || 'Не удалось загрузить кабинет продавца')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const stats = useMemo(() => ({
    listings: listings.length,
    active: listings.filter((item) => item.status === 'active').length,
    stock: listings.reduce((sum, item) => sum + item.quantity_available, 0),
    orders: orders.length,
  }), [listings, orders])

  const registerVendor = async (event) => {
    event.preventDefault()
    setSavingVendor(true)
    try {
      const payload = {
        ...vendorForm,
        latitude: Number(vendorForm.latitude),
        longitude: Number(vendorForm.longitude),
      }
      await vendorsApi.register(payload)
      toast.success('Профиль продавца создан и автоматически одобрен в demo-режиме.')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось создать профиль продавца')
    } finally {
      setSavingVendor(false)
    }
  }

  const createListing = async (event) => {
    event.preventDefault()
    setSavingListing(true)
    try {
      const payload = {
        ...listingForm,
        original_price: Number(listingForm.original_price),
        discount_percentage: Number(listingForm.discount_percentage),
        quantity_total: Number(listingForm.quantity_total),
        latitude: Number(listingForm.latitude),
        longitude: Number(listingForm.longitude),
        pickup_window_start: new Date(listingForm.pickup_window_start).toISOString(),
        pickup_window_end: new Date(listingForm.pickup_window_end).toISOString(),
        photo_url: listingForm.photo_url || null,
      }
      await listingsApi.create(payload)
      toast.success('Продукт добавлен на маркет.')
      setListingForm((current) => ({
        ...current,
        title: '',
        description: '',
        bin_number: current.bin_number,
      }))
      await load()
    } catch (err) {
      const detail = err.response?.data?.detail
      toast.error(Array.isArray(detail) ? detail.map((item) => item.msg).join(', ') : detail || 'Не удалось создать продукт')
    } finally {
      setSavingListing(false)
    }
  }

  const updateOrder = async (orderId, status) => {
    try {
      await ordersApi.updateStatus(orderId, { status })
      toast.success('Статус заказа обновлен')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось обновить заказ')
    }
  }

  const toggleAllergen = (code) => {
    setListingForm((current) => {
      if (code === 'none') return { ...current, allergens: ['none'] }
      const withoutNone = current.allergens.filter((item) => item !== 'none')
      const next = withoutNone.includes(code)
        ? withoutNone.filter((item) => item !== code)
        : [...withoutNone, code]
      return { ...current, allergens: next.length ? next : ['none'] }
    })
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-xl px-4 py-10">
        <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-red-700">{error}</div>
      </div>
    )
  }

  if (!vendor) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="text-3xl font-bold text-gray-950">Профиль продавца</h1>
        <p className="mt-2 text-gray-500">Создайте профиль заведения. В demo-режиме он будет одобрен автоматически.</p>
        <form onSubmit={registerVendor} className="card mt-6 grid gap-4 p-6">
          {[
            ['business_name', 'Название заведения'],
            ['bin_number', 'БИН'],
            ['address', 'Адрес'],
          ].map(([field, label]) => (
            <label key={field} className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
              <input
                className="input"
                required
                value={vendorForm[field]}
                onChange={(event) => setVendorForm((current) => ({ ...current, [field]: event.target.value }))}
              />
            </label>
          ))}
          <div className="grid grid-cols-2 gap-3">
            <label>
              <span className="mb-1 block text-sm font-medium text-gray-700">Широта</span>
              <input className="input" type="number" step="0.0001" value={vendorForm.latitude} onChange={(event) => setVendorForm((current) => ({ ...current, latitude: event.target.value }))} />
            </label>
            <label>
              <span className="mb-1 block text-sm font-medium text-gray-700">Долгота</span>
              <input className="input" type="number" step="0.0001" value={vendorForm.longitude} onChange={(event) => setVendorForm((current) => ({ ...current, longitude: event.target.value }))} />
            </label>
          </div>
          <button className="btn-primary" disabled={savingVendor}>{savingVendor ? 'Создаем...' : 'Создать профиль'}</button>
        </form>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col justify-between gap-3 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">Кабинет продавца</p>
          <h1 className="mt-1 text-3xl font-bold text-gray-950">{vendor.business_name}</h1>
          <p className="text-sm text-gray-500">{vendor.address}</p>
        </div>
        <button type="button" className="btn-secondary" onClick={load}>Обновить</button>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ['Продуктов', stats.listings],
          ['Активных', stats.active],
          ['Порций', stats.stock],
          ['Заказов', stats.orders],
        ].map(([label, value]) => (
          <div key={label} className="card p-4">
            <div className="text-2xl font-bold text-gray-950">{value}</div>
            <div className="text-sm text-gray-500">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
        <form onSubmit={createListing} className="card h-fit space-y-4 p-5">
          <div>
            <h2 className="text-lg font-semibold text-gray-950">Добавить продукт</h2>
            <p className="mt-1 text-sm text-gray-500">После сохранения продукт сразу появится на главной странице.</p>
          </div>

          <input className="input" required placeholder="Название" value={listingForm.title} onChange={(event) => setListingForm((current) => ({ ...current, title: event.target.value }))} />
          <textarea className="input min-h-20" required placeholder="Описание" value={listingForm.description} onChange={(event) => setListingForm((current) => ({ ...current, description: event.target.value }))} />

          <div className="grid grid-cols-2 gap-3">
            <input className="input" type="number" min="500" required placeholder="Цена" value={listingForm.original_price} onChange={(event) => setListingForm((current) => ({ ...current, original_price: event.target.value }))} />
            <input className="input" type="number" min="1" max="90" required placeholder="Скидка %" value={listingForm.discount_percentage} onChange={(event) => setListingForm((current) => ({ ...current, discount_percentage: event.target.value }))} />
          </div>
          <input className="input" type="number" min="1" required placeholder="Количество" value={listingForm.quantity_total} onChange={(event) => setListingForm((current) => ({ ...current, quantity_total: event.target.value }))} />
          <input className="input" type="url" placeholder="Фото URL" value={listingForm.photo_url} onChange={(event) => setListingForm((current) => ({ ...current, photo_url: event.target.value }))} />

          <div className="grid grid-cols-2 gap-3">
            <label>
              <span className="mb-1 block text-xs font-medium text-gray-500">Забрать с</span>
              <input className="input" type="datetime-local" required value={listingForm.pickup_window_start} onChange={(event) => setListingForm((current) => ({ ...current, pickup_window_start: event.target.value }))} />
            </label>
            <label>
              <span className="mb-1 block text-xs font-medium text-gray-500">Забрать до</span>
              <input className="input" type="datetime-local" required value={listingForm.pickup_window_end} onChange={(event) => setListingForm((current) => ({ ...current, pickup_window_end: event.target.value }))} />
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            {ALLERGENS.map((code) => (
              <button
                key={code}
                type="button"
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                  listingForm.allergens.includes(code)
                    ? 'border-amber-500 bg-amber-50 text-amber-700'
                    : 'border-gray-200 bg-white text-gray-600'
                }`}
                onClick={() => toggleAllergen(code)}
              >
                {ALLERGEN_LABELS[code]}
              </button>
            ))}
          </div>

          <button className="btn-primary w-full" disabled={savingListing}>
            {savingListing ? 'Сохраняем...' : 'Добавить продукт'}
          </button>
        </form>

        <div className="space-y-6">
          <section className="card overflow-hidden">
            <div className="border-b border-gray-100 px-5 py-4">
              <h2 className="font-semibold text-gray-950">Ваши продукты</h2>
            </div>
            <div className="divide-y divide-gray-100">
              {listings.length === 0 ? (
                <div className="p-6 text-sm text-gray-500">Вы еще не добавили продукты.</div>
              ) : listings.map((item) => (
                <div key={item.id} className="flex items-center gap-4 p-4">
                  <img
                    src={item.photo_url || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=200&q=80'}
                    alt={item.title}
                    className="h-16 w-20 rounded-lg object-cover"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-medium text-gray-950">{item.title}</h3>
                      <span className={`badge ${LISTING_STATUS_COLORS[item.status] || 'bg-gray-100'}`}>{LISTING_STATUS_LABELS[item.status] || item.status}</span>
                    </div>
                    <p className="text-sm text-gray-500">
                      {item.current_price.toLocaleString()} ₸ из {item.original_price.toLocaleString()} ₸, осталось {item.quantity_available}/{item.quantity_total}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="card overflow-hidden">
            <div className="border-b border-gray-100 px-5 py-4">
              <h2 className="font-semibold text-gray-950">Заказы</h2>
            </div>
            <div className="divide-y divide-gray-100">
              {orders.length === 0 ? (
                <div className="p-6 text-sm text-gray-500">Заказов пока нет.</div>
              ) : orders.map((order) => (
                <div key={order.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-950">Заказ #{order.id}</span>
                      <span className={`badge ${ORDER_STATUS_COLORS[order.status] || 'bg-gray-100'}`}>{ORDER_STATUS_LABELS[order.status] || order.status}</span>
                    </div>
                    <p className="text-sm text-gray-500">{order.total_amount.toLocaleString()} ₸, код выдачи: {order.pickup_token}</p>
                  </div>
                  <div className="flex gap-2">
                    {order.status === 'pending' && (
                      <button className="btn-secondary" onClick={() => updateOrder(order.id, 'confirmed')}>Подтвердить</button>
                    )}
                    {order.status === 'confirmed' && (
                      <button className="btn-secondary" onClick={() => updateOrder(order.id, 'ready_for_pickup')}>Готов</button>
                    )}
                    {order.status === 'ready_for_pickup' && (
                      <button className="btn-primary" onClick={() => updateOrder(order.id, 'picked_up')}>Выдан</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
