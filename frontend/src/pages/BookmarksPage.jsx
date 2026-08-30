import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import RecipeCard from '../components/RecipeCard'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'

function BookmarkCard({ item, onDelete, deleting }) {
  return (
    <div className="relative group">
      <RecipeCard recipe={item.recipe} />
      <button
        type="button"
        onClick={e => { e.preventDefault(); onDelete(item.recipe.id) }}
        disabled={deleting}
        title="Hapus bookmark"
        className="absolute top-3 right-3 z-10 w-8 h-8 rounded-full bg-white border border-gray-200 shadow-card flex items-center justify-center text-gray-500 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus:opacity-100 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {deleting
          ? <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
          : <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
        }
      </button>
    </div>
  )
}

export default function BookmarksPage() {
  const { isLoggedIn }          = useAuth()
  const navigate                = useNavigate()
  const [items, setItems]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [deleting, setDeleting] = useState(null)

  function load() {
    setLoading(true)
    setError('')
    api.get('/bookmarks')
      .then(r => setItems(r.data))
      .catch(() => setError('Gagal memuat bookmark. Periksa koneksi internet kamu.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!isLoggedIn) { navigate('/login', { replace: true }); return }
    load()
  }, [isLoggedIn])

  async function handleDelete(recipeId) {
    setDeleting(recipeId)
    try {
      await api.delete(`/bookmarks/${recipeId}`)
      setItems(prev => prev.filter(bm => bm.recipe.id !== recipeId))
    } catch {
      setError('Gagal menghapus bookmark. Silakan coba lagi.')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <main className="max-w-6xl mx-auto px-5 sm:px-6 py-10">

        <div className="mb-8">
          <p className="text-[11px] font-semibold text-green-700 uppercase tracking-wider mb-1">Koleksi</p>
          <h1 className="font-display text-3xl font-extrabold text-gray-900">Resep Tersimpan</h1>
          <p className="text-sm text-gray-500 mt-1.5">
            {loading ? 'Memuat...' : `${items.length} resep tersimpan`}
          </p>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorMessage message={error} onRetry={load} />
          </div>
        )}

        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-2xl border border-gray-200 shadow-card overflow-hidden animate-pulse">
                <div className="h-40 bg-gray-100" />
                <div className="p-4 space-y-2.5">
                  <div className="h-4 bg-gray-100 rounded w-4/5" />
                  <div className="h-3 bg-gray-100 rounded w-3/5" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <EmptyState
            icon="🔖"
            title="Belum ada resep tersimpan"
            body="Klik ikon bookmark saat membuka resep untuk menyimpannya di sini."
            action={{ label: 'Cari Resep', to: '/' }}
          />
        )}

        {!loading && items.length > 0 && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {items.map(item => (
                <BookmarkCard
                  key={item.recipe.id}
                  item={item}
                  onDelete={handleDelete}
                  deleting={deleting === item.recipe.id}
                />
              ))}
            </div>
            <p className="text-center text-xs text-gray-400 mt-10 hidden sm:block">
              Arahkan kursor ke kartu untuk menampilkan tombol hapus
            </p>
          </>
        )}

      </main>
    </div>
  )
}
