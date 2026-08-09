/**
 * Cliente HTTP único del frontend de osap-auth.
 *
 * - URL base desde VITE_AUTH_API_URL (nunca hardcodeada en componentes).
 * - Cabeceras JSON + Authorization Bearer cuando hay access token.
 * - En un 401, intenta renovar con el refresh token (una vez) y reintenta la petición.
 * - Si el refresh falla, limpia la sesión y notifica (logout).
 */

import { authStorage } from '../auth/authStorage'
import type { HttpError } from './types'

const BASE_URL = import.meta.env.VITE_AUTH_API_URL ?? 'http://127.0.0.1:8200'

type OnUnauthorized = () => void

let onUnauthorized: OnUnauthorized | null = null

/** El AuthContext registra aquí su callback para limpiar el estado en logout forzado. */
export function setOnUnauthorized(cb: OnUnauthorized | null): void {
  onUnauthorized = cb
}

let refreshing: Promise<boolean> | null = null

export class ApiRequestError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function tryRefresh(): Promise<boolean> {
  if (refreshing) return refreshing
  refreshing = (async () => {
    const refreshToken = authStorage.getRefreshToken()
    if (!refreshToken) return false
    try {
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!res.ok) return false
      const data = (await res.json()) as {
        access_token: string
        refresh_token: string
        user_id: string
        roles: string[]
        email_verified: boolean
      }
      authStorage.setTokens(data.access_token, data.refresh_token)
      authStorage.setSession({
        user_id: data.user_id,
        roles: data.roles,
        email_verified: data.email_verified,
      })
      return true
    } catch {
      return false
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

async function request<T>(
  path: string,
  init: RequestInit,
  { retried = false }: { retried?: boolean } = {},
): Promise<T> {
  const access = authStorage.getAccessToken()
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (access) headers.set('Authorization', `Bearer ${access}`)

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers })

  if (response.status === 401 && !retried) {
    const ok = await tryRefresh()
    if (ok) {
      return request<T>(path, init, { retried: true })
    }
    authStorage.clear()
    onUnauthorized?.()
    throw new ApiRequestError(401, 'Sesión expirada. Inicia sesión de nuevo.')
  }

  if (!response.ok) {
    let message = `Error ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string | unknown }
      if (typeof body?.detail === 'string') message = body.detail
    } catch {
      /* sin cuerpo JSON */
    }
    throw new ApiRequestError(response.status, message)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const httpClient = {
  get<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'GET' })
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'PATCH', body: body === undefined ? undefined : JSON.stringify(body) })
  },
  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' })
  },
}

export function getBaseUrl(): string {
  return BASE_URL
}

export function toHttpError(error: unknown): HttpError {
  if (error instanceof ApiRequestError) {
    return { status: error.status, message: error.message }
  }
  if (error instanceof Error) {
    return { status: 0, message: error.message }
  }
  return { status: 0, message: 'Error de red' }
}

/** Extrae el código HTTP de un error, venga de ApiRequestError o de un mock/Error con status. */
export function getErrorStatus(error: unknown): number | undefined {
  if (error instanceof ApiRequestError) return error.status
  if (error && typeof error === 'object' && 'status' in error) {
    return (error as { status?: number }).status
  }
  return undefined
}
