import type { ReactNode } from 'react'

export function AuthLayout({
  title,
  subtitle,
  children,
  embedded = false,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  /** Modo embebido (popup desde otro servicio): oculta la marca OSAP. */
  embedded?: boolean
}) {
  return (
    <div className="auth-shell">
      <div className="auth-card">
        {!embedded ? (
          <div className="brand">
            <span className="brand-mark">OS</span>
            <span className="brand-name">OSAP</span>
          </div>
        ) : (
          <p className="auth-embed-label">Conectar con tu cuenta OSAP</p>
        )}
        <h1 className="auth-title">{title}</h1>
        {subtitle ? <p className="auth-subtitle">{subtitle}</p> : null}
        {children}
      </div>
    </div>
  )
}
