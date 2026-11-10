import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import type { EntityRequestInfo } from '../../api/types'

function formatDate(value: string): string {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' })
}

// Solicitudes de incorporación pendientes de las entidades que gestiona el usuario.
export function EntityRequestsPage() {
  const [requests, setRequests] = useState<EntityRequestInfo[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = async () => {
    try {
      setRequests(await authApi.listEntityRequests())
    } catch {
      setError('No se pudieron cargar las solicitudes.')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const decide = async (request: EntityRequestInfo, action: 'approve' | 'reject') => {
    setBusyId(request.id)
    setError(null)
    setMessage(null)
    try {
      await authApi.decideEntityRequest(request.id, action)
      setMessage(
        action === 'approve'
          ? `Incorporación de «${request.nickname ?? request.name ?? request.user_id}» aprobada.`
          : `Solicitud de «${request.nickname ?? request.name ?? request.user_id}» rechazada.`,
      )
      await load()
    } catch {
      setError('No se pudo registrar la decisión.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="panel">
      <h3 className="panel-title">Solicitudes de ingreso</h3>
      <p className="panel-sub">
        Personas que han solicitado unirse a las entidades que gestionas. Cada entidad se
        aprueba o rechaza de forma independiente.
      </p>

      {requests.length === 0 ? (
        <p className="muted">No hay solicitudes pendientes.</p>
      ) : (
        <ul>
          {requests.map((request) => (
            <li key={request.id}>
              <strong>{request.nickname ?? request.name ?? request.user_id}</strong> solicita
              unirse a <strong>{request.entity_name}</strong> ({request.entity_kind}) —{' '}
              {formatDate(request.requested_at)}
              <div className="row" style={{ marginTop: '0.5rem' }}>
                <button
                  className="btn btn-primary btn-sm"
                  disabled={busyId === request.id}
                  onClick={() => void decide(request, 'approve')}
                >
                  Aprobar
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  disabled={busyId === request.id}
                  onClick={() => void decide(request, 'reject')}
                >
                  Rechazar
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {error && <p className="error">{error}</p>}
      {message && <p className="muted">{message}</p>}

      <Link className="btn btn-outline btn-sm" to="/auth/account">
        Volver a tu cuenta
      </Link>
    </div>
  )
}
