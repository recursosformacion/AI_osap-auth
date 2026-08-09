/** Tipos de la API pública de osap-auth (contrato osap-auth-api-v1.0). */

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user_id: string
  roles: string[]
  email_verified: boolean
}

export interface RegisterResponse {
  user_id?: string | null
  verification_token?: string | null
  message: string
}

export interface MessageResponse {
  message: string
}

export interface UserMe {
  user_id: string
  email: string
  name?: string | null
  roles: string[]
  email_verified: boolean
  status: string
  created_at: string | null
}

export interface SessionInfo {
  id: string
  created_at: string
  last_used_at: string
  revoked: boolean
  ip?: string | null
  user_agent?: string | null
  device_label?: string | null
}

export interface ApiErrorDetail {
  detail?: string
}

/** Error normalizado del cliente HTTP. */
export interface HttpError {
  status: number
  message: string
}
