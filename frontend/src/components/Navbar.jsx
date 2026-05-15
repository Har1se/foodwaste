import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  const links = [
    { to: '/', label: 'Маркет', show: true },
    { to: '/orders', label: 'Мои заказы', show: user?.role === 'customer' || user?.role === 'admin' },
    { to: '/vendor', label: 'Продавцу', show: user?.role === 'vendor' || user?.role === 'admin' },
    { to: '/admin', label: 'Админ', show: user?.role === 'admin' },
  ].filter((item) => item.show)

  const isActive = (to) => location.pathname === to

  const handleLogout = async () => {
    await logout()
    setOpen(false)
    navigate('/login')
  }

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-3" onClick={() => setOpen(false)}>
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600 text-sm font-black text-white">
            RB
          </span>
          <div>
            <div className="text-base font-bold leading-5 text-gray-950">RescueBite</div>
            <div className="hidden text-xs text-gray-500 sm:block">еда со скидкой рядом</div>
          </div>
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                isActive(link.to)
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-950'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-3 md:flex">
          {user ? (
            <>
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">{user.full_name || user.email}</div>
                <div className="text-xs capitalize text-gray-500">{user.role}</div>
              </div>
              <button className="btn-secondary" onClick={handleLogout}>Выйти</button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-secondary">Войти</Link>
              <Link to="/register" className="btn-primary">Создать аккаунт</Link>
            </>
          )}
        </div>

        <button
          type="button"
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium md:hidden"
          onClick={() => setOpen((value) => !value)}
        >
          Меню
        </button>
      </div>

      {open && (
        <div className="border-t border-gray-100 bg-white px-4 py-3 md:hidden">
          <div className="space-y-1">
            {links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setOpen(false)}
                className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive(link.to) ? 'bg-emerald-50 text-emerald-700' : 'text-gray-700'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="mt-3 border-t border-gray-100 pt-3">
            {user ? (
              <button className="btn-secondary w-full" onClick={handleLogout}>Выйти</button>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <Link to="/login" onClick={() => setOpen(false)} className="btn-secondary">Войти</Link>
                <Link to="/register" onClick={() => setOpen(false)} className="btn-primary">Регистрация</Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
