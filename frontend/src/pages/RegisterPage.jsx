import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'

function BrandBadge() {
  return (
    <div className="mb-5">
      <span className="font-display text-2xl font-bold text-gray-900">Smart Recipe</span>
    </div>
  )
}

export default function RegisterPage() {
  const auth = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' })
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (form.password.length < 6) {
      setError('Password minimal 6 karakter.')
      return
    }
    if (form.password !== form.confirm) {
      setError('Password dan konfirmasi password tidak cocok.')
      return
    }

    setLoading(true)
    let registered = false
    try {
      await api.post('/auth/register', {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
      })
      registered = true
      // Auto-login setelah register berhasil
      const { data } = await api.post('/auth/login', {
        email: form.email,
        password: form.password,
      })
      auth.login(data.access_token, data.user)
      navigate('/')
    } catch (err) {
      if (registered) {
        // Registrasi berhasil tapi login gagal - arahkan ke halaman login
        navigate('/login')
        return
      }
      const msg = err.response?.data?.detail
      setError(Array.isArray(msg) ? msg[0]?.msg : (msg ?? 'Terjadi kesalahan, coba lagi.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-6 font-medium transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Beranda
        </Link>

        <div className="bg-white rounded-3xl shadow-card-hover border border-gray-200 p-8 sm:p-10">

          {/* Brand */}
          <div className="text-center mb-8">
            <BrandBadge />
            <h1 className="font-display text-2xl font-extrabold text-gray-900 leading-tight">
              Buat akun gratis
            </h1>
            <p className="mt-1.5 text-sm text-gray-500">
              Mulai dapatkan rekomendasi resep yang sesuai seleramu
            </p>
          </div>

          {/* Error banner */}
          {error && (
            <div className="mb-5 flex items-start gap-2.5 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl px-4 py-3">
              <svg className="mt-0.5 shrink-0 w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="full_name" className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Nama Lengkap
              </label>
              <input
                id="full_name"
                type="text"
                name="full_name"
                value={form.full_name}
                onChange={handleChange}
                required
                autoComplete="name"
                placeholder="Nama lengkap kamu"
                className="w-full rounded-xl border border-gray-200 bg-gray-50/60 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-green-500 focus:border-transparent transition"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                required
                autoComplete="email"
                placeholder="nama@email.com"
                className="w-full rounded-xl border border-gray-200 bg-gray-50/60 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-green-500 focus:border-transparent transition"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                required
                autoComplete="new-password"
                placeholder="Minimal 6 karakter"
                className="w-full rounded-xl border border-gray-200 bg-gray-50/60 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-green-500 focus:border-transparent transition"
              />
            </div>

            <div>
              <label htmlFor="confirm" className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Konfirmasi Password
              </label>
              <input
                id="confirm"
                type="password"
                name="confirm"
                value={form.confirm}
                onChange={handleChange}
                required
                autoComplete="new-password"
                placeholder="Ulangi password kamu"
                className={[
                  'w-full rounded-xl border bg-gray-50/60 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-2 focus:border-transparent transition',
                  form.confirm && form.confirm !== form.password
                    ? 'border-rose-300 focus:ring-rose-400'
                    : 'border-gray-200 focus:ring-green-500',
                ].join(' ')}
              />
              {form.confirm && form.confirm !== form.password && (
                <p className="mt-1.5 text-xs text-rose-600 font-medium">Password tidak cocok</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-500 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-card mt-2"
            >
              {loading && (
                <svg className="animate-spin h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
              )}
              {loading ? 'Mendaftar...' : 'Buat Akun'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            Sudah punya akun?{' '}
            <Link to="/login" className="font-semibold text-green-700 hover:text-green-800">
              Masuk di sini »
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
