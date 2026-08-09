import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { ErrorMessage, SuccessMessage } from '../../components/ErrorMessage'
import { PasswordField } from '../../components/PasswordField'
import { useSubmission } from '../../hooks/useSubmission'
import { passwordMessage } from '../../utils/validation'

export function ChangePasswordPage() {
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const { run, submitting, error } = useSubmission(async () => {
    if (!current) {
      setFieldError('Introduce tu contraseña actual')
      return
    }
    const pwError = passwordMessage(next)
    if (pwError) {
      setFieldError(pwError)
      return
    }
    if (next !== confirm) {
      setFieldError('Las contraseñas nuevas no coinciden')
      return
    }
    setFieldError(null)
    await authApi.changePassword(current, next)
    setSuccess('Contraseña actualizada. Las demás sesiones han sido cerradas.')
    setCurrent('')
    setNext('')
    setConfirm('')
  })

  return (
    <div>
      <h2>Cambiar contraseña</h2>
      <div className="panel" style={{ maxWidth: 460 }}>
        <ErrorMessage message={fieldError ?? error} />
        <SuccessMessage message={success} />
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void run()
          }}
        >
          <PasswordField
            label="Contraseña actual"
            name="current"
            value={current}
            onChange={setCurrent}
            autoComplete="current-password"
          />
          <PasswordField
            label="Nueva contraseña"
            name="new"
            value={next}
            onChange={setNext}
            autoComplete="new-password"
          />
          <PasswordField
            label="Confirmar nueva contraseña"
            name="confirm"
            value={confirm}
            onChange={setConfirm}
            autoComplete="new-password"
          />
          <div className="actions">
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? 'Guardando…' : 'Cambiar contraseña'}
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
