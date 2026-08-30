import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../api/axios'
import Navbar from '../components/Navbar'
import RecipeCard from '../components/RecipeCard'
import ErrorMessage from '../components/ErrorMessage'
import EmptyState from '../components/EmptyState'

const SUGGESTIONS = [
  'ayam, bawang putih, tomat',
  'ikan, kunyit, cabai',
  'tahu, tempe, bayam',
  'udang, bawang putih, jahe',
  'daging, kentang, wortel',
  'telur, bawang merah, tomat',
]

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden animate-pulse flex flex-row">
      <div className="w-20 h-20 m-3 rounded-xl bg-gray-100 shrink-0" />
      <div className="flex-1 px-3 py-4 space-y-2">
        <div className="h-3.5 bg-gray-100 rounded w-4/5" />
        <div className="h-3 bg-gray-100 rounded w-3/5" />
        <div className="flex gap-2 pt-1">
          <div className="h-2.5 bg-gray-100 rounded w-12" />
          <div className="h-2.5 bg-gray-100 rounded w-14" />
        </div>
      </div>
    </div>
  )
}

function FilterPanel({ filters, onChange }) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-5 sm:p-6 space-y-5 shadow-card">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">

        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Tingkat Kesulitan
          </label>
          <select
            value={filters.difficulty}
            onChange={e => onChange('difficulty', e.target.value)}
            className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent font-medium"
          >
            <option value="">Semua</option>
            <option value="Mudah">Mudah</option>
            <option value="Sedang">Sedang</option>
            <option value="Sulit">Sulit</option>
          </select>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
              Waktu Masak
            </label>
            {filters.enableMaxTime && (
              <span className="text-xs font-semibold text-green-700">≤ {filters.maxTime} mnt</span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="chk-time"
              checked={filters.enableMaxTime}
              onChange={e => onChange('enableMaxTime', e.target.checked)}
              className="h-4 w-4 rounded accent-green-500 cursor-pointer"
            />
            <input
              type="range"
              min={15} max={120} step={15}
              value={filters.maxTime}
              disabled={!filters.enableMaxTime}
              onChange={e => onChange('maxTime', Number(e.target.value))}
              className="flex-1 accent-green-500 disabled:opacity-40"
            />
          </div>
          <div className="flex justify-between text-[11px] text-gray-400 mt-1 px-7">
            <span>15 mnt</span><span>120 mnt</span>
          </div>
        </div>
      </div>

      {(filters.difficulty || filters.enableMaxTime) && (
        <button
          type="button"
          onClick={() => onChange('__reset__', null)}
          className="text-xs text-rose-600 hover:text-rose-700 font-semibold"
        >
          ↻ Reset semua filter
        </button>
      )}
    </div>
  )
}

const DEFAULT_FILTERS = {
  difficulty: '',
  maxTime: 60,
  enableMaxTime: false,
}

