import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render } from '@testing-library/react'

import { authStorage } from '../src/auth/authStorage'
import { AuthProvider } from '../src/auth/AuthContext'
import { MemoryRouter } from 'react-router-dom'

const mocks = vi.hoisted(() => ({
  getMe: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('../src/api/authApi', () => ({
  authApi: {
    getMe: mocks.getMe,
    logout: mocks.logout,
  },
}))

function renderProvider() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <div>child</div>
      </AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  authStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('AuthContext (restauración)', () => {
  it('estado anónimo si no hay token', async () => {
    renderProvider()
    await new Promise((r) => setTimeout(r, 50))
    expect(mocks.getMe).not.toHaveBeenCalled()
  })

  it('limpia la sesión si el token es inválido', async () => {
    authStorage.setTokens('at', 'rt')
    mocks.getMe.mockRejectedValueOnce(new Error('bad'))
    renderProvider()
    await new Promise((r) => setTimeout(r, 50))
    expect(authStorage.getAccessToken()).toBeNull()
    expect(authStorage.getRefreshToken()).toBeNull()
  })

  it('almacena sesión mínima sin email (sin PII)', () => {
    authStorage.setTokens('at', 'rt')
    authStorage.setSession({ user_id: 'u1', roles: ['admin'], email_verified: true })
    const session = authStorage.getSession()
    expect(session).toEqual({ user_id: 'u1', roles: ['admin'], email_verified: true })
    expect(localStorage.getItem('osap.auth.session') ?? '').not.toContain('@')
  })
})
