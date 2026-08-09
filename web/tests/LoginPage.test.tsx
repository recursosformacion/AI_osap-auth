import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { authStorage } from '../src/auth/authStorage'
import { LoginPage } from '../src/pages/Login/LoginPage'
import { AuthProvider } from '../src/auth/AuthContext'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

vi.mock('../src/api/authApi', () => ({
  authApi: {
    login: vi.fn(async () => ({
      access_token: 'at',
      refresh_token: 'rt',
      user_id: 'u1',
      roles: ['user'],
      email_verified: true,
    })),
    getMe: vi.fn(async () => ({
      user_id: 'u1',
      email: 'a@b.com',
      roles: ['user'],
      email_verified: true,
      status: 'active',
      created_at: null,
    })),
  },
}))

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/auth/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/account" element={<div>account page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  authStorage.clear()
  vi.clearAllMocks()
})

describe('LoginPage', () => {
  it('inicia sesión y navega a la cuenta', async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('Email'), 'a@b.com')
    await user.type(screen.getByLabelText('Contraseña'), 'secret-password')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('account page')).toBeInTheDocument()
    expect(authStorage.getAccessToken()).toBe('at')
  })

  it('muestra error de validación con email inválido', async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByLabelText('Email'), 'no-es-email')
    await user.type(screen.getByLabelText('Contraseña'), 'secret-password')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Introduce un email válido')).toBeInTheDocument()
  })

  it('ofrece enlaces a registro y recuperación', () => {
    renderLogin()
    expect(screen.getByText('¿Has olvidado tu contraseña?')).toBeInTheDocument()
    expect(screen.getByText('Crear una cuenta')).toBeInTheDocument()
  })
})