export default function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  // Seed the query from the URL (?q=...) so a search survives navigating to a
  // recipe and back: the search lives in the URL, not just component state.
  const [query, setQuery]             = useState(() => searchParams.get('q') ?? '')
  const [filters, setFilters]         = useState(DEFAULT_FILTERS)
  const [showFilters, setShowFilters] = useState(false)
  const [results, setResults]         = useState([])
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [meta, setMeta]               = useState({ total: 0, isPersonalized: false, queryProcessed: '', ignored: [] })
  // Tracks the query we last fetched, so syncing from the URL doesn't fire a
  // duplicate request right after a manual search already set ?q=...
  const lastRun = useRef(null)

  function handleFilterChange(key, value) {
    if (key === '__reset__') setFilters(DEFAULT_FILTERS)
    else setFilters(prev => ({ ...prev, [key]: value }))
  }

  async function runSearch(searchQuery) {
    if (!searchQuery.trim()) return
    lastRun.current = searchQuery.trim()
    // Reflect the query in the URL (replace, so repeated searches don't
    // stack history entries) - this is what lets "back" restore results.
    setSearchParams({ q: searchQuery.trim() }, { replace: true })
    setLoading(true)
    setError('')
    setHasSearched(true)

    const body = { query: searchQuery.trim(), filters: {}, top_n: 20 }
    if (filters.difficulty)        body.filters.difficulty   = filters.difficulty
    if (filters.enableMaxTime)     body.filters.max_time     = filters.maxTime

    try {
      const { data } = await api.post('/recommendations/smart-search', body)
      setResults(data.results)
      setMeta({ total: data.total, isPersonalized: data.is_personalized, queryProcessed: data.query_processed, ignored: data.ignored_ingredients ?? [] })
    } catch (err) {
      const status = err.response?.status
      if (status === 503 || status === 500) {
        setError('Server AI sedang tidak tersedia. Pastikan backend berjalan.')
      } else if (!err.response) {
        setError('Tidak dapat terhubung ke server. Periksa koneksi internet kamu.')
      } else {
        setError('Gagal mengambil rekomendasi. Silakan coba lagi.')
      }
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  // Keep the view in sync with the URL query param. This handles three cases:
  //  - returning from a recipe detail page with ?q=... -> re-run the search
  //  - clicking the "Smart Recipe" wordmark (-> "/", no ?q) -> reset to the home
  //    hero view, even though HomePage stays mounted
  //  - first mount with a seeded ?q=...
  useEffect(() => {
    const q = searchParams.get('q')?.trim() ?? ''
    if (!q) {
      // No query in the URL: back to the pre-search home screen.
      lastRun.current = null
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setHasSearched(false)
      setResults([])
      setError('')
      setQuery('')
      return
    }
    // Only fetch when the URL query differs from what we already searched,
    // so a manual search (which sets ?q=...) doesn't trigger a second request.
    if (q !== lastRun.current) {
      setQuery(q)
      runSearch(q)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  function handleSubmit(e) {
    e.preventDefault()
    runSearch(query)
  }

  function handleSuggestion(s) {
    setQuery(s)
    runSearch(s)
  }

  // render helper - call as {renderSearchInput()}, NOT as <RenderSearchInput />
  function renderSearchInput() {
    return (
      <form onSubmit={handleSubmit}>
        <div className="relative flex items-center bg-white rounded-xl border border-gray-200 shadow-card focus-within:ring-2 focus-within:ring-green-500 focus-within:border-transparent transition-shadow hover:shadow-card-hover">
          <span className="pl-4 text-gray-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" />
            </svg>
          </span>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="ayam, bawang putih, tomat..."
            className="flex-1 bg-transparent px-3 py-4 text-base text-gray-900 placeholder-gray-400 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="shrink-0 m-1.5 bg-green-500 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-4 py-2.5 rounded-lg shadow-card transition-colors flex items-center gap-2"
          >
            {loading
              ? <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
              : <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
            }
            <span className="hidden sm:inline text-sm">{loading ? 'Mencari...' : 'Cari'}</span>
          </button>
        </div>

        <div className="flex items-center justify-between mt-2.5 px-1">
          <p className="text-xs text-gray-400">Pisahkan bahan dengan koma</p>
          <button
            type="button"
            onClick={() => setShowFilters(v => !v)}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 font-semibold transition-colors"
          >
            <svg className={`w-3.5 h-3.5 transition-transform ${showFilters ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 6h18M6 12h12M10 18h4" />
            </svg>
            {showFilters ? 'Sembunyikan' : 'Filter'}
          </button>
        </div>
      </form>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-6xl mx-auto px-5 sm:px-6 pb-20">

        {/* PRE-SEARCH: split hero layout */}
        {!hasSearched && (
          <section
            className="pt-12 sm:pt-20 pb-14"
            style={{
              backgroundImage: 'radial-gradient(circle, #DCE3E1 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          >
            <div className="grid lg:grid-cols-[55fr_45fr] gap-10 items-start">

              {/* Kiri: headline */}
              <div className="pt-2 lg:pt-6">
                <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-green-700 bg-green-50 ring-1 ring-green-100 px-3 py-1.5 rounded-full mb-6">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  14.945 Resep Indonesia
                </div>
                <h1 className="font-display text-5xl sm:text-6xl font-bold text-gray-900 leading-[1.05] mb-5">
                  Masak apa<br />hari ini,<br />
                  <span className="text-green-600">dari isi kulkas?</span>
                </h1>
                <p className="text-gray-500 text-base sm:text-lg leading-relaxed max-w-md">
                  Ketik bahan yang kamu punya - AI menemukan resep masakan Indonesia paling cocok, dipersonalisasi berdasarkan seleramu.
                </p>
              </div>

              {/* Kanan: search card */}
              <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-card-hover">
                {renderSearchInput()}

                {/* Filter (desktop inline) */}
                {showFilters && (
                  <div className="mt-4">
                    <FilterPanel filters={filters} onChange={handleFilterChange} />
                  </div>
                )}

                {/* Suggestions */}
                <div className="mt-5 pt-5 border-t border-gray-100">
                  <p className="text-[11px] text-gray-400 mb-3 uppercase tracking-wider font-semibold">
                    Coba pencarian populer
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTIONS.map(s => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => handleSuggestion(s)}
                        className="text-xs bg-gray-50 border border-gray-200 hover:border-green-400 hover:text-green-700 hover:bg-green-50/50 text-gray-700 px-3 py-1.5 rounded-full transition-all font-medium"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* POST-SEARCH: standalone search bar */}
        {hasSearched && (
          <div className="pt-8 max-w-2xl">
            {renderSearchInput()}

            {/* Desktop filter */}
            {showFilters && (
              <div className="hidden sm:block mt-3">
                <FilterPanel filters={filters} onChange={handleFilterChange} />
              </div>
            )}
          </div>
        )}

        {/* Mobile filter drawer */}
        {showFilters && hasSearched && (
          <div className="sm:hidden">
            <div
              className="fixed inset-0 z-40 bg-black/40"
              onClick={() => setShowFilters(false)}
            />
            <div
              className="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-3xl shadow-pop"
              style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 4rem)' }}
            >
              <div className="flex items-center justify-between px-5 pt-5 pb-3 relative">
                <span className="absolute top-2 left-1/2 -translate-x-1/2 w-12 h-1.5 rounded-full bg-gray-200" />
                <h3 className="font-display text-base font-bold text-gray-900">Filter Resep</h3>
                <button
                  type="button"
                  onClick={() => setShowFilters(false)}
                  className="p-1 text-gray-400 hover:text-gray-700"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="px-5 pb-4">
                <FilterPanel filters={filters} onChange={handleFilterChange} />
              </div>
            </div>
          </div>
        )}

        {/* Feature highlights (pre-search) */}
        {!hasSearched && (
          <section className="mt-6 max-w-5xl mx-auto grid sm:grid-cols-2 gap-4">
            {[
              {
                icon: '🧠',
                title: 'Semantic AI',
                body: 'Sentence Transformer memahami makna bahan, bukan sekadar mencocokkan kata.',
              },
              {
                icon: '✨',
                title: 'Dipersonalisasi',
                body: 'Rekomendasi makin akurat seiring kamu memberi rating dan menyimpan resep.',
              },
            ].map(f => (
              <div key={f.title} className="bg-white rounded-2xl border border-gray-200 shadow-card p-5">
                <div className="w-10 h-10 rounded-xl bg-green-50 ring-1 ring-green-100 grid place-items-center text-xl mb-3">
                  {f.icon}
                </div>
                <p className="font-display font-bold text-gray-900 text-[15px] mb-1">{f.title}</p>
                <p className="text-sm text-gray-500 leading-relaxed">{f.body}</p>
              </div>
            ))}
          </section>
        )}

        {/* Results */}
        {hasSearched && (
          <div className="mt-6">
            {!loading && !error && (
              <div className="flex items-center flex-wrap gap-2 mb-5">
                <p className="text-sm text-gray-600">
                  <span className="font-display font-bold text-gray-900 text-base">{meta.total}</span>
                  <span className="ml-1.5">resep ditemukan</span>
                  {meta.queryProcessed && (
                    <span className="text-gray-400"> untuk &ldquo;{meta.queryProcessed}&rdquo;</span>
                  )}
                </p>
                {meta.isPersonalized && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold bg-purple-50 text-purple-700 ring-1 ring-purple-100 px-2.5 py-1 rounded-full">
                    ✨ Personalized
                  </span>
                )}
              </div>
            )}

            {!loading && !error && meta.ignored.length > 0 && (
              <div className="flex items-start gap-2.5 text-sm bg-amber-50 text-amber-800 ring-1 ring-amber-100 rounded-xl px-4 py-3 mb-5">
                <span className="shrink-0 mt-0.5">ℹ️</span>
                <p>
                  Bahan{' '}
                  <span className="font-semibold">{meta.ignored.join(', ')}</span>{' '}
                  tidak ada di koleksi resep kami, jadi {meta.ignored.length > 1 ? 'mereka' : 'bahan ini'} diabaikan
                  {meta.total > 0 ? ' saat mencari.' : '.'}
                </p>
              </div>
            )}

            {error && (
              <ErrorMessage
                message={error}
                onRetry={() => runSearch(query)}
              />
            )}

            {loading && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
              </div>
            )}

            {!loading && !error && results.length === 0 && meta.ignored.length > 0 && (
              <EmptyState
                icon="🥘"
                title="Bahan tidak ada di koleksi resep"
                body="Koleksi kami berisi resep masakan Indonesia, jadi bahan yang kamu masukkan belum tersedia. Coba bahan lain seperti ayam, tahu, atau ikan."
              />
            )}

            {!loading && !error && results.length === 0 && meta.ignored.length === 0 && (
              <EmptyState
                icon="🔍"
                title="Tidak ada resep yang cocok"
                body="Coba kurangi filter atau gunakan bahan yang berbeda."
                action={{ label: 'Reset Filter', onClick: () => setFilters(DEFAULT_FILTERS) }}
              />
            )}

            {!loading && !error && results.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {results.map(r => (
                  <RecipeCard
                    key={r.recipe.id}
                    recipe={r.recipe}
                    matchPercentage={r.match_percentage}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
