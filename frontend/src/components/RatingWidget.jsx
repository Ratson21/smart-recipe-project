import { useState } from 'react'
import api from '../api/axios'

const LABELS = ['', 'Tidak bagus', 'Kurang bagus', 'Cukup', 'Bagus', 'Sangat bagus']

export default function RatingWidget({ recipeId, initialRating = 0 }) {
  const [selected, setSelected]     = useState(initialRating)
  const [hovered, setHovered]       = useState(0)
  const [saving, setSaving]         = useState(false)
  const [savedScore, setSavedScore] = useState(initialRating)
  const [error, setError]           = useState('')

  const display = hovered || selected

  async function handleSubmit() {
    if (!selected) return
    setSaving(true)
    setError('')
    try {
      await api.post('/ratings', { recipe_id: recipeId, rating_score: selected })
      setSavedScore(selected)
    } catch (err) {
      setError(
        err.response?.status === 401
          ? 'Sesi kamu berakhir. Silakan masuk lagi.'
          : 'Gagal menyimpan rating.'
      )
    } finally {
      setSaving(false)
    }
  }

  const isDirty = selected !== savedScore

  return (
    <div className="space-y-3">
      {/* Stars */}
      <div className="flex gap-1.5" onMouseLeave={() => setHovered(0)}>
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            type="button"
            onMouseEnter={() => setHovered(star)}
            onClick={() => setSelected(star)}
            aria-label={`Beri ${star} bintang`}
            className={`text-3xl leading-none transition-all duration-150 hover:scale-110 active:scale-95 ${
              star <= display ? 'text-amber-400' : 'text-gray-200'
            }`}
          >
            ★
          </button>
        ))}
      </div>

      {/* Label for hovered / selected */}
      <p className="text-xs text-gray-500 h-4">
        {display > 0 ? LABELS[display] : 'Pilih bintang untuk memberi nilai'}
      </p>

      {/* Submit button */}
      {selected > 0 && (
        <button
          type="button"
          onClick={handleSubmit}
          disabled={saving || !isDirty}
          className="w-full py-2.5 text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-green-500 hover:bg-green-600 text-white shadow-card"
        >
          {saving
            ? 'Menyimpan...'
            : !isDirty
              ? `✓ Tersimpan (${savedScore}★)`
              : 'Simpan Rating'}
        </button>
      )}

      {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}
    </div>
  )
}
