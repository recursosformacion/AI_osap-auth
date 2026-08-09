import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/AuthContext'
import { AuthLayout } from '../../components/AuthLayout'
import { ErrorMessage } from '../../components/ErrorMessage'
import { FormField } from '../../components/FormField'
import { PasswordField } from '../../components/PasswordField'
import { useSubmission } from '../../hooks/useSubmission'
import { isValidEmail } from '../../utils/validation'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/auth/account'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)

  const { run, submitting, error } = useSubmission(async () => {
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
    navigate(from, { replace: true })
  })

  return (
    <AuthLayout title="Iniciar sesión" subtitle="Accede a tu cuenta de OSAP">
      <ErrorMessage message={fieldError ?? error} />
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          void run()
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
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? 'Entrando…' : 'Entrar'}
          </button>
        </div>
      </form>
      <div className="stack" style={{ marginTop: 16 }}>
        <Link className="link text-center" to="/auth/forgot-password">
          ¿Has olvidado tu contraseña?
        </Link>
        <p className="muted text-center" style={{ margin: 0 }}>
          ¿No tienes cuenta?{' '}
          <Link className="link" to="/auth/register">
            Crear una cuenta
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
