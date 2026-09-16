import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { login as apiLogin, getMe, type MeResponse } from '../api/auth'

interface AuthState {
  user: MeResponse | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  hasRole: (role: string) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  })

  // Restore session on mount
  useEffect(() => {
    const token = sessionStorage.getItem('access_token')
    if (!token) {
      setState({ user: null, isAuthenticated: false, isLoading: false })
      return
    }
    getMe()
      .then((user) => setState({ user, isAuthenticated: true, isLoading: false }))
      .catch(() => {
        sessionStorage.clear()
        setState({ user: null, isAuthenticated: false, isLoading: false })
      })
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password)
    sessionStorage.setItem('access_token', tokens.access_token)
    sessionStorage.setItem('refresh_token', tokens.refresh_token)
    const user = await getMe()
    setState({ user, isAuthenticated: true, isLoading: false })
  }, [])

  const logout = useCallback(() => {
    sessionStorage.clear()
    setState({ user: null, isAuthenticated: false, isLoading: false })
  }, [])

  const hasRole = useCallback(
    (role: string) => state.user?.roles.includes(role) ?? false,
    [state.user],
  )

  return (
    <AuthContext.Provider value={{ ...state, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
