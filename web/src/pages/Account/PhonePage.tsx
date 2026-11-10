import { useState } from 'react'
import { Link } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { useAuth } from '../../auth/AuthContext'

// Teléfono voluntario para comunicaciones por WhatsApp de la entidad del usuario.
// No es un identificador de cuenta ni se verifica; el usuario puede borrarlo.
export function PhonePage() {
  const { user, reload } = useAuth()
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  if (!user) return null

  const save = async () => {
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      await authApi.updateMyPhone(phone.trim() || null)
      await reload()
      setMessage(phone.trim() ? 'Teléfono guardado.' : 'Teléfono eliminado.')
    } catch {
      setError('No se pudo guardar el teléfono. Revisa el formato (7-15 dígitos).')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="panel">
      <h3 className="panel-title">Teléfono (WhatsApp)</h3>
      <p className="panel-sub">
        Añade un teléfono de forma voluntaria para recibir comunicaciones de tu entidad por
        WhatsApp. Puedes cambiarlo o borrarlo cuando quieras.
      </p>
      <label htmlFor="phone" className="muted">Teléfono</label>
      <input
        id="phone"
        type="tel"
        value={phone}
        disabled={saving}
        maxLength={32}
        placeholder="+34 600 123 456"
        onChange={(e) => setPhone(e.target.value)}
      />
      <div className="row" style={{ marginTop: '0.75rem' }}>
        <button className="btn btn-primary btn-sm" disabled={saving} onClick={save}>
          {saving ? 'Guardando…' : 'Guardar'}
        </button>
        <Link className="btn btn-outline btn-sm" to="/auth/account">
          Volver a tu cuenta
        </Link>
      </div>
      {error && <p className="error">{error}</p>}
      {message && <p className="muted">{message}</p>}
    </div>
  )
}
