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

// Alta/onboarding del usuario: nickname único + aceptación legal + visibilidad pública.
// La visibilidad viene marcada por defecto (opt-out) y puede desmarcarse aquí mismo.
export function OnboardingPage() {
  const { user, reload } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const fromState = (location.state as { authorize?: CompleteAuthorizationInput } | null)
    ?.authorize
  const [legal, setLegal] = useState<LegalCurrent | null>(null)
  const [nickname, setNickname] = useState(user?.nickname ?? '')
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
