import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/AuthContext'
import { Loading } from '../../components/Loading'

export function LogoutPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    void (async () => {
      await logout()
      if (active) navigate('/auth/login', { replace: true })
    })()
    return () => {
      active = false
    }
  }, [logout, navigate])

  return <Loading label="Cerrando sesión…" />
}
