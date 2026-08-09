import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { useAuth } from '../../auth/AuthContext'
import { ErrorMessage } from '../../components/ErrorMessage'
import { useSubmission } from '../../hooks/useSubmission'

export function DeleteAccountPage() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [confirmed, setConfirmed] = useState(false)
  const [typed, setTyped] = useState('')

  const { run, submitting, error } = useSubmission(async () => {
    if (typed.trim() !== 'ELIMINAR') {
      return
    }
    await authApi.deleteAccount()
    await logout()
    navigate('/auth/login', { replace: true })
  })

  return (
    <div>
      <h2>Eliminar tu cuenta</h2>
      <div className="panel" style={{ maxWidth: 520, borderColor: '#fecaca' }}>
        <div className="alert alert-error" role="alert">
          <strong>Eliminar tu cuenta es una operación permanente.</strong>
          <p className="muted" style={{ marginTop: 8 }}>
            Se cerrarán todas tus sesiones y tus datos de identidad se eliminarán. En los
            servicios de OSAP se conservará únicamente el dato estadístico agregado, sin
            relación con tu identidad. Esta acción no puede deshacerse.
          </p>
        </div>

        <label className="form-field" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          Entiendo las consecuencias y quiero eliminar mi cuenta definitivamente.
        </label>

        <div className="form-field">
          <label>Escribe ELIMINAR para confirmar</label>
          <input
            className="form-input"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="ELIMINAR"
          />
        </div>

        <ErrorMessage message={error} />

        <div className="actions">
          <button
            className="btn btn-danger"
            disabled={submitting || !confirmed || typed.trim() !== 'ELIMINAR'}
            onClick={() => void run()}
          >
            {submitting ? 'Eliminando…' : 'Eliminar mi cuenta definitivamente'}
          </button>
          <button className="btn btn-outline" onClick={() => navigate('/auth/account')}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}
