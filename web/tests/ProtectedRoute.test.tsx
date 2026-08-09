import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'

import { authStorage } from '../src/auth/authStorage'
import { AuthProvider } from '../src/auth/AuthContext'
import { ProtectedRoute } from '../src/routes/ProtectedRoute'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const mocks = vi.hoisted(() => ({
  getMe: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('../src/api/authApi', () => ({
  authApi: { getMe: mocks.getMe, logout: mocks.logout },
}))

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/private']}>
      <AuthProvider>
        <Routes>
          <Route
            path="/private"
            element={
              <ProtectedRoute>
                <div>contenido privado</div>
              </ProtectedRoute>
            }
          />
          <Route path="/auth/login" element={<div>login page</div>} />
        </Routes>
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

describe('ProtectedRoute', () => {
  it('redirige a login si no hay sesión', async () => {
    renderProtected()
    expect(await screen.findByText('login page')).toBeInTheDocument()
  })

  it('muestra el contenido si hay sesión', async () => {
    authStorage.setTokens('at', 'rt')
    mocks.getMe.mockResolvedValueOnce({
      user_id: 'u1',
      email: 'a@b.com',
      roles: ['user'],
      email_verified: true,
      status: 'active',
      created_at: null,
    })
    renderProtected()
    expect(await screen.findByText('contenido privado')).toBeInTheDocument()
  })
})
