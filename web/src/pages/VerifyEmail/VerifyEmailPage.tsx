import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import { getErrorStatus } from '../../api/httpClient'
import { AuthLayout } from '../../components/AuthLayout'
import { ErrorMessage } from '../../components/ErrorMessage'
import { FormField } from '../../components/FormField'
import { Loading } from '../../components/Loading'
import { useSubmission } from '../../hooks/useSubmission'
import { isValidEmail } from '../../utils/validation'

type Status =
  | 'verifying'
  | 'verified'
  | 'invalid'
  | 'already'
  | 'error'

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [status, setStatus] = useState<Status>('verifying')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [resendEmail, setResendEmail] = useState('')
  const [resent, setResent] = useState(false)

  useEffect(() => {
    if (!token) {
      setStatus('invalid')
      return
    }
    let active = true
    authApi
      .verifyEmail(token)
      .then(() => active && setStatus('verified'))
      .catch((err: unknown) => {
        if (!active) return
        const status = getErrorStatus(err)
        if (status === 409) setStatus('already')
        else if (status === 401) setStatus('invalid')
        else {
          setStatus('error')
          setErrorMsg(err instanceof Error ? err.message : 'Error de red. Inténtalo de nuevo.')
        }
      })
    return () => {
      active = false
    }
  }, [token])

  const resend = useSubmission(async () => {
    if (!isValidEmail(resendEmail)) return
    await authApi.resendVerification(resendEmail)
    setResent(true)
  })

  const body = () => {
    switch (status) {
      case 'verifying':
        return <Loading label="Verificando tu correo…" />
      case 'verified':
        return (
          <div className="alert alert-success" role="status">
            Tu correo se ha verificado correctamente. Ya puedes acceder.
          </div>
        )
      case 'already':
        return (
          <div className="alert alert-info" role="status">
            Este correo ya estaba verificado.
          </div>
        )
      case 'invalid':
        return (
          <>
            <div className="alert alert-error" role="alert">
              El enlace de verificación es inválido o ha caducado. Solicita uno nuevo.
            </div>
            <ResendForm
              email={resendEmail}
              setEmail={setResendEmail}
              resent={resent}
              onResend={resend.run}
              submitting={resend.submitting}
            />
          </>
        )
      case 'error':
        return (
          <>
            <ErrorMessage message={errorMsg} />
            <ResendForm
              email={resendEmail}
              setEmail={setResendEmail}
              resent={resent}
              onResend={resend.run}
              submitting={resend.submitting}
            />
          </>
        )
    }
  }

  return (
    <AuthLayout title="Verificar email" subtitle="Confirmación de tu cuenta">
      {body()}
      <div className="actions">
        <Link className="btn btn-outline" to="/auth/login">
          Ir a iniciar sesión
        </Link>
      </div>
    </AuthLayout>
  )
}

function ResendForm({
  email,
  setEmail,
  resent,
  onResend,
  submitting,
}: {
  email: string
  setEmail: (v: string) => void
  resent: boolean
  onResend: () => Promise<unknown>
  submitting: boolean
}) {
  return (
    <form
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        void onResend()
      }}
    >
      {resent ? (
        <div className="alert alert-success" role="status">
          Si el email existe, recibirás un nuevo enlace de verificación.
        </div>
      ) : null}
      <FormField
        label="Tu email"
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
          {submitting ? 'Enviando…' : 'Reenviar verificación'}
        </button>
      </div>
    </form>
  )
}
