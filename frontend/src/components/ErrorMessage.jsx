/**
 * variants: 'inline' (default) | 'page'
 * 'page'   - centered in a full-height area with a retry button
 * 'inline' - banner inside a section
 */
export default function ErrorMessage({
  message = 'Terjadi kesalahan. Silakan coba lagi.',
  onRetry,
  variant = 'inline',
}) {
  if (variant === 'page') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 gap-5">
        <div className="w-16 h-16 rounded-3xl bg-rose-50 ring-1 ring-rose-100 grid place-items-center text-3xl">
          ⚠️
        </div>
        <div className="space-y-1.5 max-w-sm">
          <p className="font-display font-bold text-gray-900 text-lg">Gagal memuat data</p>
          <p className="text-sm text-gray-500 leading-relaxed">{message}</p>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="text-sm font-semibold bg-gray-900 hover:bg-gray-800 text-white px-5 py-2.5 rounded-xl transition-colors shadow-card"
          >
            Coba Lagi
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl px-4 py-3">
      <svg className="mt-0.5 shrink-0 w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
          clipRule="evenodd"
        />
      </svg>
      <div className="flex-1">
        <span>{message}</span>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="ml-3 underline text-rose-700 hover:text-rose-800 font-semibold"
          >
            Coba lagi
          </button>
        )}
      </div>
    </div>
  )
}
