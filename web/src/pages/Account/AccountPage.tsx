import { Link } from 'react-router-dom'

import { useAuth } from '../../auth/AuthContext'

function formatDate(value: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' })
}

export function AccountPage() {
  const { user } = useAuth()

  if (!user) return null

  return (
    <div>
      <h2>Tu cuenta</h2>

      <section className="panel">
        <h3 className="panel-title">Cuenta</h3>
        <p className="panel-sub">Tus datos de identidad.</p>
        <dl>
          <dt className="muted">Nombre</dt>
          <dd>{user.name || '—'}</dd>
          <dt className="muted">Email</dt>
          <dd>{user.email}</dd>
          <dt className="muted">Estado de verificación</dt>
          <dd>
            {user.email_verified ? (
              <span className="badge badge-ok">Verificado</span>
            ) : (
              <span className="badge badge-warn">Sin verificar</span>
            )}
          </dd>
          <dt className="muted">Fecha de creación</dt>
          <dd>{formatDate(user.created_at)}</dd>
        </dl>
      </section>

      <section className="panel">
        <h3 className="panel-title">Seguridad</h3>
        <p className="panel-sub">Gestiona tu contraseña y tus sesiones.</p>
        <div className="row">
          <Link className="btn btn-outline btn-sm" to="/auth/account/password">
            Cambiar contraseña
          </Link>
          <Link className="btn btn-outline btn-sm" to="/auth/account/sessions">
            Sesiones activas
          </Link>
        </div>
      </section>

      <section className="panel">
        <h3 className="panel-title">Cuenta personal</h3>
        <p className="panel-sub">Cambia tu email o elimina tu cuenta.</p>
        <div className="row">
          <Link className="btn btn-outline btn-sm" to="/auth/account/email">
            Cambiar email
          </Link>
          <Link className="btn btn-danger btn-sm" to="/auth/account/delete">
            Eliminar cuenta
          </Link>
        </div>
      </section>
    </div>
  )
}
