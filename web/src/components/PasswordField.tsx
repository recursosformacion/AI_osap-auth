import { useId, useState } from 'react'

interface PasswordFieldProps {
  label: string
  name: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  error?: string | null
  autoComplete?: string
}

export function PasswordField({
  label,
  name,
  value,
  onChange,
  placeholder,
  error,
  autoComplete,
}: PasswordFieldProps) {
  const id = useId()
  const [visible, setVisible] = useState(false)
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <div className="password-wrap">
        <input
          id={id}
          className="form-input"
          type={visible ? 'text' : 'password'}
          name={name}
          value={value}
          placeholder={placeholder}
          autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        >
          {visible ? 'Ocultar' : 'Mostrar'}
        </button>
      </div>
      {error ? <p className="field-error">{error}</p> : null}
    </div>
  )
}
