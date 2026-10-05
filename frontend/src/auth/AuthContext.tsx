import { createContext, useCallback, useContext, useEffect, useState, type PropsWithChildren } from 'react'
import { api } from '../services/api'
import type { ApiSuccess, User } from '../types'

interface AuthValue { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; register: (payload: Record<string, string>) => Promise<void>; logout: () => void }
const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const logout = useCallback(() => { localStorage.removeItem('finchat_token'); setUser(null) }, [])
  const loadUser = useCallback(async () => {
    if (!localStorage.getItem('finchat_token')) { setLoading(false); return }
    try { setUser((await api.get<ApiSuccess<User>>('/auth/me')).data.data) } catch { logout() } finally { setLoading(false) }
  }, [logout])
  useEffect(() => { void loadUser(); window.addEventListener('finchat:unauthorized', logout); return () => window.removeEventListener('finchat:unauthorized', logout) }, [loadUser, logout])
  const login = async (email: string, password: string) => {
    const response = await api.post<ApiSuccess<{ access_token: string }>>('/auth/login', { email, password })
    localStorage.setItem('finchat_token', response.data.data.access_token)
    setUser((await api.get<ApiSuccess<User>>('/auth/me')).data.data)
  }
  const register = async (payload: Record<string, string>) => { await api.post('/auth/register', payload); await login(payload.email, payload.password) }
  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('AuthProvider ausente'); return value }
