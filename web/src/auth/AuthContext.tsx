import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { authApi } from '../api/authApi'
import { setOnUnauthorized } from '../api/httpClient'
import { authStorage } from './authStorage'
import type { AuthStatus, AuthUser } from './authTypes'

interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  isAdmin: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<boolean>
  reload: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<AuthUser | null>(null)

  const clearLocal = useCallback(() => {
    authStorage.clear()
    setUser(null)
    setStatus('anonymous')
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      /* logout local de todas formas */
    }
    clearLocal()
  }, [clearLocal])

  const restore = useCallback(async () => {
    if (!authStorage.getAccessToken()) {
      setStatus('anonymous')
      return
    }
    setStatus('loading')
    try {
      const me = await authApi.getMe()
      setUser(me)
      authStorage.setSession({
        user_id: me.user_id,
        roles: me.roles,
        email_verified: me.email_verified,
      })
      setStatus('authenticated')
    } catch {
      clearLocal()
    }
  }, [clearLocal])

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await authApi.login(email, password)
      authStorage.setTokens(res.access_token, res.refresh_token)
      authStorage.setSession({
        user_id: res.user_id,
        roles: res.roles,
        email_verified: res.email_verified,
      })
      setStatus('authenticated')
      try {
        setUser(await authApi.getMe())
      } catch {
        setUser({
          user_id: res.user_id,
          email: email,
          roles: res.roles,
          email_verified: res.email_verified,
          status: 'active',
          created_at: null,
        })
      }
    },
    [],
  )

  const reload = useCallback(async () => {
    try {
      setUser(await authApi.getMe())
    } catch {
      /* se conserva el usuario actual si falla */
    }
  }, [])

  const refresh = useCallback(async (): Promise<boolean> => {
    const token = authStorage.getRefreshToken()
    if (!token) return false
    try {
      const res = await authApi.refresh(token)
      authStorage.setTokens(res.access_token, res.refresh_token)
      authStorage.setSession({
        user_id: res.user_id,
        roles: res.roles,
        email_verified: res.email_verified,
      })
      return true
    } catch {
      clearLocal()
      return false
    }
  }, [clearLocal])

  useEffect(() => {
    // Handoff del gate de onboarding en el flujo social: el callback redirige aquí con los
    // tokens en el #fragment y el contexto OIDC para reanudar `authorize/complete` después.
    const hash = window.location.hash
    if (hash && hash.includes('access_token=')) {
      const params = new URLSearchParams(hash.slice(1))
      const access = params.get('access_token')
      const refresh = params.get('refresh_token')
      if (access) authStorage.setTokens(access, refresh ?? '')
      if (params.get('authorize') === '1') {
        sessionStorage.setItem(
          'osap.pendingAuthorize',
          JSON.stringify({
            client_id: params.get('client_id') ?? '',
            redirect_uri: params.get('redirect_uri') ?? '',
            response_type: params.get('response_type') ?? 'code',
            scope: params.get('scope') ?? 'openid profile',
            state: params.get('state') || null,
            nonce: params.get('nonce') || null,
            code_challenge: params.get('code_challenge') || null,
            code_challenge_method: params.get('code_challenge_method') || 'S256',
          }),
        )
      }
      window.history.replaceState(null, '', window.location.pathname + window.location.search)
    }
    void restore()
  }, [restore])

  useEffect(() => {
    setOnUnauthorized(clearLocal)
    return () => setOnUnauthorized(null)
  }, [clearLocal])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      isAuthenticated: status === 'authenticated',
      isLoading: status === 'loading',
      isAdmin: user?.roles.includes('admin') ?? false,
      login,
      logout,
      refresh,
      reload,
    }),
    [status, user, login, logout, refresh, reload],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
