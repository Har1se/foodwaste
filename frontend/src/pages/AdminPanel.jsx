import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import { LISTING_STATUS_COLORS, LISTING_STATUS_LABELS, ORDER_STATUS_COLORS, ORDER_STATUS_LABELS } from '../utils/constants'

const TABS = [
  ['overview', 'Обзор'],
  ['users', 'Пользователи'],
  ['vendors', 'Продавцы'],
  ['listings', 'Продукты'],
  ['orders', 'Заказы'],
  ['jobs', 'Задачи'],
]

export default function AdminPanel() {
  const toast = useToast()
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [vendors, setVendors] = useState([])
  const [listings, setListings] = useState([])
  const [orders, setOrders] = useState([])
  const [jobs, setJobs] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      if (tab === 'overview') {
        const { data } = await adminApi.stats()
        setStats(data)
      }
      if (tab === 'users') {
        const { data } = await adminApi.users({ limit: 100 })
        setUsers(data.data)
      }
      if (tab === 'vendors') {
        const { data } = await adminApi.vendors()
        setVendors(data)
      }
      if (tab === 'listings') {
        const { data } = await adminApi.listings({ limit: 100 })
        setListings(data.data)
      }
      if (tab === 'orders') {
        const { data } = await adminApi.orders({ limit: 100 })
        setOrders(data.data)
      }
      if (tab === 'jobs') {
        const { data } = await adminApi.jobs()
        setJobs(data)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось загрузить данные')
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => {
    load()
  }, [load])

  const approveVendor = async (id, action = 'approve') => {
    try {
      await adminApi.approveVendor(id, { action, reason: 'Demo approval' })
      toast.success(action === 'approve' ? 'Продавец одобрен' : 'Продавец отклонен')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось обновить продавца')
    }
  }

  const toggleUser = async (user) => {
    try {
      await adminApi.updateUser(user.id, { is_active: !user.is_active })
      toast.success('Статус пользователя обновлен')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось обновить пользователя')
    }
  }

  const triggerDecay = async () => {
    try {
      const { data } = await adminApi.triggerDecay()
      toast.success(data.detail || 'Price decay выполнен')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось запустить price decay')
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col justify-between gap-3 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">Администрирование</p>
          <h1 className="mt-1 text-3xl font-bold text-gray-950">Панель RescueBite</h1>
        </div>
        <button className="btn-secondary" onClick={load}>Обновить</button>
      </div>

      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-gray-200">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium ${
              tab === key
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-gray-500 hover:text-gray-950'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-red-700">{error}</div>
      ) : (
        <>
          {tab === 'overview' && <Overview stats={stats} onTriggerDecay={triggerDecay} />}
          {tab === 'users' && <Users users={users} onToggle={toggleUser} />}
          {tab === 'vendors' && <Vendors vendors={vendors} onApprove={approveVendor} />}
          {tab === 'listings' && <Listings listings={listings} />}
          {tab === 'orders' && <Orders orders={orders} />}
          {tab === 'jobs' && <Jobs jobs={jobs} />}
        </>
      )}
    </div>
  )
}

function Overview({ stats, onTriggerDecay }) {
  const items = [
    ['Пользователи', stats?.total_users ?? 0],
    ['Продавцы', stats?.total_vendors ?? 0],
    ['Продукты', stats?.total_listings ?? 0],
    ['Активные', stats?.active_listings ?? 0],
    ['Заказы', stats?.total_orders ?? 0],
    ['Ожидают', stats?.pending_orders ?? 0],
  ]
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
        {items.map(([label, value]) => (
          <div key={label} className="card p-4">
            <div className="text-2xl font-bold text-gray-950">{value}</div>
            <div className="text-sm text-gray-500">{label}</div>
          </div>
        ))}
      </div>
      <div className="card p-5">
        <h2 className="font-semibold text-gray-950">Инструменты</h2>
        <p className="mt-1 text-sm text-gray-500">Ручной запуск пересчета цен для старых продуктов.</p>
        <button className="btn-secondary mt-4" onClick={onTriggerDecay}>Запустить price decay</button>
      </div>
    </div>
  )
}

