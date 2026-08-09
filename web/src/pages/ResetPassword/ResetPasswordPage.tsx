import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { getErrorStatus } from '../../api/httpClient'
import { AuthLayout } from '../../components/AuthLayout'
import { ErrorMessage } from '../../components/ErrorMessage'
import { PasswordField } from '../../components/PasswordField'
import { useSubmission } from '../../hooks/useSubmission'
import { passwordMessage } from '../../utils/validation'

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const { run, submitting, error } = useSubmission(async () => {
    const pwError = passwordMessage(password)
    if (pwError) {
      setFieldError(pwError)
      return
    }
    if (password !== confirm) {
      setFieldError('Las contraseñas no coinciden')
      return
    }
    if (!token) {
      setFieldError('El enlace de recuperación es inválido o ha caducado')
      return
    }
    setFieldError(null)
    try {
      await authApi.confirmPasswordReset(token, password)
      setDone(true)
    } catch (err) {
      if (getErrorStatus(err) === 401) {
        setFieldError('El enlace de recuperación es inválido o ha caducado')
        return
      }
      throw err
    }
  })

  if (done) {
    return (
      <AuthLayout title="Contraseña actualizada">
        <div className="alert alert-success" role="status">
          Tu contraseña se ha cambiado correctamente. Las demás sesiones han sido cerradas.
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
    <AuthLayout title="Nueva contraseña" subtitle="Establece una contraseña nueva">
      <ErrorMessage message={fieldError ?? error} />
      <form
        onSubmit={(e) => {
          e.preventDefault()
          void run()
        }}
      >
        <PasswordField
          label="Nueva contraseña"
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
            {submitting ? 'Guardando…' : 'Cambiar contraseña'}
          </button>
        </div>
      </form>
    </AuthLayout>
  )
}
