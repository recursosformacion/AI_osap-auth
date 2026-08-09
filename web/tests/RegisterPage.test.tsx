import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { authApi } from '../src/api/authApi'
import { RegisterPage } from '../src/pages/Register/RegisterPage'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../src/api/authApi', () => ({
  authApi: {
    register: vi.fn(),
  },
}))

const registerMock = vi.mocked(authApi.register)

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function renderRegister() {
  return render(
    <MemoryRouter>
      <RegisterPage />
    </MemoryRouter>,
  )
}

describe('RegisterPage', () => {
  it('valida coincidencia de contraseñas antes de llamar al backend', async () => {
    const user = userEvent.setup()
    renderRegister()

    await user.type(screen.getByLabelText('Email'), 'a@b.com')
    await user.type(screen.getByLabelText('Contraseña'), 'secret-password')
    await user.type(screen.getByLabelText('Confirmar contraseña'), 'other-password')
    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(screen.getByText('Las contraseñas no coinciden')).toBeInTheDocument()
    expect(registerMock).not.toHaveBeenCalled()
  })

  it('muestra pantalla de cuenta creada tras registrar', async () => {
    registerMock.mockResolvedValueOnce({
      user_id: 'u1',
      verification_token: null,
      message: 'ok',
    })
    const user = userEvent.setup()
    renderRegister()

    await user.type(screen.getByLabelText('Email'), 'a@b.com')
    await user.type(screen.getByLabelText('Contraseña'), 'secret-password')
    await user.type(screen.getByLabelText('Confirmar contraseña'), 'secret-password')
    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(
      await screen.findByText(/Comprueba tu correo electrónico para activarla/),
    ).toBeInTheDocument()
    expect(registerMock).toHaveBeenCalledWith({ email: 'a@b.com', password: 'secret-password' })
  })
})
