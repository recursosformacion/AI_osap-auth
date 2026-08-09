import { useId } from 'react'

interface FormFieldProps {
  label: string
  type?: string
  name: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  error?: string | null
  autoComplete?: string
  required?: boolean
  inputMode?: 'email' | 'text' | 'numeric' | undefined
}

export function FormField({
  label,
  type = 'text',
  name,
  value,
  onChange,
  placeholder,
  error,
  autoComplete,
  required,
  inputMode,
}: FormFieldProps) {
  const id = useId()
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        className="form-input"
        type={type}
        name={name}
        value={value}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required={required}
        inputMode={inputMode}
        onChange={(e) => onChange(e.target.value)}
      />
      {error ? <p className="field-error">{error}</p> : null}
    </div>
  )
}
