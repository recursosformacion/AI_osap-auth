import { useCallback, useState } from 'react'

/**
 * Hook auxiliar para formularios: estado de envío (submitting) y manejo genérico
 * de errores como mensaje de usuario.
 */
export function useSubmission<TArgs extends unknown[]>(
  fn: (...args: TArgs) => Promise<unknown>,
) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(
    async (...args: TArgs) => {
      setSubmitting(true)
      setError(null)
      try {
        await fn(...args)
        return true
      } catch (err) {
        setError(messageFromError(err))
        return false
      } finally {
        setSubmitting(false)
      }
    },
    [fn],
  )

  return { run, submitting, error, setError }
}

function messageFromError(err: unknown): string {
  if (err instanceof Error) return err.message
  return 'Se ha producido un error inesperado'
}
