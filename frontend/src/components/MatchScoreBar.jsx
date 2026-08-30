/**
 * Match-score visual.
 *
 * variant="pill" (default) - compact pill badge, designed to float over
 *                            a card image at top-right.
 * variant="bar"             - slim progress bar with label, used inline
 *                            inside content (kept for backwards-compat).
 */
export default function MatchScoreBar({ percentage, variant = 'pill' }) {
  const pct = Math.max(0, Math.min(100, Math.round(percentage)))

  if (variant === 'bar') {
    const barColor =
      pct >= 75 ? 'bg-sage-500' :
      pct >= 50 ? 'bg-amber-400' :
                  'bg-orange-400'
    const textColor =
      pct >= 75 ? 'text-sage-700' :
      pct >= 50 ? 'text-amber-600' :
                  'text-orange-500'

    return (
      <div>
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-gray-400">Kesesuaian</span>
          <span className={`text-xs font-semibold ${textColor}`}>{pct}%</span>
        </div>
        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    )
  }

  // Pill (default)
  const tone =
    pct >= 75 ? 'bg-sage-500 text-white'
    : pct >= 50 ? 'bg-white text-sage-700 border border-sage-200'
    :             'bg-white text-gray-600 border border-gray-200'

  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-full shadow-card ${tone}`}
      aria-label={`Kecocokan ${pct} persen`}
    >
      <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
      {pct}% cocok
    </span>
  )
}
