import { useCallback, useEffect, useRef, useState } from 'react'
import { adminApi } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import {
  LISTING_STATUS_COLORS,
  LISTING_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  ORDER_STATUS_LABELS,
} from '../utils/constants'

const TABS = [
  ['overview', 'Обзор'],
  ['users', 'Пользователи'],
  ['vendors', 'Продавцы'],
  ['listings', 'Продукты'],
  ['orders', 'Заказы'],
  ['logs', 'Логи'],
  ['jobs', 'Задачи'],
]

const LEVEL_COLORS = {
  info:    'bg-sky-100 text-sky-700',
  warning: 'bg-amber-100 text-amber-800',
  error:   'bg-red-100 text-red-700',
}

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
  const [logs, setLogs] = useState([])
  const [jobs, setJobs] = useState(null)

  const load = useCallback(async (logParams) => {
    setLoading(true)
    setError('')
    try {
      if (tab === 'overview') {
        const { data } = await adminApi.stats()
        setStats(data)
      } else if (tab === 'users') {
        const { data } = await adminApi.users({ limit: 100 })
        setUsers(data.data)
      } else if (tab === 'vendors') {
        const { data } = await adminApi.vendors()
        setVendors(data)
      } else if (tab === 'listings') {
        const { data } = await adminApi.listings({ limit: 100 })
        setListings(data.data)
      } else if (tab === 'orders') {
        const { data } = await adminApi.orders({ limit: 100 })
        setOrders(data.data)
      } else if (tab === 'logs') {
        const { data } = await adminApi.logs({ limit: 100, ...logParams })
        setLogs(data.data)
      } else if (tab === 'jobs') {
        const { data } = await adminApi.jobs()
        setJobs(data)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось загрузить данные')
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => { load() }, [load])

  const approveVendor = async (id, action = 'approve') => {
    try {
      await adminApi.approveVendor(id, { action, reason: 'Admin action' })
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

  const seedReset = async () => {
    try {
      const { data } = await adminApi.seedReset()
      toast.success(data.detail || 'Seed reset выполнен')
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Не удалось выполнить seed reset')
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col justify-between gap-3 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
            Администрирование
          </p>
          <h1 className="mt-1 text-3xl font-bold text-gray-950">Панель RescueBite</h1>
        </div>
        <button className="btn-secondary self-start" onClick={() => load()}>
          Обновить
        </button>
      </div>

      {/* Tab bar */}
      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-gray-200">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
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
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-red-700">{error}</div>
      ) : (
        <>
          {tab === 'overview' && (
            <Overview stats={stats} onTriggerDecay={triggerDecay} onSeedReset={seedReset} />
          )}
          {tab === 'users' && <Users users={users} onToggle={toggleUser} />}
          {tab === 'vendors' && <Vendors vendors={vendors} onApprove={approveVendor} />}
          {tab === 'listings' && <Listings listings={listings} />}
          {tab === 'orders' && <Orders orders={orders} />}
          {tab === 'logs' && <Logs initialLogs={logs} onFilter={(p) => load(p)} />}
          {tab === 'jobs' && <Jobs jobs={jobs} />}
        </>
      )}
    </div>
  )
}

// ── Tab components ────────────────────────────────────────────────────────────

function Overview({ stats, onTriggerDecay, onSeedReset }) {
  const items = [
    ['Пользователи', stats?.total_users ?? 0],
    ['Продавцы', stats?.total_vendors ?? 0],
    ['Продуктов', stats?.total_listings ?? 0],
    ['Активных', stats?.active_listings ?? 0],
    ['Заказов', stats?.total_orders ?? 0],
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
      <div className="card p-5 space-y-4">
        <h2 className="font-semibold text-gray-950">Инструменты</h2>
        <div className="flex flex-wrap gap-3">
          <div>
            <p className="text-sm text-gray-500 mb-2">Пересчитать цены для устаревших продуктов.</p>
            <button className="btn-secondary" onClick={onTriggerDecay}>
              Запустить price decay
            </button>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-2">Сбросить и пересоздать демо-данные.</p>
            <button className="btn-secondary" onClick={onSeedReset}>
              Seed reset
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Users({ users, onToggle }) {
  return (
    <Table
      headers={['ID', 'Email', 'Имя', 'Роль', 'Статус', 'Действие']}
      rows={users.map((u) => ({
        key: `user-${u.id}`,
        cells: [
          `#${u.id}`,
          u.email,
          u.full_name || '—',
          u.role,
          u.is_active ? (
            <span className="badge bg-emerald-100 text-emerald-700">Активен</span>
          ) : (
            <span className="badge bg-red-100 text-red-700">Заблокирован</span>
          ),
          <button
            key="action"
            className="text-sm font-medium text-emerald-700 hover:underline"
            onClick={() => onToggle(u)}
          >
            {u.is_active ? 'Заблокировать' : 'Активировать'}
          </button>,
        ],
      }))}
    />
  )
}

function Vendors({ vendors, onApprove }) {
  return (
    <div className="space-y-3">
      {vendors.map((v) => (
        <div
          key={`vendor-${v.id}`}
          className="card flex flex-col justify-between gap-3 p-4 sm:flex-row sm:items-center"
        >
          <div>
            <div className="font-semibold text-gray-950">{v.business_name}</div>
            <div className="text-sm text-gray-500">
              {v.address}, БИН {v.bin_number}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`badge ${
                v.is_approved ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
              }`}
            >
              {v.is_approved ? 'Одобрен' : 'Ожидает'}
            </span>
            {!v.is_approved && (
              <button className="btn-primary" onClick={() => onApprove(v.id)}>
                Одобрить
              </button>
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
      rows={listings.map((item) => ({
        key: `listing-${item.id}`,
        cells: [
          `#${item.id}`,
          item.title,
          `${item.current_price.toLocaleString()} ₸`,
          `${item.quantity_available}/${item.quantity_total}`,
          <span
            key="status"
            className={`badge ${LISTING_STATUS_COLORS[item.status] || 'bg-gray-100'}`}
          >
            {LISTING_STATUS_LABELS[item.status] || item.status}
          </span>,
        ],
      }))}
    />
  )
}

function Orders({ orders }) {
  return (
    <Table
      headers={['ID', 'Покупатель', 'Сумма', 'Статус', 'Дата']}
      rows={orders.map((o) => ({
        key: `order-${o.id}`,
        cells: [
          `#${o.id}`,
          `#${o.customer_id}`,
          `${o.total_amount.toLocaleString()} ₸`,
          <span
            key="status"
            className={`badge ${ORDER_STATUS_COLORS[o.status] || 'bg-gray-100'}`}
          >
            {ORDER_STATUS_LABELS[o.status] || o.status}
          </span>,
          new Date(o.created_at).toLocaleDateString('ru-RU'),
        ],
      }))}
    />
  )
}

// ── Logs tab ──────────────────────────────────────────────────────────────────

function Logs({ initialLogs, onFilter }) {
  const [logs, setLogs] = useState(initialLogs)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    user_id: '',
    endpoint: '',
    level: '',
    date_from: '',
    date_to: '',
  })

  const applyFilters = async () => {
    setLoading(true)
    try {
      const params = { limit: 100 }
      if (filters.user_id) params.user_id = Number(filters.user_id)
      if (filters.endpoint) params.endpoint = filters.endpoint
      if (filters.level) params.level = filters.level
      if (filters.date_from) params.date_from = new Date(filters.date_from).toISOString()
      if (filters.date_to) params.date_to = new Date(filters.date_to).toISOString()
      const { data } = await adminApi.logs(params)
      setLogs(data.data)
    } catch {
      // error handled by parent
    } finally {
      setLoading(false)
    }
  }

  const reset = async () => {
    setFilters({ user_id: '', endpoint: '', level: '', date_from: '', date_to: '' })
    setLoading(true)
    try {
      const { data } = await adminApi.logs({ limit: 100 })
      setLogs(data.data)
    } finally {
      setLoading(false)
    }
  }

  const levelCounts = logs.reduce((acc, l) => {
    acc[l.level] = (acc[l.level] || 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {/* Filter panel */}
      <div className="card p-4 space-y-3">
        <h2 className="font-semibold text-gray-950 text-sm">Фильтры</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <div>
            <label className="label text-xs">User ID</label>
            <input
              className="input text-sm"
              type="number"
              placeholder="Все"
              value={filters.user_id}
              onChange={(e) => setFilters((f) => ({ ...f, user_id: e.target.value }))}
            />
          </div>
          <div>
            <label className="label text-xs">Endpoint</label>
            <input
              className="input text-sm"
              placeholder="/auth, /orders…"
              value={filters.endpoint}
              onChange={(e) => setFilters((f) => ({ ...f, endpoint: e.target.value }))}
            />
          </div>
          <div>
            <label className="label text-xs">Уровень</label>
            <select
              className="input text-sm"
              value={filters.level}
              onChange={(e) => setFilters((f) => ({ ...f, level: e.target.value }))}
            >
              <option value="">Все</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
          <div>
            <label className="label text-xs">С</label>
            <input
              className="input text-sm"
              type="datetime-local"
              value={filters.date_from}
              onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))}
            />
          </div>
          <div>
            <label className="label text-xs">По</label>
            <input
              className="input text-sm"
              type="datetime-local"
              value={filters.date_to}
              onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))}
            />
          </div>
        </div>
        <div className="flex gap-2">
          <button className="btn-primary text-sm" onClick={applyFilters} disabled={loading}>
            {loading ? 'Загружаем…' : 'Применить'}
          </button>
          <button className="btn-secondary text-sm" onClick={reset} disabled={loading}>
            Сбросить
          </button>
        </div>
      </div>

      {/* Summary badges */}
      {logs.length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="badge bg-gray-100 text-gray-700">Всего: {logs.length}</span>
          {Object.entries(levelCounts).map(([lvl, cnt]) => (
            <span key={lvl} className={`badge ${LEVEL_COLORS[lvl] || 'bg-gray-100'}`}>
              {lvl}: {cnt}
            </span>
          ))}
        </div>
      )}

      {/* Log table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                {['ID', 'Время', 'User', 'Метод', 'Endpoint', 'Статус', 'Уровень', 'Время (мс)', 'IP'].map(
                  (h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-3 text-left font-medium text-gray-500">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.length === 0 ? (
                <tr>
                  <td className="px-3 py-8 text-center text-gray-500" colSpan={9}>
                    Нет логов
                  </td>
                </tr>
              ) : (
                logs.map((lg) => (
                  <LogRow key={`log-${lg.id}`} log={lg} />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function LogRow({ log }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <tr
        className={`cursor-pointer hover:bg-gray-50 transition-colors ${
          log.level === 'error' ? 'bg-red-50/40' : log.level === 'warning' ? 'bg-amber-50/30' : ''
        }`}
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-3 py-2 text-gray-400">#{log.id}</td>
        <td className="px-3 py-2 whitespace-nowrap text-gray-600">
          {new Date(log.created_at).toLocaleString('ru-RU', {
            month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
          })}
        </td>
        <td className="px-3 py-2 text-gray-700">
          {log.user_id ? (
            <span className="font-mono">#{log.user_id} <span className="text-gray-400">({log.role})</span></span>
          ) : '—'}
        </td>
        <td className="px-3 py-2">
          <span className={`badge text-[10px] font-bold ${
            log.method === 'GET' ? 'bg-sky-100 text-sky-700' :
            log.method === 'POST' ? 'bg-emerald-100 text-emerald-700' :
            log.method === 'DELETE' ? 'bg-red-100 text-red-700' :
            'bg-gray-100 text-gray-700'
          }`}>
            {log.method}
          </span>
        </td>
        <td className="px-3 py-2 font-mono text-gray-800 max-w-[200px] truncate" title={log.endpoint}>
          {log.endpoint}
        </td>
        <td className="px-3 py-2">
          <span className={`font-bold ${
            log.response_status >= 500 ? 'text-red-600' :
            log.response_status >= 400 ? 'text-amber-600' : 'text-gray-700'
          }`}>
            {log.response_status}
          </span>
        </td>
        <td className="px-3 py-2">
          <span className={`badge text-[10px] ${LEVEL_COLORS[log.level] || 'bg-gray-100 text-gray-700'}`}>
            {log.level}
          </span>
        </td>
        <td className="px-3 py-2 text-gray-500">{log.duration_ms}мс</td>
        <td className="px-3 py-2 font-mono text-gray-400 text-[10px]">{log.ip_address || '—'}</td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={9} className="bg-gray-50 px-4 py-3 text-xs">
            <div className="space-y-2">
              {log.user_agent && (
                <p className="text-gray-500">
                  <span className="font-semibold text-gray-700">User-Agent:</span> {log.user_agent}
                </p>
              )}
              {log.request_body && (
                <div>
                  <span className="font-semibold text-gray-700">Request body:</span>
                  <pre className="mt-1 rounded bg-white border border-gray-200 p-2 overflow-x-auto text-[10px] text-gray-600">
                    {log.request_body}
                  </pre>
                </div>
              )}
              {log.error_message && (
                <p className="text-red-600">
                  <span className="font-semibold">Error:</span> {log.error_message}
                </p>
              )}
              {log.error_traceback && (
                <pre className="rounded bg-red-50 border border-red-200 p-2 overflow-x-auto text-[10px] text-red-700">
                  {log.error_traceback}
                </pre>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function Jobs({ jobs }) {
  if (!jobs) {
    return (
      <div className="card p-8 text-center text-gray-500">
        Celery worker недоступен. Запустите worker для просмотра очереди задач.
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

// ── Generic table ─────────────────────────────────────────────────────────────

function Table({ headers, rows }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-200 bg-gray-50">
            <tr>
              {headers.map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-gray-500" colSpan={headers.length}>
                  Нет данных
                </td>
              </tr>
            ) : (
              rows.map(({ key, cells }) => (
                <tr key={key} className="hover:bg-gray-50">
                  {cells.map((cell, ci) => (
                    <td key={ci} className="px-4 py-3 text-gray-700">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
