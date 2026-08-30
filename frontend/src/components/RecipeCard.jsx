import { Link } from 'react-router-dom'
import MatchScoreBar from './MatchScoreBar'

function getCategoryStyle(category) {
  const c = (category || '').toLowerCase()
  if (c.includes('ayam') || c.includes('unggas'))
    return { emoji: '🍗', gradient: 'from-amber-100 via-orange-50 to-red-50' }
  if (c.includes('seafood') || c.includes('ikan') || c.includes('laut'))
    return { emoji: '🐟', gradient: 'from-sky-100 via-cyan-50 to-blue-50' }
  if (c.includes('daging') || c.includes('sapi') || c.includes('kambing'))
    return { emoji: '🥩', gradient: 'from-rose-100 via-red-50 to-orange-50' }
  if (c.includes('sayur'))
    return { emoji: '🥬', gradient: 'from-emerald-100 via-green-50 to-lime-50' }
  if (c.includes('tahu') || c.includes('tempe'))
    return { emoji: '🥘', gradient: 'from-yellow-100 via-amber-50 to-orange-50' }
  if (c.includes('telur'))
    return { emoji: '🥚', gradient: 'from-yellow-100 via-lime-50 to-emerald-50' }
  if (c.includes('nasi') || c.includes('rice'))
    return { emoji: '🍚', gradient: 'from-stone-100 via-gray-50 to-slate-50' }
  if (c.includes('mie') || c.includes('pasta') || c.includes('mi'))
    return { emoji: '🍜', gradient: 'from-amber-100 via-yellow-50 to-orange-50' }
  if (c.includes('sup') || c.includes('soto') || c.includes('soup'))
    return { emoji: '🍲', gradient: 'from-orange-100 via-amber-50 to-yellow-50' }
  if (c.includes('kue') || c.includes('dessert') || c.includes('cake'))
    return { emoji: '🍰', gradient: 'from-pink-100 via-rose-50 to-fuchsia-50' }
  return { emoji: '🍳', gradient: 'from-gray-100 via-stone-50 to-slate-50' }
}

const DIFFICULTY_STYLE = {
  Mudah:  'bg-green-50  text-green-700',
  Sedang: 'bg-amber-50  text-amber-700',
  Sulit:  'bg-rose-50   text-rose-700',
}

function ClockIcon() {
  return (
    <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
    </svg>
  )
}
export default function RecipeCard({ recipe, matchPercentage }) {
  const { emoji, gradient } = getCategoryStyle(recipe.category)
  const diffStyle = DIFFICULTY_STYLE[recipe.difficulty_level] ?? 'bg-gray-100 text-gray-500'

  return (
    <Link
      to={`/recipe/${recipe.id}`}
      className="group flex flex-row bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden hover:shadow-card-hover hover:border-gray-300 transition-all duration-200"
    >
      {/* Thumbnail */}
      <div className={`relative shrink-0 w-20 h-20 self-center m-3 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center overflow-hidden`}>
        <span className="text-3xl opacity-90 select-none group-hover:scale-110 transition-transform duration-300">
          {emoji}
        </span>
      </div>

      {/* Body */}
      <div className="flex flex-col flex-1 px-3 py-3 gap-1 min-w-0 justify-center">
        <h3 className="font-display text-[14px] font-bold text-gray-900 leading-snug line-clamp-2 group-hover:text-green-600 transition-colors">
          {recipe.title}
        </h3>

        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 mt-0.5">
          {recipe.estimated_time_minutes > 0 && (
            <span className="flex items-center gap-1 text-[11px] text-gray-500 shrink-0">
              <ClockIcon />
              {recipe.estimated_time_minutes} mnt
            </span>
          )}
          {recipe.difficulty_level && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold shrink-0 ${diffStyle}`}>
              {recipe.difficulty_level}
            </span>
          )}
        </div>

        {matchPercentage != null && (
          <div className="mt-1">
            <MatchScoreBar percentage={matchPercentage} />
          </div>
        )}
      </div>
    </Link>
  )
}
