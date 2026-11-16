import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../../api/authApi'

import type { MembershipStatus } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'

const MEMBERSHIP_LABELS: Record<MembershipStatus, string> = {
  pending: 'Pendiente de aprobación',
  approved: 'Aprobada',
  rejected: 'Rechazada',
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' })
}

const NEWS_LANGUAGES = [
  ['es', 'Español'],
  ['ca', 'Català'],
  ['fr', 'Français'],
  ['en', 'English'],
  ['de', 'Deutsch'],
] as const
const NEWS_TOPICS = [
  ["coral", "Música coral y vocal"],
  ["clasica", "Música clásica"],
  ["antigua", "Música antigua"],
  ["opera", "Ópera"],
  ["instrumentos", "Instrumentos y técnica"],
  ["educacion", "Educación y formación"],
  ["patrimonio", "Partituras y patrimonio"],
  ["concursos", "Concursos y convocatorias"],
  ["industria", "Industria y tecnología"],
] as const

export function AccountPage() {
  const { user, reload } = useAuth()
  const [newsOptIn, setNewsOptIn] = useState(false)
  const [newsLanguage, setNewsLanguage] = useState("es")
  const [newsLanguages, setNewsLanguages] = useState<string[]>(["es"])
  const [newsTopics, setNewsTopics] = useState<string[]>([])
  const [newsSaving, setNewsSaving] = useState(false)
  const [newsMessage, setNewsMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    setNewsOptIn(Boolean(user.news_opt_in))
    setNewsLanguage(user.news_language ?? "es")
    setNewsLanguages(user.news_languages?.length ? user.news_languages : [user.news_language ?? "es"])
    setNewsTopics(user.news_topics ?? [])
  }, [user])

  const saveNews = async () => {
    setNewsSaving(true)
    setNewsMessage(null)
    try {
      await authApi.updateNewsPreferences({
        news_opt_in: newsOptIn,
        news_language: newsLanguages[0] ?? newsLanguage,
        news_languages: newsLanguages.length ? newsLanguages : [newsLanguage],
        news_topics: newsTopics,
      })
      await reload()
      setNewsMessage("Preferencias guardadas.")
    } catch (error) {
      setNewsMessage(error instanceof Error ? error.message : "No se pudieron guardar.")
    } finally {
      setNewsSaving(false)
    }
  }

  if (!user) return null

  return (
    <div>
      <h2>Tu cuenta</h2>

      {user.onboarding?.required && (
        <section className="panel">
          <h3 className="panel-title">Completa tu alta</h3>
          <p className="panel-sub">
            Elige tu nickname para poder aparecer en la lista pública de colaboradores.
          </p>
          <Link className="btn btn-primary btn-sm" to="/auth/account/onboarding">
            Completar alta
          </Link>
        </section>
      )}

      <section className="panel">
        <h3 className="panel-title">Cuenta</h3>
        <p className="panel-sub">Tus datos de identidad.</p>
        <dl>
          <dt className="muted">Nombre</dt>
          <dd>{user.name || '—'}</dd>
          <dt className="muted">Nickname</dt>
          <dd>{user.nickname || '—'}</dd>
          <dt className="muted">Teléfono</dt>
          <dd>{user.phone || '—'}</dd>
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
        <h3 className="panel-title">Entidades</h3>
        {user.memberships && user.memberships.length > 0 ? (
          <ul>
            {user.memberships.map((membership) => (
              <li key={membership.id}>
                <strong>{membership.entity_name}</strong> ({membership.entity_kind}) —{' '}
                {MEMBERSHIP_LABELS[membership.status]}
                {membership.is_representative ? ' · la representas' : ''}
              </li>
            ))}
          </ul>
        ) : (
          <p className="panel-sub">
            No perteneces a ninguna entidad. Puedes solicitar unirte a una o representar la tuya.
          </p>
        )}
        <div className="row">
          <Link className="btn btn-primary btn-sm" to="/auth/account/entity">
            Gestionar entidades
          </Link>
          <Link className="btn btn-primary btn-sm" to="/auth/account/entity-requests">
            Solicitudes de ingreso
          </Link>
        </div>
      </section>

      <section className="panel">
        <h3 className="panel-title">Seguridad</h3>
        <p className="panel-sub">Gestiona tu contraseña y tus sesiones.</p>
        <div className="row">
          <Link className="btn btn-primary btn-sm" to="/auth/account/password">
            Cambiar contraseña
          </Link>
          <Link className="btn btn-primary btn-sm" to="/auth/account/sessions">
            Sesiones activas
          </Link>
        </div>
      </section>

      <section className="panel">
        <h3 className="panel-title">Privacidad y visibilidad</h3>
        <p className="panel-sub">Controla si tu nickname aparece en la lista pública de colaboradores.</p>
        <div className="row">
          <Link className="btn btn-primary btn-sm" to="/auth/account/privacy">
            Privacidad y visibilidad
          </Link>
        </div>
      </section>

      <section className="panel">
        <h3 className="panel-title">Noticias</h3>
        <p className="panel-sub">
          Puedes leer noticias musicales en OSAP sin recibir correos. Si quieres, activa un resumen por correo en tu idioma y sobre tus temas.
        </p>
        <label className="row" style={{ gap: 8 }}>
          <input
            type="checkbox"
            checked={newsOptIn}
            onChange={(e) => setNewsOptIn(e.target.checked)}
          />
          Recibir un resumen por correo
        </label>
        {newsOptIn ? (
          <>
            <div style={{ marginTop: 10 }}>
              <strong>Idiomas</strong>
              <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
                {NEWS_LANGUAGES.map(([value, label]) => (
                  <label key={value} className="row" style={{ gap: 4 }}>
                    <input
                      type="checkbox"
                      checked={newsLanguages.includes(value)}
                      onChange={(e) =>
                        setNewsLanguages(
                          e.target.checked
                            ? [...newsLanguages, value]
                            : newsLanguages.filter((language) => language !== value),
                        )
                      }
                    />
                    {label}
                  </label>
                ))}
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => setNewsLanguages(NEWS_LANGUAGES.map(([value]) => value))}
                >
                  Todos
                </button>
              </div>
            </div>
            <div style={{ marginTop: 10 }}>
              <strong>Temas</strong>
              <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
                {NEWS_TOPICS.map(([code, label]) => (
                  <label key={code} className="row" style={{ gap: 4 }}>
                    <input
                      type="checkbox"
                      checked={newsTopics.includes(code)}
                      onChange={(e) =>
                        setNewsTopics(
                          e.target.checked
                            ? [...newsTopics, code]
                            : newsTopics.filter((topic) => topic !== code),
                        )
                      }
                    />
                    {label}
                  </label>
                ))}
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => setNewsTopics(NEWS_TOPICS.map(([code]) => code))}
                >
                  Marcar todos los temas
                </button>
              </div>
            </div>
          </>
        ) : null}
        <div className="row" style={{ marginTop: 10 }}>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={newsSaving}
            onClick={() => void saveNews()}
          >
            {newsSaving ? 'Guardando…' : 'Guardar preferencias'}
          </button>
          {newsMessage && <span className="muted">{newsMessage}</span>}
        </div>
      </section>

      <section className="panel">
        <h3 className="panel-title">Cuenta personal</h3>
        <p className="panel-sub">Cambia tu email o elimina tu cuenta.</p>
        <div className="row">
          <Link className="btn btn-primary btn-sm" to="/auth/account/phone">
            Teléfono (WhatsApp)
          </Link>
          <Link className="btn btn-primary btn-sm" to="/auth/account/email">
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

