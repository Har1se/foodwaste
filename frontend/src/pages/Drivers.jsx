import { useEffect, useState, useCallback } from 'react'
import { useToast } from '../contexts/ToastContext'
import { driversApi } from '../api/client'

const VEHICLE_LABELS = {
  bicycle: { label: 'Велосипед', icon: '🚲' },
  scooter: { label: 'Самокат', icon: '🛴' },
  car:     { label: 'Авто',     icon: '🚗' },
  walk:    { label: 'Пешком',   icon: '🚶' },
}

const DELIVERY_STATUS_LABELS = {
  assigned:          { label: 'Назначен',        color: 'bg-blue-100 text-blue-700' },
  en_route_pickup:   { label: 'Едет к точке',    color: 'bg-yellow-100 text-yellow-700' },
  at_pickup:         { label: 'У точки забора',  color: 'bg-orange-100 text-orange-700' },
  en_route_delivery: { label: 'Доставляет',      color: 'bg-purple-100 text-purple-700' },
  delivered:         { label: 'Доставлено',      color: 'bg-green-100 text-green-700' },
  failed:            { label: 'Не выполнено',    color: 'bg-red-100 text-red-700' },
}

const NEXT_STATUS = {
  assigned:          'en_route_pickup',
  en_route_pickup:   'at_pickup',
  at_pickup:         'en_route_delivery',
  en_route_delivery: 'delivered',
}

const NEXT_STATUS_LABEL = {
  assigned:          'Выехать к точке',
  en_route_pickup:   'Прибыл к точке',
  at_pickup:         'Забрал заказ',
  en_route_delivery: 'Доставлено',
}

