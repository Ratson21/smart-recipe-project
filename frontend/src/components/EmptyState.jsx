import { Link } from 'react-router-dom'

/**
 * icon      - emoji or single character
 * title     - bold heading
 * body      - supporting text
 * action    - { label, to } for a Link, or { label, onClick } for a button
 */
export default function EmptyState({ icon = '📭', title, body, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-24 px-4 gap-5">
      <div className="w-20 h-20 rounded-3xl bg-gray-50 ring-1 ring-gray-100 grid place-items-center text-4xl select-none">
        {icon}
      </div>
      <div className="space-y-1.5 max-w-sm">
        {title && <p className="font-display font-bold text-gray-900 text-lg">{title}</p>}
        {body  && <p className="text-sm text-gray-500 leading-relaxed">{body}</p>}
      </div>
      {action && (
        action.to ? (
          <Link
            to={action.to}
            className="inline-flex items-center gap-1.5 text-sm font-semibold bg-green-500 hover:bg-green-600 text-white px-5 py-2.5 rounded-xl shadow-card transition-colors"
          >
            {action.label}
          </Link>
        ) : (
          <button
            type="button"
            onClick={action.onClick}
            className="inline-flex items-center gap-1.5 text-sm font-semibold bg-green-500 hover:bg-green-600 text-white px-5 py-2.5 rounded-xl shadow-card transition-colors"
          >
            {action.label}
          </button>
        )
      )}
    </div>
  )
}
