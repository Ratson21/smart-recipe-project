import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import CookingTimer from '../components/CookingTimer'
import RatingWidget from '../components/RatingWidget'
import RecipeCard from '../components/RecipeCard'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'

function parseIngredients(raw) {
  if (!raw) return []
  return raw.split('--').map(s => s.trim()).filter(Boolean)
}

function parseSteps(text) {
  if (!text) return []
  return text
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)
    .map(s => s.replace(/^\d+[).]\s*/, ''))
}

const DIFFICULTY_STYLE = {
  Mudah:  'bg-green-50  text-green-700  ring-1 ring-green-100',
  Sedang: 'bg-amber-50  text-amber-700  ring-1 ring-amber-100',
  Sulit:  'bg-rose-50   text-rose-700   ring-1 ring-rose-100',
}

function getCategoryStyle(category) {
  const c = (category || '').toLowerCase()
  if (c.includes('ayam') || c.includes('unggas'))      return { emoji: '🍗', gradient: 'from-amber-100  via-orange-50 to-rose-50' }
  if (c.includes('ikan') || c.includes('seafood'))     return { emoji: '🐟', gradient: 'from-sky-100    via-cyan-50   to-blue-50' }
  if (c.includes('daging') || c.includes('sapi'))      return { emoji: '🥩', gradient: 'from-rose-100   via-red-50    to-orange-50' }
  if (c.includes('sayur'))                             return { emoji: '🥬', gradient: 'from-emerald-100 via-green-50 to-lime-50' }
  if (c.includes('tahu')   || c.includes('tempe'))     return { emoji: '🥘', gradient: 'from-yellow-100 via-amber-50  to-orange-50' }
  if (c.includes('telur'))                             return { emoji: '🥚', gradient: 'from-yellow-100 via-lime-50   to-emerald-50' }
  if (c.includes('mie')    || c.includes('pasta'))     return { emoji: '🍜', gradient: 'from-amber-100  via-yellow-50 to-orange-50' }
  if (c.includes('sup')    || c.includes('soto'))      return { emoji: '🍲', gradient: 'from-orange-100 via-amber-50  to-yellow-50' }
  if (c.includes('kue')    || c.includes('dessert'))   return { emoji: '🍰', gradient: 'from-pink-100   via-rose-50   to-fuchsia-50' }
  return { emoji: '🍳', gradient: 'from-gray-100 via-stone-50 to-slate-50' }
}

function MetaItem({ icon, value, label }) {
  if (!value) return null
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-9 h-9 rounded-xl bg-white ring-1 ring-gray-200 grid place-items-center text-base shrink-0">
        {icon}
      </span>
      <div className="leading-tight">
        <p className="text-sm font-semibold text-gray-900">{value}</p>
        <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">{label}</p>
      </div>
    </div>
  )
}

function SectionHeading({ children }) {
  return (
    <h2 className="font-display text-xl font-bold text-gray-900 border-l-4 border-green-500 pl-4 mb-5">
      {children}
    </h2>
  )
}

function PageSkeleton() {
  return (
    <div className="animate-pulse space-y-6 pt-8">
      <div className="h-72 bg-gray-100 rounded-3xl" />
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-3">
          {[...Array(6)].map((_, i) => <div key={i} className="h-4 bg-gray-100 rounded" />)}
        </div>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <div key={i} className="h-16 bg-gray-100 rounded-xl" />)}
        </div>
      </div>
    </div>
  )
}

function DetailHeader({ bookmark, onBack }) {
  return (
    <header className="sticky top-0 z-20 bg-white/85 backdrop-blur-md border-b border-gray-200/70">
      <div className="max-w-6xl mx-auto px-5 sm:px-6 h-16 flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors font-medium"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Kembali
        </button>

        {bookmark}
      </div>
    </header>
  )
}

