import { useState } from 'react'
import { Link } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { AuthLayout } from '../../components/AuthLayout'
import { ErrorMessage } from '../../components/ErrorMessage'
import { FormField } from '../../components/FormField'
import { PasswordField } from '../../components/PasswordField'
import { useSubmission } from '../../hooks/useSubmission'
import { isValidEmail, passwordMessage } from '../../utils/validation'

export function RegisterPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const { run, submitting, error } = useSubmission(async () => {
    if (!isValidEmail(email)) {
      setFieldError('Introduce un email válido')
      return
    }
    const pwError = passwordMessage(password)
    if (pwError) {
      setFieldError(pwError)
      return
    }
    if (password !== confirm) {
      setFieldError('Las contraseñas no coinciden')
      return
    }
    setFieldError(null)
    await authApi.register({ email, password, name: name.trim() || undefined })
    setDone(true)
  })

  if (done) {
    return (
      <AuthLayout title="Cuenta creada" subtitle="Un último paso">
        <div className="alert alert-success" role="status">
          Hemos creado tu cuenta. Comprueba tu correo electrónico para activarla.
        </div>
        <div className="actions">
          <Link className="btn btn-primary" to="/auth/login">
            Ir a iniciar sesión
          </Link>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Crear una cuenta" subtitle="Únete a OSAP">
      <ErrorMessage message={fieldError ?? error} />
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          void run()
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
          autoComplete="new-password"
        />
        <PasswordField
          label="Confirmar contraseña"
          name="confirm"
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
        />
        <div className="actions">
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? 'Creando…' : 'Crear cuenta'}
          </button>
        </div>
      </form>
      <p className="muted text-center" style={{ marginTop: 16 }}>
        ¿Ya tienes cuenta?{' '}
        <Link className="link" to="/auth/login">
          Inicia sesión
        </Link>
      </p>
    </AuthLayout>
  )
}
