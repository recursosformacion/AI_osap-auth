export function ErrorMessage({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div className="alert alert-error" role="alert">
      {message}
    </div>
  )
}

export function SuccessMessage({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div className="alert alert-success" role="status">
      {message}
    </div>
  )
}
