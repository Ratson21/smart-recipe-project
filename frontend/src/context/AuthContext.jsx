import { createContext, useContext, useEffect, useState } from 'react'

const AuthContext = createContext(null)

/** True hanya jika token ada dan klaim `exp`-nya belum lewat. */
function isTokenValid(token) {
  if (!token) return false
  try {
    const { exp } = JSON.parse(atob(token.split('.')[1]))
    return typeof exp === 'number' && exp * 1000 > Date.now()
  } catch {
    return false
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => {
    const stored = localStorage.getItem('token')
    if (isTokenValid(stored)) return stored
    // Token basi/expired tertinggal di storage - bersihkan supaya UI konsisten logout.
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    return null
  })
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('user')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })

  // axios memancarkan event ini saat request mana pun balik 401 (token expired/invalid).
  useEffect(() => {
    function handleExpired() {
      setToken(null)
      setUser(null)
    }
    window.addEventListener('auth:expired', handleExpired)
    return () => window.removeEventListener('auth:expired', handleExpired)
  }, [])

  function login(newToken, userData) {
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(userData))
    setToken(newToken)
    setUser(userData)
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, isLoggedIn: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
