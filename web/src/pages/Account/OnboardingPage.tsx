import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import type {
  CompleteAuthorizationInput,
  EntityKind,
  EntityListItem,
  LegalCurrent,
} from '../../api/types'
import { useAuth } from '../../auth/AuthContext'

const KIND_LABELS: Record<EntityKind, string> = {
  coral: 'Coral',
  orquesta: 'Orquesta',
  grupo: 'Grupo',
  banda: 'Banda',
  ensemble: 'Ensemble',
  escuela: 'Escuela / Conservatorio',
  iglesia: 'Iglesia',
}

function _pendingAuthorize(): CompleteAuthorizationInput | null {
  const raw = sessionStorage.getItem('osap.pendingAuthorize')
  if (!raw) return null
  try {
    return JSON.parse(raw) as CompleteAuthorizationInput
  } catch {
    return null
  }
}

// El nickname es un handle ASCII (3-30, empieza por letra, termina en letra/número).
// Se ofrece el nombre como propuesta, no como valor inmutable: el usuario puede editarlo.
function proposeNickname(name: string | null | undefined): string {
  if (!name) return ''
  const ascii = name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
  let handle = ascii
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 30)
  handle = handle.replace(/^[^a-z]+/, '').replace(/[^a-z0-9]+$/g, '')
  return handle.length >= 3 ? handle : ''
}

