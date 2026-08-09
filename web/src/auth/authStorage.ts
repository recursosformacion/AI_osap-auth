/**
 * Almacenamiento de tokens y sesión del frontend de osap-auth.
 *
 * Guardamos el access token y el refresh token, más una sesión mínima (sin PII:
 * solo user_id, roles, email_verified). El email y demás datos personales solo se
 * obtienen del backend y no se persisten.
 */

import type { StoredSession } from './authTypes'

const ACCESS_KEY = 'osap.auth.access'
const REFRESH_KEY = 'osap.auth.refresh'
const SESSION_KEY = 'osap.auth.session'

export const authStorage = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY)
  },
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY)
  },
  getSession(): StoredSession | null {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as StoredSession
    } catch {
      return null
    }
  },
  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(ACCESS_KEY, accessToken)
    localStorage.setItem(REFRESH_KEY, refreshToken)
  },
  setSession(session: StoredSession): void {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(SESSION_KEY)
  },
}
