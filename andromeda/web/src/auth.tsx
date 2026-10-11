import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { onAuthStateChanged, type User } from 'firebase/auth'
import { auth, isConfigured } from './firebase'

interface AuthState {
  user: User | null
  loading: boolean
}

const AuthContext = createContext<AuthState>({ user: null, loading: true })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => ({ user: null, loading: isConfigured() }))

  useEffect(() => {
    if (!isConfigured()) return
    return onAuthStateChanged(auth(), (user) => setState({ user, loading: false }))
  }, [])

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  return useContext(AuthContext)
}

/** Route guard: wait for the session to restore, then redirect signed-out users to `/`. */
export function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="py-16 text-center text-sm text-muted-foreground">Loading…</div>
  }
  if (!user) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}