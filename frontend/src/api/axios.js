import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = err.config?.url ?? ''
    // 401 pada request biasa = token hilang / kedaluwarsa / tidak valid.
    // Endpoint /auth/* punya 401-nya sendiri (mis. password salah) - jangan dibajak.
    if (err.response?.status === 401 && !url.startsWith('/auth/')) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.dispatchEvent(new Event('auth:expired'))
    }
    return Promise.reject(err)
  },
)

export default api