export default function Drivers() {
  const { showToast } = useToast()
  const [profile, setProfile] = useState(null)
  const [deliveries, setDeliveries] = useState([])
  const [route, setRoute] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notDriver, setNotDriver] = useState(false)
  const [registering, setRegistering] = useState(false)
  const [vehicleType, setVehicleType] = useState('bicycle')
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [updatingLoc, setUpdatingLoc] = useState(false)

  const loadData = useCallback(async () => {
    try {
      const [profileRes, deliveriesRes] = await Promise.all([
        driversApi.me(),
        driversApi.myDeliveries(),
      ])
      setProfile(profileRes.data)
      setDeliveries(deliveriesRes.data)
      setNotDriver(false)
    } catch (err) {
      if (err.response?.status === 404) setNotDriver(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleRegister = async (e) => {
    e.preventDefault()
    setRegistering(true)
    try {
      await driversApi.register({ vehicle_type: vehicleType })
      showToast('Профиль водителя создан!', 'success')
      await loadData()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Ошибка регистрации', 'error')
    } finally {
      setRegistering(false)
    }
  }

  const handleUpdateLocation = async (e) => {
    e.preventDefault()
    if (!lat || !lng) return
    setUpdatingLoc(true)
    try {
      await driversApi.updateLocation({
        lat: parseFloat(lat),
        lng: parseFloat(lng),
        status: 'available',
      })
      showToast('Местоположение обновлено. Статус: Доступен', 'success')
      await loadData()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Ошибка', 'error')
    } finally {
      setUpdatingLoc(false)
    }
  }

  const handleGeoLocate = () => {
    if (!navigator.geolocation) {
      showToast('Геолокация не поддерживается браузером', 'error')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6))
        setLng(pos.coords.longitude.toFixed(6))
        showToast('Координаты получены', 'success')
      },
      () => showToast('Не удалось получить геолокацию', 'error')
    )
  }

  const handleDeliveryStatus = async (deliveryId, newStatus) => {
    try {
      await driversApi.updateDelivery(deliveryId, { status: newStatus })
      showToast('Статус обновлён', 'success')
      await loadData()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Ошибка', 'error')
    }
  }

  const handleRouteOptimize = async () => {
    try {
      const { data } = await driversApi.routeOptimize()
      setRoute(data)
      showToast(`Маршрут оптимизирован. Дистанция: ${data.total_distance_km} км`, 'success')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Нет активных доставок для оптимизации', 'error')
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
      </div>
    )
  }

  if (notDriver) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <div className="text-6xl mb-6">🚚</div>
        <h1 className="text-3xl font-extrabold text-gray-900 mb-3">Стать водителем</h1>
        <p className="text-gray-500 mb-8">
          Доставляйте заказы из ресторанов клиентам и зарабатывайте на доставке.
        </p>
        <form onSubmit={handleRegister} className="inline-flex flex-col items-center gap-4 w-full max-w-xs">
          <div className="grid grid-cols-2 gap-2 w-full">
            {Object.entries(VEHICLE_LABELS).map(([value, { label, icon }]) => (
              <button
                key={value}
                type="button"
                onClick={() => setVehicleType(value)}
                className={`flex flex-col items-center gap-1 rounded-xl border-2 p-3 transition-all ${
                  vehicleType === value
                    ? 'border-brand-600 bg-brand-50'
                    : 'border-gray-200 bg-white hover:border-brand-300'
                }`}
              >
                <span className="text-2xl">{icon}</span>
                <span className="text-xs font-semibold text-gray-700">{label}</span>
              </button>
            ))}
          </div>
          <button
            type="submit"
            disabled={registering}
            className="btn-primary w-full"
          >
            {registering ? 'Регистрация...' : 'Зарегистрироваться как водитель'}
          </button>
        </form>
      </div>
    )
  }

  const activeDeliveries = deliveries.filter(
    (d) => !['delivered', 'failed'].includes(d.status)
  )
  const completedDeliveries = deliveries.filter(
    (d) => ['delivered', 'failed'].includes(d.status)
  )

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-extrabold text-gray-900 mb-8">Кабинет водителя</h1>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        {/* Left column */}
        <div className="space-y-6">
          {/* Profile card */}
          {profile && (
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold text-gray-900">Мой профиль</h2>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                  profile.status === 'available' ? 'bg-green-100 text-green-700' :
                  profile.status === 'busy' ? 'bg-orange-100 text-orange-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {profile.status === 'available' ? 'Доступен' :
                   profile.status === 'busy' ? 'Занят' : 'Офлайн'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: 'Транспорт', value: `${VEHICLE_LABELS[profile.vehicle_type]?.icon} ${VEHICLE_LABELS[profile.vehicle_type]?.label}` },
                  { label: 'Рейтинг', value: `⭐ ${profile.rating.toFixed(1)}` },
                  { label: 'Доставок', value: profile.total_deliveries },
                  { label: 'Верификация', value: profile.is_verified ? '✅ Подтверждён' : '⏳ Ожидание' },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-xl bg-gray-50 p-3 text-center">
                    <div className="text-xs text-gray-500 mb-1">{label}</div>
                    <div className="font-semibold text-gray-800 text-sm">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active deliveries */}
          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900">
                Активные доставки
                {activeDeliveries.length > 0 && (
                  <span className="ml-2 rounded-full bg-brand-600 px-2 py-0.5 text-xs text-white">
                    {activeDeliveries.length}
                  </span>
                )}
              </h2>
              {activeDeliveries.length > 0 && (
                <button
                  type="button"
                  onClick={handleRouteOptimize}
                  className="btn-secondary text-xs"
                >
                  Оптимизировать маршрут
                </button>
              )}
            </div>

            {activeDeliveries.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-200 p-8 text-center">
                <div className="text-3xl mb-2">📦</div>
                <p className="text-sm text-gray-500">Нет активных доставок</p>
              </div>
            ) : (
              <div className="space-y-3">
                {activeDeliveries.map((delivery) => {
                  const status = DELIVERY_STATUS_LABELS[delivery.status]
                  const nextStatus = NEXT_STATUS[delivery.status]
                  return (
                    <div key={delivery.id} className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <div className="font-semibold text-gray-900 text-sm">Заказ #{delivery.order_id}</div>
                          {delivery.distance_km && (
                            <div className="text-xs text-gray-500 mt-0.5">
                              ~{delivery.distance_km} км до точки
                            </div>
                          )}
                        </div>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${status?.color}`}>
                          {status?.label}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 mb-3">
                        <div>📍 Забор: {delivery.pickup_lat.toFixed(4)}, {delivery.pickup_lng.toFixed(4)}</div>
                        <div>🏠 Доставка: {delivery.delivery_lat.toFixed(4)}, {delivery.delivery_lng.toFixed(4)}</div>
                      </div>
                      {nextStatus && (
                        <button
                          type="button"
                          onClick={() => handleDeliveryStatus(delivery.id, nextStatus)}
                          className="btn-primary text-xs w-full"
                        >
                          {NEXT_STATUS_LABEL[delivery.status]}
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Optimized route */}
          {route && route.stops.length > 0 && (
            <div className="rounded-2xl border border-brand-200 bg-brand-50 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold text-brand-800">Оптимальный маршрут</h2>
                <span className="text-sm text-brand-600 font-semibold">
                  {route.total_distance_km} км
                </span>
              </div>
              <div className="space-y-2">
                {route.stops.map((stop, i) => (
                  <div key={stop.delivery_id} className="flex items-center gap-3 rounded-xl bg-white p-3">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white text-xs font-bold">
                      {stop.sequence}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-gray-900 text-sm">Заказ #{stop.order_id}</div>
                      <div className="text-xs text-gray-500">{stop.lat.toFixed(4)}, {stop.lng.toFixed(4)}</div>
                    </div>
                    {i > 0 && (
                      <div className="text-xs text-gray-500">+{stop.distance_from_prev_km} км</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Completed deliveries */}
          {completedDeliveries.length > 0 && (
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <h2 className="font-bold text-gray-900 mb-4">
                История доставок ({completedDeliveries.length})
              </h2>
              <div className="space-y-2">
                {completedDeliveries.slice(0, 10).map((delivery) => {
                  const status = DELIVERY_STATUS_LABELS[delivery.status]
                  return (
                    <div key={delivery.id} className="flex items-center justify-between rounded-xl bg-gray-50 px-4 py-3">
                      <div className="text-sm font-semibold text-gray-800">Заказ #{delivery.order_id}</div>
                      <div className="flex items-center gap-3">
                        {delivery.distance_km && (
                          <span className="text-xs text-gray-500">{delivery.distance_km} км</span>
                        )}
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${status?.color}`}>
                          {status?.label}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Right column — location update */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <h2 className="font-bold text-gray-900 mb-4">Обновить местоположение</h2>
            <form onSubmit={handleUpdateLocation} className="space-y-3">
              <div>
                <label className="label">Широта (lat)</label>
                <input
                  type="number"
                  step="0.000001"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  placeholder="43.238649"
                  className="input"
                />
              </div>
              <div>
                <label className="label">Долгота (lng)</label>
                <input
                  type="number"
                  step="0.000001"
                  value={lng}
                  onChange={(e) => setLng(e.target.value)}
                  placeholder="76.945112"
                  className="input"
                />
              </div>
              <button
                type="button"
                onClick={handleGeoLocate}
                className="btn-secondary w-full text-sm"
              >
                📍 Определить автоматически
              </button>
              <button
                type="submit"
                disabled={updatingLoc || !lat || !lng}
                className="btn-primary w-full"
              >
                {updatingLoc ? 'Сохранение...' : 'Обновить и перейти в онлайн'}
              </button>
            </form>

            {profile?.current_lat && (
              <div className="mt-4 rounded-xl bg-gray-50 p-3">
                <div className="text-xs text-gray-500 mb-1">Текущее местоположение</div>
                <div className="font-mono text-sm text-gray-800">
                  {profile.current_lat.toFixed(5)}, {profile.current_lng.toFixed(5)}
                </div>
              </div>
            )}
          </div>

          {/* Stats */}
          {profile && (
            <div className="rounded-2xl border border-gray-200 bg-white p-5">
              <h2 className="font-bold text-gray-900 mb-4">Статистика</h2>
              <div className="space-y-3">
                {[
                  { label: 'Всего доставок', value: profile.total_deliveries, icon: '📦' },
                  { label: 'Активных сейчас', value: activeDeliveries.length, icon: '🔄' },
                  { label: 'Успешных', value: completedDeliveries.filter(d => d.status === 'delivered').length, icon: '✅' },
                ].map(({ label, value, icon }) => (
                  <div key={label} className="flex items-center justify-between rounded-xl bg-gray-50 px-4 py-3">
                    <span className="text-sm text-gray-600">{icon} {label}</span>
                    <span className="font-bold text-gray-900">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
