import { render } from '@testing-library/react'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import type { ReactElement, ReactNode } from 'react'

import { AuthProvider } from '../src/auth/AuthContext'

export function renderWithProviders(ui: ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

export function renderAuthenticated(ui: ReactElement) {
  return render(
    <MemoryRouter>
      <AuthProvider>{ui}</AuthProvider>
    </MemoryRouter>,
  )
}

export function Wrapper({ children }: { children: ReactNode }) {
  return (
    <MemoryRouter>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  )
}
