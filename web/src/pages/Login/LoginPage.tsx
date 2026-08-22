import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { getBaseUrl } from '../../api/httpClient'
import { useAuth } from '../../auth/AuthContext'
import { AuthLayout } from '../../components/AuthLayout'
import { ErrorMessage } from '../../components/ErrorMessage'
import { FormField } from '../../components/FormField'
import { PasswordField } from '../../components/PasswordField'
import { useSubmission } from '../../hooks/useSubmission'
import { isValidEmail, passwordMessage } from '../../utils/validation'
import type { CompleteAuthorizationInput } from '../../api/types'

const SOCIAL_LABELS: Record<string, string> = {
  google: 'Continuar con Google',
  github: 'Continuar con GitHub',
}

/** Query string con los parámetros OIDC (downstream) para no perder el contexto social. */
function oidcSearch(searchParams: URLSearchParams): string {
  const keys = [
    'client_id',
    'redirect_uri',
    'response_type',
    'scope',
    'state',
    'nonce',
    'code_challenge',
    'code_challenge_method',
  ]
  const params = new URLSearchParams()
  for (const key of keys) {
    const value = searchParams.get(key)
    if (value) params.set(key, value)
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

type Mode = 'login' | 'register' | 'registered'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const from = (location.state as { from?: string } | null)?.from ?? '/auth/account'

  const embed = searchParams.get('embed') === '1'
  const oidc: CompleteAuthorizationInput | null =
    embed && searchParams.get('client_id') && searchParams.get('redirect_uri')
      ? {
          client_id: searchParams.get('client_id') ?? '',
          redirect_uri: searchParams.get('redirect_uri') ?? '',
          response_type: searchParams.get('response_type') ?? 'code',
          scope: searchParams.get('scope') ?? 'openid profile',
          state: searchParams.get('state'),
          nonce: searchParams.get('nonce'),
          code_challenge: searchParams.get('code_challenge'),
          code_challenge_method: searchParams.get('code_challenge_method') ?? 'S256',
        }
      : null

  const [mode, setMode] = useState<Mode>('login')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [socialProviders, setSocialProviders] = useState<string[]>([])

  // Login
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  // Registro
  const [name, setName] = useState('')
  const [regEmail, setRegEmail] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regConfirm, setRegConfirm] = useState('')

  useEffect(() => {
    authApi
      .getSocialProviders()
      .then((res) => setSocialProviders(res.providers))
      .catch(() => {
        /* sin login social */
      })
  }, [])

  const socialQuery = oidcSearch(searchParams)
  const apiBase = getBaseUrl().replace(/\/$/, '')

  const { run: runLogin, submitting: submittingLogin, error: loginError } = useSubmission(
    async () => {
      if (!isValidEmail(email)) {
        setFieldError('Introduce un email válido')
        return
      }
      if (!password) {
        setFieldError('Introduce tu contraseña')
        return
      }
      setFieldError(null)
      await login(email, password)
      if (oidc) {
        const res = await authApi.completeAuthorization(oidc)
        const url = new URL(res.redirect_uri)
        url.searchParams.set('code', res.code)
        if (res.state) url.searchParams.set('state', res.state)
        window.location.replace(url.toString())
        return
      }
      navigate(from, { replace: true })
    },
  )

  const { run: runRegister, submitting: submittingRegister, error: registerError } = useSubmission(
    async () => {
      if (!isValidEmail(regEmail)) {
        setFieldError('Introduce un email válido')
        return
      }
      const pwError = passwordMessage(regPassword)
      if (pwError) {
        setFieldError(pwError)
        return
      }
      if (regPassword !== regConfirm) {
        setFieldError('Las contraseñas no coinciden')
        return
      }
      setFieldError(null)
      await authApi.register({ email: regEmail, password: regPassword, name: name.trim() || undefined })
      setMode('registered')
    },
  )

  const title = mode === 'login' ? 'Iniciar sesión' : mode === 'register' ? 'Crear una cuenta' : 'Cuenta creada'
  const subtitle =
    mode === 'login'
      ? oidc
        ? 'Accede a tu cuenta para continuar'
        : 'Accede a tu cuenta de OSAP'
      : mode === 'register'
        ? 'Únete a OSAP'
        : 'Un último paso'

  const currentError = mode === 'login' ? loginError : mode === 'register' ? registerError : null

  if (mode === 'registered') {
    return (
      <AuthLayout title={title} subtitle={subtitle} embedded={Boolean(oidc)}>
        <div className="alert alert-success" role="status">
          Hemos creado tu cuenta. Te enviaremos un email para activarla.
        </div>
        <div className="actions">
          <button className="btn btn-primary" type="button" onClick={() => setMode('login')}>
            Volver a iniciar sesión
          </button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title={title} subtitle={subtitle} embedded={Boolean(oidc)}>
      <ErrorMessage message={fieldError ?? currentError} />
      {mode === 'login' ? (
        <>
          <form
            noValidate
            onSubmit={(e) => {
              e.preventDefault()
              void runLogin()
            }}
          >
            <FormField
              label="Email"
              name="email"
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="tucorreo@ejemplo.com"
              autoComplete="email"
              inputMode="email"
              required
            />
            <PasswordField
              label="Contraseña"
              name="password"
              value={password}
              onChange={setPassword}
              placeholder="••••••••"
              autoComplete="current-password"
            />
            <div className="actions">
              <button className="btn btn-primary" type="submit" disabled={submittingLogin}>
                {submittingLogin ? 'Entrando…' : 'Entrar'}
              </button>
            </div>
          </form>

          {socialProviders.length > 0 ? (
            <div className="stack" style={{ marginTop: 16 }}>
              <div className="divider">o continúa con</div>
              {socialProviders.map((provider) => (
                <a
                  key={provider}
                  className="btn btn-outline"
                  href={`${apiBase}/auth/oauth/${provider}${socialQuery}`}
                >
                  {SOCIAL_LABELS[provider] ?? `Continuar con ${provider}`}
                </a>
              ))}
            </div>
          ) : null}

          <div className="stack" style={{ marginTop: 16 }}>
            <Link className="link text-center" to="/auth/forgot-password">
              ¿Has olvidado tu contraseña?
            </Link>
            <p className="muted text-center" style={{ margin: 0 }}>
              ¿No tienes cuenta?{' '}
              <button type="button" className="link-as-button" onClick={() => setMode('register')}>
                Crear una cuenta
              </button>
            </p>
          </div>
        </>
      ) : (
        <form
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            void runRegister()
          }}
        >
          <FormField
            label="Nombre"
            name="name"
            value={name}
            onChange={setName}
            placeholder="Tu nombre (opcional)"
            autoComplete="name"
          />
          <FormField
            label="Email"
            name="regEmail"
            type="email"
            value={regEmail}
            onChange={setRegEmail}
            placeholder="tucorreo@ejemplo.com"
            autoComplete="email"
            inputMode="email"
            required
          />
          <PasswordField
            label="Contraseña"
            name="regPassword"
            value={regPassword}
            onChange={setRegPassword}
            autoComplete="new-password"
          />
          <PasswordField
            label="Confirmar contraseña"
            name="regConfirm"
            value={regConfirm}
            onChange={setRegConfirm}
            autoComplete="new-password"
          />
          <div className="actions">
            <button className="btn btn-primary" type="submit" disabled={submittingRegister}>
              {submittingRegister ? 'Creando…' : 'Crear cuenta'}
            </button>
          </div>
          <p className="muted text-center" style={{ marginTop: 16 }}>
            ¿Ya tienes cuenta?{' '}
            <button type="button" className="link-as-button" onClick={() => setMode('login')}>
              Inicia sesión
            </button>
          </p>
        </form>
      )}
    </AuthLayout>
  )
}
