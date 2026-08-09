import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { httpClient, setOnUnauthorized, ApiRequestError } from '../src/api/httpClient'
import { authStorage } from '../src/auth/authStorage'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const fetchMock = vi.fn()
const unauthorizedMock = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  authStorage.setTokens('at-old', 'rt-old')
  setOnUnauthorized(unauthorizedMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  authStorage.clear()
  setOnUnauthorized(null)
  vi.clearAllMocks()
})

describe('httpClient', () => {
  it('renueva con el refresh token y reintenta en un 401', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          access_token: 'at-new',
          refresh_token: 'rt-new',
          user_id: 'u1',
          roles: ['user'],
          email_verified: true,
        }),
      )
      .mockResolvedValueOnce(jsonResponse(200, { user_id: 'u1' }))

    const data = await httpClient.get<{ user_id: string }>('/auth/me')

    expect(data.user_id).toBe('u1')
    // 1. me(401) 2. refresh 3. me(reintento)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[1][0]).toContain('/auth/refresh')
    expect(authStorage.getAccessToken()).toBe('at-new')
  })

  it('si el refresh falla, limpia y notifica logout', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'bad' }))

    await expect(httpClient.get('/auth/me')).rejects.toBeInstanceOf(ApiRequestError)
    expect(unauthorizedMock).toHaveBeenCalled()
    expect(authStorage.getAccessToken()).toBeNull()
    expect(authStorage.getRefreshToken()).toBeNull()
  })

  it('propaga el mensaje detail del backend en errores', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(422, { detail: 'password demasiado corta' }))
    await expect(httpClient.post('/auth/register', {})).rejects.toThrow(
      'password demasiado corta',
    )
  })
})
