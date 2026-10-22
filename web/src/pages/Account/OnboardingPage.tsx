import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import type { CompleteAuthorizationInput, LegalCurrent } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'

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
  const [terms, setTerms] = useState(user?.onboarding?.terms_accepted ?? false)
  const [privacy, setPrivacy] = useState(user?.onboarding?.privacy_accepted ?? false)
  const [isPublic, setIsPublic] = useState(user?.nickname_public_consent ?? true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    void (async () => {
      try {
        setLegal(await authApi.getLegalCurrent())
      } catch {
        setError('No se pudieron cargar los textos legales.')
      }
    })()
  }, [])

  // `user` se carga de forma asíncrona: rellenar la propuesta cuando llegue, sin pisar
  // lo que el usuario ya haya escrito.
  useEffect(() => {
    setNickname((current) => current || user?.nickname || proposeNickname(user?.name))
  }, [user?.nickname, user?.name])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!legal) return
    setSaving(true)
    setError(null)
    try {
      await authApi.completeOnboarding({
        nickname: nickname.trim(),
        terms_version: legal.terms_version,
        privacy_version: legal.privacy_version,
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
      setError('No se pudo completar el alta. Revisa el nickname (3-30, único) y acepta los textos.')
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
