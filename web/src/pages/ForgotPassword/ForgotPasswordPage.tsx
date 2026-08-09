import { useState } from 'react'
import { Link } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { AuthLayout } from '../../components/AuthLayout'
import { FormField } from '../../components/FormField'
import { useSubmission } from '../../hooks/useSubmission'
import { isValidEmail } from '../../utils/validation'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  const { run, submitting, error } = useSubmission(async () => {
    if (!isValidEmail(email)) return
    // Respuesta genérica del backend: nunca revela si el email existe.
    await authApi.requestPasswordReset(email)
    setSent(true)
  })

  return (
    <AuthLayout title="Recuperar contraseña" subtitle="Te ayudamos a recuperar el acceso">
      {sent ? (
        <div className="alert alert-success" role="status">
          Si existe una cuenta asociada a este correo, recibirás instrucciones para
          recuperar tu contraseña.
        </div>
      ) : (
        <form
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            void run()
          }}
        >
          {error ? <div className="alert alert-error">{error}</div> : null}
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
          <div className="actions">
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? 'Enviando…' : 'Enviar instrucciones'}
            </button>
          </div>
        </form>
      )}
      <div className="actions">
        <Link className="btn btn-outline" to="/auth/login">
          Volver a iniciar sesión
        </Link>
      </div>
    </AuthLayout>
  )
}
