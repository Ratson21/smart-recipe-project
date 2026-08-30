import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins  = Math.floor(diff / 60_000)
  const hours = Math.floor(mins  / 60)
  const days  = Math.floor(hours / 24)
  if (mins  <  1) return 'Baru saja'
  if (mins  < 60) return `${mins} mnt lalu`
  if (hours < 24) return `${hours} jam lalu`
  if (days  === 1) return 'Kemarin'
  if (days  <  7) return `${days} hari lalu`
  return new Date(iso).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })
}

const CATEGORY_EMOJI = {
  ayam: '🍗', seafood: '🐟', ikan: '🐟', udang: '🦐', daging: '🥩',
  sayur: '🥬', tahu: '🥘', tempe: '🥘', telur: '🥚',
  nasi: '🍚', mie: '🍜', sup: '🍲', kue: '🍰',
}

function getCategoryEmoji(category = '') {
  const c = category.toLowerCase()
  for (const [k, v] of Object.entries(CATEGORY_EMOJI)) {
    if (c.includes(k)) return v
  }
  return '🍳'
}

const DIFFICULTY_STYLE = {
  Mudah:  'bg-green-50  text-green-700  ring-1 ring-green-100',
  Sedang: 'bg-amber-50  text-amber-700  ring-1 ring-amber-100',
  Sulit:  'bg-rose-50   text-rose-700   ring-1 ring-rose-100',
}

function HistoryRow({ item }) {
  const { recipe, viewed_at } = item
  const emoji     = getCategoryEmoji(recipe.category)
  const diffStyle = DIFFICULTY_STYLE[recipe.difficulty_level] ?? ''

  return (
    <Link
      to={`/recipe/${recipe.id}`}
      className="flex items-center gap-4 p-4 bg-white rounded-2xl border border-gray-200 shadow-card hover:shadow-card-hover hover:border-green-300 transition-all group"
    >
      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 ring-1 ring-gray-200 flex items-center justify-center text-2xl shrink-0">
        {emoji}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-display font-bold text-[15px] text-gray-900 truncate group-hover:text-green-700 transition-colors">
          {recipe.title}
        </p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1">
          {recipe.category && (
            <span className="text-xs text-gray-500 font-medium">{recipe.category}</span>
          )}
          {recipe.estimated_time_minutes > 0 && (
            <span className="text-xs text-gray-400">⏱ {recipe.estimated_time_minutes} mnt</span>
          )}
          {recipe.difficulty_level && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${diffStyle}`}>
              {recipe.difficulty_level}
            </span>
          )}
        </div>
      </div>
      <span className="text-xs text-gray-400 shrink-0 hidden sm:block font-medium">{timeAgo(viewed_at)}</span>
      <svg className="w-4 h-4 text-gray-300 group-hover:text-green-500 group-hover:translate-x-0.5 transition-all shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 5l7 7-7 7" />
      </svg>
    </Link>
  )
}

export default function HistoryPage() {
  const { isLoggedIn }    = useAuth()
  const navigate          = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  function load() {
    setLoading(true)
    setError('')
    api.get('/history')
      .then(r => setItems(r.data))
      .catch(() => setError('Gagal memuat riwayat. Periksa koneksi internet kamu.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!isLoggedIn) { navigate('/login', { replace: true }); return }
    load()
  }, [isLoggedIn])

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <main className="max-w-3xl mx-auto px-5 sm:px-6 py-10">

        <div className="mb-8">
          <p className="text-[11px] font-semibold text-green-700 uppercase tracking-wider mb-1">Aktivitas</p>
          <h1 className="font-display text-3xl font-extrabold text-gray-900">Riwayat Tontonan</h1>
          <p className="text-sm text-gray-500 mt-1.5">
            {loading ? 'Memuat...' : `${items.length} resep terakhir yang kamu lihat`}
          </p>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorMessage message={error} onRetry={load} />
          </div>
        )}

        {loading && (
          <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-20 bg-white rounded-2xl border border-gray-200 shadow-card animate-pulse" />
            ))}
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <EmptyState
            icon="📖"
            title="Belum ada riwayat"
            body="Mulai jelajahi resep dan riwayatmu akan muncul di sini."
            action={{ label: 'Cari Resep', to: '/' }}
          />
        )}

        {!loading && items.length > 0 && (
          <div className="space-y-3">
            {items.map((item, i) => (
              <HistoryRow key={`${item.recipe.id}-${i}`} item={item} />
            ))}
            <p className="text-center text-xs text-gray-400 pt-4">
              Menampilkan {items.length} riwayat terbaru
            </p>
          </div>
        )}

      </main>
    </div>
  )
}
