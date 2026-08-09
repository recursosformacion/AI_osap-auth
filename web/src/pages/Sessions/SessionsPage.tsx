import { useEffect, useState } from 'react'

import { authApi } from '../../api/authApi'
import type { SessionInfo } from '../../api/types'
import { ErrorMessage } from '../../components/ErrorMessage'
import { Loading } from '../../components/Loading'

function formatDate(value: string): string {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })
}

export function SessionsPage() {
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const load = async () => {
    setLoading(true)
    try {
      setSessions(await authApi.getSessions())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar sesiones')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const revoke = async (id: string) => {
    try {
      await authApi.revokeSession(id)
      setSessions((prev) =>
        prev ? prev.map((s) => (s.id === id ? { ...s, revoked: true } : s)) : prev,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cerrar la sesión')
    }
  }

  const revokeAll = async () => {
    try {
      await authApi.logoutAll()
      setSessions((prev) => (prev ? prev.map((s) => ({ ...s, revoked: true })) : prev))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron cerrar las sesiones')
    }
  }

  return (
    <div>
      <h2>Sesiones activas</h2>
      <ErrorMessage message={error} />
      {loading ? (
        <Loading label="Cargando sesiones…" />
      ) : (
        <div className="panel">
          {sessions && sessions.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Dispositivo</th>
                  <th>Navegador</th>
                  <th>Creada</th>
                  <th>Última actividad</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id}>
                    <td>{s.device_label || '—'}</td>
                    <td>{s.user_agent || '—'}</td>
                    <td>{formatDate(s.created_at)}</td>
                    <td>{formatDate(s.last_used_at)}</td>
                    <td>
                      {s.revoked ? (
                        <span className="badge badge-danger">Cerrada</span>
                      ) : (
                        <span className="badge badge-ok">Activa</span>
                      )}
                    </td>
                    <td>
                      {!s.revoked ? (
                        <button
                          className="btn btn-outline btn-sm"
                          onClick={() => void revoke(s.id)}
                        >
                          Cerrar
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">No hay sesiones activas.</p>
          )}
          <div className="row" style={{ marginTop: 16 }}>
            <button className="btn btn-outline btn-sm" onClick={() => void revokeAll()}>
              Cerrar todas las sesiones
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
