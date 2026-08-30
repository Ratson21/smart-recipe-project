import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import ErrorMessage from '../components/ErrorMessage'

function StatCard({ icon, label, value, loading }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-card p-5 text-center">
      <div className="text-2xl mb-1.5">{icon}</div>
      <div className={`font-display text-2xl font-extrabold text-gray-900 ${loading ? 'animate-pulse' : ''}`}>
        {loading ? (
          <div className="h-7 w-10 bg-gray-100 rounded mx-auto" />
        ) : value}
      </div>
      <div className="text-[11px] text-gray-500 mt-1 uppercase tracking-wider font-medium">{label}</div>
    </div>
  )
}

function formatJoin(isoString) {
  if (!isoString) return '-'
  return new Date(isoString).toLocaleDateString('id-ID', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

export default function ProfilePage() {
  const { isLoggedIn, user, logout } = useAuth()
  const navigate                     = useNavigate()

  const [bookmarkCount, setBookmarkCount] = useState(null)
  const [historyCount,  setHistoryCount]  = useState(null)
  const [statsLoading, setStatsLoading]   = useState(true)
  const [statsError,   setStatsError]     = useState('')

  function loadStats() {
    setStatsLoading(true)
    setStatsError('')
    Promise.allSettled([
      api.get('/bookmarks'),
      api.get('/history'),
    ]).then(([bmRes, histRes]) => {
      if (bmRes.status   === 'fulfilled') setBookmarkCount(bmRes.value.data.length)
      else setBookmarkCount(null)

      if (histRes.status === 'fulfilled') setHistoryCount(histRes.value.data.length)
      else setHistoryCount(null)

      if (bmRes.status === 'rejected' && histRes.status === 'rejected')
        setStatsError('Gagal memuat statistik. Periksa koneksi internet kamu.')
    }).finally(() => setStatsLoading(false))
  }

  // Track intentional logout so the effect goes to '/' instead of '/login'
  const loggingOut = useRef(false)

  useEffect(() => {
    if (!isLoggedIn) {
      navigate(loggingOut.current ? '/' : '/login', { replace: true })
      loggingOut.current = false
      return
    }
    loadStats()
  }, [isLoggedIn])

  function handleLogout() {
    loggingOut.current = true
    logout()
  }

  if (!isLoggedIn) return null

  const initials = user?.full_name
    ?.split(' ')
    .map(w => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() ?? '?'

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <main className="max-w-lg mx-auto px-5 sm:px-6 py-12">

        {/* Avatar + identity */}
        <div className="flex flex-col items-center text-center mb-10">
          <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-green-400 to-green-600 text-white flex items-center justify-center text-3xl font-bold select-none shadow-card-hover mb-5 ring-4 ring-white">
            {initials}
          </div>
          <h1 className="font-display text-2xl font-extrabold text-gray-900">{user?.full_name}</h1>
          <p className="text-sm text-gray-500 mt-1">{user?.email}</p>
          <p className="text-xs text-gray-400 mt-1.5">
            Bergabung sejak {formatJoin(user?.created_at)}
          </p>
        </div>

        {/* Stats error */}
        {statsError && (
          <div className="mb-6">
            <ErrorMessage message={statsError} onRetry={loadStats} />
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-10">
          <StatCard
            icon="🔖"
            label="Tersimpan"
            value={bookmarkCount ?? '-'}
            loading={statsLoading}
          />
          <StatCard
            icon="👁"
            label="Dilihat"
            value={historyCount != null ? `${historyCount}` : '-'}
            loading={statsLoading}
          />
          <StatCard
            icon="📅"
            label="Hari ini"
            value={new Date().toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}
            loading={false}
          />
        </div>

        {/* Quick links */}
        <div className="space-y-2.5 mb-10">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Menu</p>

          {[
            { to: '/bookmarks', icon: '🔖', title: 'Resep Tersimpan', sub: statsLoading ? '...' : `${bookmarkCount ?? 0} resep` },
            { to: '/history',   icon: '📖', title: 'Riwayat Tontonan', sub: statsLoading ? '...' : `${historyCount ?? 0} resep terakhir` },
            { to: '/',          icon: '🔍', title: 'Cari Resep', sub: 'Temukan resep baru hari ini' },
          ].map(item => (
            <Link
              key={item.to + item.title}
              to={item.to}
              className="flex items-center justify-between bg-white rounded-2xl border border-gray-200 shadow-card px-5 py-4 hover:border-green-300 hover:shadow-card-hover transition-all group"
            >
              <div className="flex items-center gap-3.5">
                <span className="w-10 h-10 rounded-xl bg-gray-50 ring-1 ring-gray-100 grid place-items-center text-xl">
                  {item.icon}
                </span>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{item.title}</p>
                  <p className="text-xs text-gray-500">{item.sub}</p>
                </div>
              </div>
              <svg className="w-4 h-4 text-gray-300 group-hover:text-green-500 group-hover:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          ))}
        </div>

        {/* Logout */}
        <button
          type="button"
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-rose-200 text-rose-600 hover:bg-rose-50 hover:border-rose-300 text-sm font-semibold transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Keluar dari akun
        </button>

      </main>
    </div>
  )
}
