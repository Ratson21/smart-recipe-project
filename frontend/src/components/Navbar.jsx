import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function BrandMark() {
  return (
    <Link to="/" className="flex items-center gap-1 group shrink-0">
      <span className="font-display text-xl font-bold text-gray-900 tracking-tight group-hover:text-green-600 transition-colors">
        Smart Recipe
      </span>
    </Link>
  )
}

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `text-sm transition-colors ${
          isActive
            ? 'text-gray-900 font-semibold'
            : 'text-gray-500 hover:text-gray-900'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

export default function Navbar() {
  const { isLoggedIn, user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-20 bg-gray-50/90 backdrop-blur-md border-b border-gray-200/70">
      <div className="max-w-6xl mx-auto px-5 sm:px-6 h-16 flex items-center justify-between gap-6">

        <BrandMark />

        <nav className="hidden sm:flex items-center gap-7">
          <NavItem to="/how-it-works">Cara Kerja</NavItem>
          <NavItem to="/evaluation">Evaluasi</NavItem>
        </nav>

        <div className="flex items-center gap-2 shrink-0">
          {isLoggedIn ? (
            <>
              <Link
                to="/profile"
                className="hidden sm:flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 transition-colors px-2 py-1.5 rounded-lg hover:bg-gray-100"
              >
                <span className="w-7 h-7 rounded-full bg-green-100 text-green-700 grid place-items-center text-xs font-semibold select-none">
                  {user?.full_name?.[0]?.toUpperCase() ?? '?'}
                </span>
                <span className="max-w-[110px] truncate font-medium">{user?.full_name}</span>
              </Link>
              <button
                onClick={handleLogout}
                className="hidden sm:inline text-xs text-gray-500 hover:text-red-600 transition-colors px-3 py-1.5 rounded-lg hover:bg-red-50 font-medium"
              >
                Keluar
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm text-gray-600 hover:text-gray-900 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors font-medium">
                Masuk
              </Link>
              <Link to="/register" className="text-sm font-semibold bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors shadow-card">
                Daftar
              </Link>
            </>
          )}
        </div>

      </div>
    </header>
  )
}
