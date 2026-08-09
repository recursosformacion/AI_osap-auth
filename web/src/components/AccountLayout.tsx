import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'

export function AccountLayout({ children }: { children?: ReactNode }) {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <div className="app-nav-inner">
          <NavLink to="/auth/account" className="brand" style={{ textDecoration: 'none' }}>
            <span className="brand-mark">OS</span>
            <span className="brand-name">OSAP</span>
          </NavLink>
          <NavLink to="/auth/account" end className="nav-link">
            Cuenta
          </NavLink>
          <NavLink to="/auth/account/sessions" className="nav-link">
            Sesiones
          </NavLink>
          <NavLink to="/auth/account/password" className="nav-link">
            Contraseña
          </NavLink>
          {isAdmin ? (
            <NavLink to="/auth/admin/users" className="nav-link">
              Administración
            </NavLink>
          ) : null}
          <span style={{ flex: 1 }} />
          {user ? <span className="muted">{user.email}</span> : null}
          <button className="btn btn-outline btn-sm" onClick={() => void handleLogout()}>
            Cerrar sesión
          </button>
        </div>
      </nav>
      <main className="app-content">
        {children ?? <Outlet />}
      </main>
    </div>
  )
}