// Alta/onboarding del usuario: nickname único + aceptación legal + visibilidad pública.
// Además pregunta si representa una entidad (y su nombre) o si pertenece a una ya creada.
// La visibilidad viene marcada por defecto (opt-out) y puede desmarcarse aquí mismo.
export function OnboardingPage() {
  const { user, reload } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const fromState = (location.state as { authorize?: CompleteAuthorizationInput } | null)
    ?.authorize
  const [legal, setLegal] = useState<LegalCurrent | null>(null)
  const [nickname, setNickname] = useState(
    user?.nickname ?? proposeNickname(user?.name),
  )
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [terms, setTerms] = useState(user?.onboarding?.terms_accepted ?? false)
  const [privacy, setPrivacy] = useState(user?.onboarding?.privacy_accepted ?? false)
  const [isPublic, setIsPublic] = useState(user?.nickname_public_consent ?? true)
  const [entities, setEntities] = useState<EntityListItem[]>([])
  const [representsEntity, setRepresentsEntity] = useState(false)
  const [entityName, setEntityName] = useState('')
  const [entityKind, setEntityKind] = useState<EntityKind>('coral')
  const [entityEmail, setEntityEmail] = useState('')
  const [memberEntityId, setMemberEntityId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    void (async () => {
      try {
        setLegal(await authApi.getLegalCurrent())
      } catch {
        setError('No se pudieron cargar los textos legales.')
      }
      try {
        setEntities(await authApi.listEntities())
      } catch {
        // El listado es opcional: si falla, el usuario aún puede representar una entidad nueva.
      }
    })()
  }, [])

  // `user` se carga de forma asíncrona: rellenar la propuesta cuando llegue, sin pisar
  // lo que el usuario ya haya escrito.
  useEffect(() => {
    setNickname((current) => current || user?.nickname || proposeNickname(user?.name))
  }, [user?.nickname, user?.name])

  useEffect(() => {
    setPhone((current) => current || user?.phone || '')
  }, [user?.phone])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!legal) return
    if (representsEntity && !entityName.trim()) {
      setError('Indica el nombre de la entidad que representas.')
      return
    }
    if (representsEntity && !entityEmail.trim()) {
      setError('Indica el correo de contacto de la entidad.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await authApi.completeOnboarding({
        nickname: nickname.trim(),
        terms_version: legal.terms_version,
        privacy_version: legal.privacy_version,
        phone: phone.trim() || undefined,
        ...(representsEntity
          ? {
              entity_name: entityName.trim(),
              entity_kind: entityKind,
              entity_email: entityEmail.trim(),
            }
          : memberEntityId
            ? { entity_id: memberEntityId }
            : {}),
      })
      await authApi.setPublicConsent(isPublic)
      // Si veníamos de un `authorize` en curso (email embebido o social), reanudarlo.
      const authorize = fromState ?? _pendingAuthorize()
      sessionStorage.removeItem('osap.pendingAuthorize')
      if (authorize) {
        const res = await authApi.completeAuthorization(authorize)
        const url = new URL(res.redirect_uri)
        url.searchParams.set('code', res.code)
        if (res.state) url.searchParams.set('state', res.state)
        window.location.replace(url.toString())
        return
      }
      await reload()
      navigate('/auth/account')
    } catch {
      setError(
        'No se pudo completar el alta. Revisa el nickname (3-30, único), la entidad (nombre único) y acepta los textos.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <h3 className="panel-title">Completa tu alta</h3>
      <p className="panel-sub">
        Elige tu nickname público y acepta los textos legales. Podrás cambiar la visibilidad cuando quieras.
      </p>

      <label htmlFor="onboarding-nickname" className="muted">Nickname</label>
      <input
        id="onboarding-nickname"
        value={nickname}
        onChange={(e) => setNickname(e.target.value)}
        minLength={3}
        maxLength={30}
        placeholder="3-30 caracteres"
        required
      />

      <label htmlFor="onboarding-phone" className="muted">Teléfono (opcional)</label>
      <input
        id="onboarding-phone"
        type="tel"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        maxLength={32}
        placeholder="+34 600 123 456"
      />
      <p className="muted">
        Solo para comunicaciones por WhatsApp de tu entidad. Puedes borrarlo cuando quieras.
      </p>

      <label className="row" style={{ marginTop: '0.75rem' }}>
        <input
          type="checkbox"
          checked={representsEntity}
          onChange={(e) => {
            setRepresentsEntity(e.target.checked)
            if (e.target.checked) setMemberEntityId('')
          }}
        />
        <span>Represento a una entidad (coral, orquesta, grupo)</span>
      </label>

      {representsEntity && (
        <>
          <label htmlFor="onboarding-entity-name" className="muted">Nombre de la entidad</label>
          <input
            id="onboarding-entity-name"
            value={entityName}
            onChange={(e) => setEntityName(e.target.value)}
            maxLength={120}
            placeholder="Coral nnnnn / Orquesta kkkkk / Grup sss"
            required
          />
          <label htmlFor="onboarding-entity-kind" className="muted">Tipo de entidad</label>
          <select
            id="onboarding-entity-kind"
            value={entityKind}
            onChange={(e) => setEntityKind(e.target.value as EntityKind)}
          >
            {Object.entries(KIND_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <label htmlFor="onboarding-entity-email" className="muted">
            Correo de contacto de la entidad
          </label>
          <input
            id="onboarding-entity-email"
            type="email"
            value={entityEmail}
            onChange={(e) => setEntityEmail(e.target.value)}
            maxLength={254}
            placeholder="contacto@entidad.example"
            required
          />
          <p className="muted">
            Este nombre será el que se ofrezca a futuros usuarios para agruparse. El correo
            queda guardado con el creador como responsable.
          </p>
        </>
      )}

      <label htmlFor="onboarding-member-entity" className="muted" style={{ marginTop: '0.75rem' }}>
        Solicito pertenecer a una entidad ya registrada
      </label>
      <select
        id="onboarding-member-entity"
        value={memberEntityId}
        disabled={representsEntity}
        onChange={(e) => {
          setMemberEntityId(e.target.value)
          if (e.target.value) setRepresentsEntity(false)
        }}
      >
        <option value="">— Ninguna —</option>
        {entities.map((entity) => (
          <option key={entity.id} value={entity.id}>
            {entity.name} ({KIND_LABELS[entity.kind]})
          </option>
        ))}
      </select>
      {memberEntityId ? (
        <p className="muted">
          La solicitud se enviará al gestor de la entidad. No serás miembro hasta que la apruebe.
        </p>
      ) : null}

      <label className="row" style={{ marginTop: '0.75rem' }}>
        <input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} required />
        {legal ? (
          <span>
            Acepto los{' '}
            <a href={legal.terms_url} target="_blank" rel="noreferrer">
              términos ({legal.terms_version})
            </a>
          </span>
        ) : (
          <span>Acepto los términos</span>
        )}
      </label>
      <label className="row">
        <input type="checkbox" checked={privacy} onChange={(e) => setPrivacy(e.target.checked)} required />
        {legal ? (
          <span>
            Acepto la{' '}
            <a href={legal.privacy_url} target="_blank" rel="noreferrer">
              política de privacidad ({legal.privacy_version})
            </a>
          </span>
        ) : (
          <span>Acepto la política de privacidad</span>
        )}
      </label>

      <label className="row" style={{ marginTop: '0.5rem' }}>
        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
        <span>Mostrar mi nickname en la lista pública de colaboradores</span>
      </label>

      {error && <p className="error">{error}</p>}

      <div className="row" style={{ marginTop: '0.75rem' }}>
        <button className="btn btn-primary btn-sm" type="submit" disabled={saving || !legal}>
          {saving ? 'Guardando…' : 'Guardar'}
        </button>
        <Link className="btn btn-outline btn-sm" to="/auth/account">
          Cancelar
        </Link>
      </div>
    </form>
  )
}
