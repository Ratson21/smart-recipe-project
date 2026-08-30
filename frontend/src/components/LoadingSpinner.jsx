/**
 * sizes: 'sm' | 'md' (default) | 'lg' | 'page'
 * 'page' centers itself vertically in a full-height container
 */
export default function LoadingSpinner({ size = 'md', label = 'Memuat...' }) {
  const ring = {
    sm:   'w-5  h-5  border-2',
    md:   'w-8  h-8  border-2',
    lg:   'w-12 h-12 border-[3px]',
    page: 'w-12 h-12 border-[3px]',
  }[size] ?? 'w-8 h-8 border-2'

  const spinner = (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`${ring} rounded-full border-gray-200 border-t-green-500 animate-spin`}
        role="status"
        aria-label={label}
      />
      {size !== 'sm' && (
        <p className="text-sm text-gray-400 font-medium">{label}</p>
      )}
    </div>
  )

  if (size === 'page') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        {spinner}
      </div>
    )
  }

  return spinner
}
