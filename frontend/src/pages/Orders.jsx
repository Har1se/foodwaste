import { useCallback, useEffect, useState } from 'react'
import { ordersApi, paymentsApi } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import { ORDER_STATUS_COLORS, ORDER_STATUS_LABELS } from '../utils/constants'

export default function Orders() {
  const toast = useToast()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [paying, setPaying] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await ordersApi.list({ limit: 100 })
      setOrders(data.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось загрузить заказы')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const pay = async (orderId) => {
    setPaying(orderId)
    try {
      await paymentsApi.initiate(orderId)
      await paymentsApi.simulateSuccess(orderId)
      toast.success('Оплата успешно проведена в demo-режиме')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось оплатить заказ')
    } finally {
      setPaying(null)
    }
  }

  const cancel = async (orderId) => {
    try {
      await ordersApi.updateStatus(orderId, { status: 'cancelled', reason: 'Cancelled by customer' })
      toast.success('Заказ отменен')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось отменить заказ')
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">Покупатель</p>
          <h1 className="mt-1 text-3xl font-bold text-gray-950">Мои заказы</h1>
        </div>
        <button className="btn-secondary" onClick={load}>Обновить</button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-32 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-red-700">{error}</div>
      ) : orders.length === 0 ? (
        <div className="card p-10 text-center">
          <h2 className="text-lg font-semibold text-gray-950">Заказов пока нет</h2>
          <p className="mt-2 text-sm text-gray-500">Выберите продукт на главной странице и оформите первый заказ.</p>
          <a href="/" className="btn-primary mt-5">Перейти в маркет</a>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <article key={order.id} className="card p-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-start">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold text-gray-950">Заказ #{order.id}</h2>
                    <span className={`badge ${ORDER_STATUS_COLORS[order.status] || 'bg-gray-100'}`}>
                      {ORDER_STATUS_LABELS[order.status] || order.status}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 text-sm text-gray-600 sm:grid-cols-2">
                    <p>Сумма: <strong className="text-gray-950">{order.total_amount.toLocaleString()} ₸</strong></p>
                    <p>Позиции: {order.items?.length || 0}</p>
                    <p>Дата: {new Date(order.created_at).toLocaleString('ru-RU')}</p>
                    <p>Код выдачи: <span className="font-mono font-semibold text-emerald-700">{order.pickup_token}</span></p>
                  </div>
                  {order.items?.length > 0 && (
                    <div className="mt-4 rounded-lg bg-gray-50 p-3">
                      {order.items.map((item) => (
                        <p key={item.id} className="text-xs text-gray-500">
                          Продукт #{item.listing_id}: {item.quantity} шт. по {item.unit_price.toLocaleString()} ₸
                        </p>
                      ))}
                    </div>
                  )}
                </div>

                {order.status === 'pending' && (
                  <div className="flex gap-2 md:flex-col">
                    <button className="btn-primary" disabled={paying === order.id} onClick={() => pay(order.id)}>
                      {paying === order.id ? 'Оплата...' : 'Оплатить'}
                    </button>
                    <button className="btn-danger" onClick={() => cancel(order.id)}>
                      Отменить
                    </button>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
