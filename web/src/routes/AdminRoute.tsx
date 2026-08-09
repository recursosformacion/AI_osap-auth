import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'
import { Loading } from '../components/Loading'

/**
 * Ruta administrativa. La autorización viene determinada por el rol del backend
 * (claim `roles` del token); el frontend solo refleja esa información, no decide.
 */
export function AdminRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, isAdmin } = useAuth()

  if (isLoading) {
    return <Loading label="Comprobando acceso…" />
  }
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />
  }
  if (!isAdmin) {
    return <Navigate to="/auth/account" replace />
  }
  return <>{children}</>
}