export default function RecipeDetailPage() {
  const { id }         = useParams()
  const { isLoggedIn } = useAuth()
  const navigate       = useNavigate()

  const [recipe, setRecipe]                     = useState(null)
  const [similar, setSimilar]                   = useState([])
  const [userRating, setUserRating]             = useState(0)
  const [isBookmarked, setIsBookmarked]         = useState(false)
  const [bookmarkLoading, setBookmarkLoading]   = useState(false)

  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')   // network/server error on main fetch
  const [notFound, setNotFound] = useState(false)

  // Go back to the page the user came from; fall back to home when this page
  // was opened directly (shared link, refresh) and has no in-app history.
  function goBack() {
    if (window.history.state?.idx > 0) navigate(-1)
    else navigate('/')
  }

  function buildErrorMessage(err) {
    if (!err.response) return 'Tidak dapat terhubung ke server. Periksa koneksi internet kamu.'
    if (err.response.status === 404) return null
    if (err.response.status >= 500) return 'Server sedang bermasalah. Silakan coba beberapa saat lagi.'
    return 'Gagal memuat resep. Silakan coba lagi.'
  }

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setNotFound(false)
      setError('')

      try {
        const { data } = await api.get(`/recipes/${id}`)
        if (!cancelled) setRecipe(data)
      } catch (err) {
        if (cancelled) return
        if (err.response?.status === 404) setNotFound(true)
        else setError(buildErrorMessage(err))
        setLoading(false)
        return
      }

      const [simRes, rateRes, bmRes] = await Promise.allSettled([
        api.get(`/recommendations/similar/${id}`),
        isLoggedIn ? api.get(`/ratings/recipe/${id}`) : Promise.resolve(null),
        isLoggedIn ? api.get('/bookmarks')             : Promise.resolve(null),
      ])

      if (cancelled) return

      if (simRes.status === 'fulfilled') setSimilar(simRes.value.data ?? [])

      if (rateRes.status === 'fulfilled' && rateRes.value?.data)
        setUserRating(rateRes.value.data.rating_score ?? 0)

      if (bmRes.status === 'fulfilled' && bmRes.value?.data)
        setIsBookmarked(bmRes.value.data.some(bm => bm.recipe.id === id))

      if (!cancelled) setLoading(false)
    }

    load()
    return () => { cancelled = true }
  }, [id, isLoggedIn])

  async function toggleBookmark() {
    if (!isLoggedIn) { navigate('/login'); return }
    setBookmarkLoading(true)
    try {
      if (isBookmarked) {
        await api.delete(`/bookmarks/${id}`)
        setIsBookmarked(false)
      } else {
        await api.post('/bookmarks', { recipe_id: id })
        setIsBookmarked(true)
      }
    } catch {
      // ignore - state stays unchanged
    } finally {
      setBookmarkLoading(false)
    }
  }

  const bookmarkButton = (
    <button
      type="button"
      onClick={toggleBookmark}
      disabled={bookmarkLoading || loading}
      title={isBookmarked ? 'Hapus bookmark' : 'Simpan ke bookmark'}
      className={`flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-xl border transition-all disabled:opacity-50 shadow-card ${
        isBookmarked
          ? 'bg-green-500 border-green-500 text-white hover:bg-green-600'
          : 'bg-white border-gray-200 text-gray-700 hover:border-green-400 hover:text-green-700'
      }`}
    >
      {bookmarkLoading
        ? <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
        : (
          <svg
            className="w-4 h-4"
            fill={isBookmarked ? 'currentColor' : 'none'}
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" />
          </svg>
        )
      }
      <span className="hidden sm:inline">
        {isBookmarked ? 'Tersimpan' : 'Simpan'}
      </span>
    </button>
  )

  // ── 404 ──────────────────────────────────────────────────────────────────

  if (notFound) {
    return (
      <div className="min-h-screen bg-gray-50">
        <DetailHeader onBack={goBack} />
        <EmptyState
          icon="🍳"
          title="Resep tidak ditemukan"
          body="Resep mungkin telah dihapus atau ID tidak valid."
          action={{ label: '← Kembali ke beranda', to: '/' }}
        />
      </div>
    )
  }

  // ── Network / server error ────────────────────────────────────────────────

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <DetailHeader onBack={goBack} />
        <ErrorMessage
          variant="page"
          message={error}
          onRetry={() => { setError(''); setLoading(true); window.location.reload() }}
        />
      </div>
    )
  }

  // ── Main render ───────────────────────────────────────────────────────────

  const ingredients = recipe ? parseIngredients(recipe.ingredients_raw) : []
  const steps       = recipe ? parseSteps(recipe.steps)                  : []
  const diffStyle   = DIFFICULTY_STYLE[recipe?.difficulty_level] ?? 'bg-gray-100 text-gray-500 ring-1 ring-gray-200'
  const cat         = getCategoryStyle(recipe?.category)

  return (
    <div className="min-h-screen bg-gray-50">

      <DetailHeader bookmark={bookmarkButton} onBack={goBack} />

      <main className="max-w-6xl mx-auto px-5 sm:px-6 pb-20">
        {loading && <PageSkeleton />}

        {!loading && recipe && (
          <>
            {/* Hero */}
            <section className="pt-8">
              <div className="grid lg:grid-cols-[2fr_1fr] gap-8 items-start">

                {/* Kiri: judul + meta */}
                <div>
                  {recipe.category && (
                    <span className="inline-block text-[11px] font-semibold text-green-700 bg-green-50 ring-1 ring-green-100 px-2.5 py-1 rounded-full mb-4 uppercase tracking-wider">
                      {recipe.category}
                    </span>
                  )}
                  <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 leading-[1.1] mb-6">
                    {recipe.title}
                  </h1>

                  <div className="flex flex-wrap gap-x-6 gap-y-4">
                    <MetaItem icon="⏱️" value={recipe.estimated_time_minutes > 0 ? `${recipe.estimated_time_minutes} mnt` : null} label="Waktu" />
                    <MetaItem icon="🥘" value={recipe.total_ingredients > 0 ? `${recipe.total_ingredients}` : null} label="Bahan" />
                    <MetaItem icon="📋" value={recipe.total_steps > 0 ? `${recipe.total_steps}` : null} label="Langkah" />
                    {recipe.difficulty_level && (
                      <div className="flex items-center gap-2.5">
                        <span className="w-9 h-9 rounded-xl bg-white ring-1 ring-gray-200 grid place-items-center text-base shrink-0">
                          🎯
                        </span>
                        <div className="leading-tight">
                          <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-semibold ${diffStyle}`}>
                            {recipe.difficulty_level}
                          </span>
                          <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium mt-0.5">Kesulitan</p>
                        </div>
                      </div>
                    )}
                    {recipe.total_reviews > 0 && (
                      <div className="flex items-center gap-2.5">
                        <span className="w-9 h-9 rounded-xl bg-white ring-1 ring-gray-200 grid place-items-center text-base shrink-0">⭐</span>
                        <div className="leading-tight">
                          <p className="text-sm font-semibold text-gray-900">
                            {recipe.average_rating.toFixed(1)} <span className="text-gray-400 font-normal">({recipe.total_reviews})</span>
                          </p>
                          <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Rating</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Kanan: emoji thumbnail */}
                <div className={`hidden lg:flex items-center justify-center aspect-square max-w-xs w-full rounded-2xl bg-gradient-to-br ${cat.gradient} border border-gray-200`}>
                  <span className="text-8xl opacity-90 select-none">{cat.emoji}</span>
                </div>

              </div>
            </section>

            {/* Main content grid */}
            <div className="mt-10 grid lg:grid-cols-3 gap-10">

              {/* LEFT: ingredients + steps */}
              <div className="lg:col-span-2 space-y-12">
                <section>
                  <SectionHeading>Bahan-bahan</SectionHeading>
                  {ingredients.length === 0 ? (
                    <p className="text-sm text-gray-400">Data bahan tidak tersedia.</p>
                  ) : (
                    <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-2.5">
                      {ingredients.map((ing, i) => (
                        <li key={i} className="flex items-start gap-3 text-sm text-gray-800 leading-relaxed">
                          <span className="mt-2 w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
                          {ing}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <section>
                  <SectionHeading>Cara Memasak</SectionHeading>
                  {steps.length === 0 ? (
                    <p className="text-sm text-gray-400">Langkah memasak tidak tersedia.</p>
                  ) : (
                    <ol className="space-y-8">
                      {steps.map((step, i) => (
                        <li key={i} className="relative">
                          <div className="flex gap-4">
                            <div className="flex flex-col items-center shrink-0">
                              <span className="w-9 h-9 rounded-full bg-green-500 text-white text-sm font-bold grid place-items-center shadow-card">
                                {i + 1}
                              </span>
                              {i !== steps.length - 1 && (
                                <span className="w-px flex-1 bg-gray-200 mt-2" />
                              )}
                            </div>
                            <div className="flex-1 pb-2">
                              <p className="text-[15px] text-gray-800 leading-relaxed">{step}</p>
                              <CookingTimer defaultMinutes={5} />
                            </div>
                          </div>
                        </li>
                      ))}
                    </ol>
                  )}
                </section>
              </div>

              {/* RIGHT: rating */}
              <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
                <section className="bg-white rounded-2xl border border-gray-200 shadow-card p-5 sm:p-6">
                  <SectionHeading>Beri Rating</SectionHeading>
                  {isLoggedIn
                    ? <RatingWidget recipeId={id} initialRating={userRating} />
                    : (
                      <div className="text-center py-2">
                        <p className="text-sm text-gray-500 mb-4">
                          Login untuk memberi rating resep ini
                        </p>
                        <Link
                          to="/login"
                          className="inline-block text-sm font-semibold bg-green-500 hover:bg-green-600 text-white px-5 py-2.5 rounded-xl shadow-card transition-colors"
                        >
                          Masuk
                        </Link>
                      </div>
                    )
                  }
                </section>
              </div>
            </div>

            {/* Similar Recipes */}
            {similar.length > 0 && (
              <section className="mt-16 pt-12 border-t border-gray-100">
                <SectionHeading>Resep Serupa</SectionHeading>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  {similar.map(r => (
                    <RecipeCard
                      key={r.recipe.id}
                      recipe={r.recipe}
                      matchPercentage={r.match_percentage}
                    />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  )
}
