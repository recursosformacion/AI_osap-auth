import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { ErrorMessage, SuccessMessage } from '../../components/ErrorMessage'
import { FormField } from '../../components/FormField'
import { useSubmission } from '../../hooks/useSubmission'
import { isValidEmail } from '../../utils/validation'

export function ChangeEmailPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const { run, submitting, error } = useSubmission(async () => {
    if (!isValidEmail(email)) {
      setFieldError('Introduce un email válido')
      return
    }
    setFieldError(null)
    await authApi.changeEmail(email)
    setSuccess(
      'Se ha iniciado el cambio de email. Comprueba tu nuevo correo para verificarlo.',
    )
    setEmail('')
  })

  return (
    <div>
      <h2>Cambiar email</h2>
      <div className="panel" style={{ maxWidth: 460 }}>
        <p className="muted">
          El cambio de email requiere verificar el nuevo correo antes de completarse. Tu email
          actual seguirá siendo válido hasta entonces.
        </p>
        <ErrorMessage message={fieldError ?? error} />
        <SuccessMessage message={success} />
        <form
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            void run()
          }}
        >
          <FormField
            label="Nuevo email"
            name="email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="nuevo@ejemplo.com"
            autoComplete="email"
            inputMode="email"
            required
          />
          <div className="actions">
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? 'Enviando…' : 'Solicitar cambio de email'}
            </button>
            <button
              className="btn btn-outline"
              type="button"
              onClick={() => navigate('/auth/account')}
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
