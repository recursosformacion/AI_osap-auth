import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'

import { authApi } from '../src/api/authApi'
import { VerifyEmailPage } from '../src/pages/VerifyEmail/VerifyEmailPage'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../src/api/authApi', () => ({
  authApi: {
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
  },
}))

const verifyMock = vi.mocked(authApi.verifyEmail)

afterEach(() => {
  cleanup()
  vi.resetAllMocks()
})

function renderVerify(token: string) {
  return render(
    <MemoryRouter initialEntries={[`/auth/verify-email?token=${token}`]}>
      <VerifyEmailPage />
    </MemoryRouter>,
  )
}

describe('VerifyEmailPage', () => {
  it('muestra éxito cuando el token es válido', async () => {
    verifyMock.mockResolvedValue({ message: 'ok' })
    renderVerify('valid-token')
    expect(await screen.findByText(/Tu correo se ha verificado correctamente/)).toBeInTheDocument()
  })

  it('muestra token inválido y ofrece reenviar', async () => {
    const err = new Error('inválido') as Error & { status?: number }
    err.status = 401
    verifyMock.mockRejectedValue(err)
    renderVerify('bad-token')
    expect(
      await screen.findByText('El enlace de verificación es inválido o ha caducado. Solicita uno nuevo.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Reenviar verificación')).toBeInTheDocument()
  })

  it('muestra "ya verificado" en un 409', async () => {
    const err = new Error('ya') as Error & { status?: number }
    err.status = 409
    verifyMock.mockRejectedValue(err)
    renderVerify('token')
    expect(await screen.findByText('Este correo ya estaba verificado.')).toBeInTheDocument()
  })

  it('sin token muestra enlace inválido', async () => {
    renderVerify('')
    expect(
      await screen.findByText('El enlace de verificación es inválido o ha caducado. Solicita uno nuevo.'),
    ).toBeInTheDocument()
    expect(verifyMock).not.toHaveBeenCalled()
  })
})
