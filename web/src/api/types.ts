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

/** Parámetros OIDC que el SPA devuelve al completar la autorización (flujo embebido). */
export interface CompleteAuthorizationInput {
  client_id: string
  redirect_uri: string
  response_type?: string
  scope?: string
  state?: string | null
  nonce?: string | null
  code_challenge?: string | null
  code_challenge_method?: string | null
}

export interface CompleteAuthorizationResponse {
  redirect_uri: string
  code: string
  state?: string | null
}

export interface SocialProvidersResponse {
  providers: string[]
}

/** Error normalizado del cliente HTTP. */
export interface HttpError {
  status: number
  message: string
}