function Users({ users, onToggle }) {
  return (
    <Table
      headers={['ID', 'Email', 'Имя', 'Роль', 'Статус', 'Действие']}
      rows={users.map((user) => [
        `#${user.id}`,
        user.email,
        user.full_name || '-',
        user.role,
        user.is_active ? 'Активен' : 'Заблокирован',
        <button key={user.id} className="text-sm font-medium text-emerald-700 hover:underline" onClick={() => onToggle(user)}>
          {user.is_active ? 'Заблокировать' : 'Активировать'}
        </button>,
      ])}
    />
  )
}

function Vendors({ vendors, onApprove }) {
  return (
    <div className="space-y-3">
      {vendors.map((vendor) => (
        <div key={vendor.id} className="card flex flex-col justify-between gap-3 p-4 sm:flex-row sm:items-center">
          <div>
            <div className="font-semibold text-gray-950">{vendor.business_name}</div>
            <div className="text-sm text-gray-500">{vendor.address}, БИН {vendor.bin_number}</div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`badge ${vendor.is_approved ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
              {vendor.is_approved ? 'Одобрен' : 'Ожидает'}
            </span>
            {!vendor.is_approved && (
              <button className="btn-primary" onClick={() => onApprove(vendor.id)}>Одобрить</button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function Listings({ listings }) {
  return (
    <Table
      headers={['ID', 'Название', 'Цена', 'Остаток', 'Статус']}
      rows={listings.map((item) => [
        `#${item.id}`,
        item.title,
        `${item.current_price.toLocaleString()} ₸`,
        `${item.quantity_available}/${item.quantity_total}`,
        <span key={item.id} className={`badge ${LISTING_STATUS_COLORS[item.status] || 'bg-gray-100'}`}>
          {LISTING_STATUS_LABELS[item.status] || item.status}
        </span>,
      ])}
    />
  )
}

function Orders({ orders }) {
  return (
    <Table
      headers={['ID', 'Покупатель', 'Сумма', 'Статус', 'Дата']}
      rows={orders.map((order) => [
        `#${order.id}`,
        `#${order.customer_id}`,
        `${order.total_amount.toLocaleString()} ₸`,
        <span key={order.id} className={`badge ${ORDER_STATUS_COLORS[order.status] || 'bg-gray-100'}`}>
          {ORDER_STATUS_LABELS[order.status] || order.status}
        </span>,
        new Date(order.created_at).toLocaleDateString('ru-RU'),
      ])}
    />
  )
}

function Jobs({ jobs }) {
  if (!jobs) {
    return (
      <div className="card p-8 text-center text-gray-500">
        Celery worker недоступен. Запустите worker, если хотите смотреть очередь задач.
      </div>
    )
  }
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {[
        ['Активные', jobs.queue_stats?.active ?? 0],
        ['Reserved', jobs.queue_stats?.reserved ?? 0],
        ['Scheduled', jobs.queue_stats?.scheduled ?? 0],
        ['Workers', jobs.queue_stats?.workers?.length ?? 0],
      ].map(([label, value]) => (
        <div key={label} className="card p-4">
          <div className="text-2xl font-bold text-gray-950">{value}</div>
          <div className="text-sm text-gray-500">{label}</div>
        </div>
      ))}
    </div>
  )
}

function Table({ headers, rows }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-200 bg-gray-50">
            <tr>
              {headers.map((header) => (
                <th key={header} className="px-4 py-3 text-left font-medium text-gray-500">{header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-gray-500" colSpan={headers.length}>Нет данных</td>
              </tr>
            ) : rows.map((row, index) => (
              <tr key={index} className="hover:bg-gray-50">
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="px-4 py-3 text-gray-700">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
