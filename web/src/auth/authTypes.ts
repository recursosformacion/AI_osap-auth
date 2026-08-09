export type AuthStatus = 'anonymous' | 'authenticated' | 'loading'

/** Información mínima de sesión persistida (sin PII como el email). */
export interface StoredSession {
  user_id: string
  roles: string[]
  email_verified: boolean
}

export interface AuthUser {
  user_id: string
  email: string
  name?: string | null
  roles: string[]
  email_verified: boolean
  status: string
  created_at: string | null
}
