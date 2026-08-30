import { useState, useEffect, useRef } from 'react'

export default function CookingTimer({ defaultMinutes = 5 }) {
  const [inputMin,  setInputMin]  = useState(defaultMinutes)
  const [totalSecs, setTotalSecs] = useState(defaultMinutes * 60)
  const [remaining, setRemaining] = useState(defaultMinutes * 60)
  const [status,    setStatus]    = useState('idle') // idle | running | paused | done
  const intervalRef = useRef(null)

  useEffect(() => () => clearInterval(intervalRef.current), [])

  function start() {
    intervalRef.current = setInterval(() => {
      setRemaining(r => {
        if (r <= 1) { clearInterval(intervalRef.current); setStatus('done'); return 0 }
        return r - 1
      })
    }, 1000)
    setStatus('running')
  }

  function pause() {
    clearInterval(intervalRef.current)
    setStatus('paused')
  }

  function reset() {
    clearInterval(intervalRef.current)
    const s = inputMin * 60
    setTotalSecs(s)
    setRemaining(s)
    setStatus('idle')
  }

  function changeMin(v) {
    const m = Math.max(1, Math.min(60, Number(v) || 1))
    setInputMin(m)
    setTotalSecs(m * 60)
    setRemaining(m * 60)
  }

  const mm  = String(Math.floor(remaining / 60)).padStart(2, '0')
  const ss  = String(remaining % 60).padStart(2, '0')
  const pct = totalSecs > 0 ? Math.round(((totalSecs - remaining) / totalSecs) * 100) : 0

  const isIdle    = status === 'idle'
  const isRunning = status === 'running'
  const isPaused  = status === 'paused'
  const isDone    = status === 'done'

  // Color tone for the active card
  const tone = isDone
    ? 'from-green-50 via-emerald-50 to-green-100 ring-green-200'
    : isRunning
      ? 'from-green-50 to-white ring-green-200'
      : isPaused
        ? 'from-amber-50 to-white ring-amber-200'
        : 'from-gray-50 to-white ring-gray-200'

  return (
    <div className={`mt-4 rounded-2xl bg-gradient-to-br ${tone} ring-1 p-4 transition-colors`}>
      <div className="flex items-center gap-3 flex-wrap">
        <span className="w-9 h-9 rounded-xl bg-white ring-1 ring-gray-200 grid place-items-center text-base shadow-card shrink-0">
          ⏱️
        </span>

        {/* Duration display / edit */}
        {isIdle ? (
          <div className="flex items-baseline gap-1.5">
            <input
              type="number"
              min="1" max="60"
              value={inputMin}
              onChange={e => changeMin(e.target.value)}
              className="w-14 rounded-lg border border-gray-300 px-2 py-1.5 text-sm font-mono text-center font-semibold focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <span className="text-xs text-gray-500 font-medium">menit</span>
          </div>
        ) : (
          <span className={`font-mono text-2xl font-extrabold tracking-widest tabular-nums leading-none ${
            isDone ? 'text-green-700' : isRunning ? 'text-gray-900' : 'text-amber-600'
          }`}>
            {mm}:{ss}
          </span>
        )}

        {isDone && (
          <span className="text-[11px] font-bold bg-green-500 text-white px-2.5 py-1 rounded-full shadow-card">
            ✓ Selesai!
          </span>
        )}

        {/* Control buttons */}
        <div className="ml-auto flex gap-1.5">
          {!isRunning && !isDone && (
            <button
              type="button"
              onClick={start}
              className="flex items-center gap-1 px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-xs font-semibold rounded-lg transition-colors shadow-card"
            >
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path d="M6.3 2.841A1.5 1.5 0 004 4.11v11.78a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
              </svg>
              {isPaused ? 'Lanjut' : 'Mulai'}
            </button>
          )}
          {isRunning && (
            <button
              type="button"
              onClick={pause}
              className="flex items-center gap-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors shadow-card"
            >
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path d="M5.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 007.25 3h-1.5zM12.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 0014.25 3h-1.5z" />
              </svg>
              Jeda
            </button>
          )}
          {!isIdle && (
            <button
              type="button"
              onClick={reset}
              className="px-3 py-1.5 bg-white hover:bg-gray-50 text-gray-600 text-xs font-semibold rounded-lg transition-colors ring-1 ring-gray-200"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {!isIdle && (
        <div className="mt-3 h-2 bg-white/70 rounded-full overflow-hidden ring-1 ring-gray-200/60">
          <div
            className={`h-full rounded-full transition-all duration-1000 ${
              isDone ? 'bg-green-500' : isRunning ? 'bg-green-400' : 'bg-amber-400'
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  )
}
