import { useState } from 'react'
import { Link } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { useAuth } from '../../auth/AuthContext'

// Privacidad y visibilidad: autorización de cuenta para publicar el nickname en la lista
// pública de colaboradores (la lista la compone osap-api desde osap-auth).
export function PrivacyPage() {
  const { user, reload } = useAuth()
  const [isPublic, setIsPublic] = useState(user?.nickname_public_consent ?? false)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  if (!user) return null

  const toggle = async (value: boolean) => {
    setSaving(true)
    setError(null)
    try {
      await authApi.setPublicConsent(value)
      setIsPublic(value)
      await reload()
    } catch {
      setError('No se pudo guardar la preferencia.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="panel">
      <h3 className="panel-title">Privacidad y visibilidad</h3>
      {user.nickname ? (
        <>
          <p className="panel-sub">
            Tu nickname público: <strong>{user.nickname}</strong>
          </p>
          <label className="row">
            <input
              type="checkbox"
              checked={isPublic}
              disabled={saving}
              onChange={(e) => void toggle(e.target.checked)}
            />
            <span>Mostrar mi nickname en la lista pública de colaboradores</span>
          </label>
          <p className="muted">
            Solo se publica el nickname. El email, tu nombre y tus datos nunca se muestran.
          </p>
        </>
      ) : (
        <p className="panel-sub">
          Aún no has elegido nickname.{' '}
          <Link to="/auth/account/onboarding">Completa tu alta</Link> para poder publicarte.
        </p>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
