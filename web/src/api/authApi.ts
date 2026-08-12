/**
 * Cliente de la API de osap-auth. Los componentes NO llaman a fetch directamente;
 * usan estas funciones.
 */

import { httpClient } from './httpClient'
import type {
  CompleteAuthorizationInput,
  CompleteAuthorizationResponse,
  LoginResponse,
  MessageResponse,
  RegisterResponse,
  SessionInfo,
  SocialProvidersResponse,
  UserMe,
} from './types'

export interface RegisterInput {
  email: string
  password: string
  name?: string
}

export const authApi = {
  register(input: RegisterInput): Promise<RegisterResponse> {
    return httpClient.post<RegisterResponse>('/auth/register', input)
  },
  verifyEmail(token: string): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/verify-email', { token })
  },
  resendVerification(email: string): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/resend-verification', { email })
  },
  login(email: string, password: string): Promise<LoginResponse> {
    return httpClient.post<LoginResponse>('/auth/login', { email, password })
  },
  completeAuthorization(input: CompleteAuthorizationInput): Promise<CompleteAuthorizationResponse> {
    return httpClient.post<CompleteAuthorizationResponse>('/auth/authorize/complete', input)
  },
  getSocialProviders(): Promise<SocialProvidersResponse> {
    return httpClient.get<SocialProvidersResponse>('/auth/oauth/providers')
  },
  refresh(refreshToken: string): Promise<LoginResponse> {
    return httpClient.post<LoginResponse>('/auth/refresh', { refresh_token: refreshToken })
  },
  logout(): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/logout')
  },
  logoutAll(): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/logout-all')
  },
  getSessions(): Promise<SessionInfo[]> {
    return httpClient.get<SessionInfo[]>('/auth/sessions')
  },
  revokeSession(id: string): Promise<MessageResponse> {
    return httpClient.delete<MessageResponse>(`/auth/sessions/${id}`)
  },
  getMe(): Promise<UserMe> {
    return httpClient.get<UserMe>('/auth/me')
  },
  changePassword(currentPassword: string, newPassword: string): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/me/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },
  requestPasswordReset(email: string): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/password-reset/request', { email })
  },
  confirmPasswordReset(token: string, newPassword: string): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/password-reset/confirm', {
      token,
      new_password: newPassword,
    })
  },
  changeEmail(email: string): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/me/email', { email })
  },
  confirmChangeEmail(token: string): Promise<MessageResponse> {
    return httpClient.post<MessageResponse>('/auth/change-email/confirm', { token })
  },
  deleteAccount(): Promise<MessageResponse> {
    return httpClient.delete<MessageResponse>('/auth/me')
  },
  adminListUsers(): Promise<UserMe[]> {
    return httpClient.get<UserMe[]>('/auth/admin/users')
  },
  adminGetUser(id: string): Promise<UserMe> {
    return httpClient.get<UserMe>(`/auth/admin/users/${id}`)
  },
  adminCreateUser(input: {
    email: string
    password: string
    name?: string
    roles: string[]
  }): Promise<UserMe> {
    return httpClient.post<UserMe>('/auth/admin/users', input)
  },
  adminUpdateUser(
    id: string,
    input: { name?: string | null; roles?: string[]; status?: string },
  ): Promise<UserMe> {
    return httpClient.patch<UserMe>(`/auth/admin/users/${id}`, input)
  },
  adminDeleteUser(id: string): Promise<MessageResponse> {
    return httpClient.delete<MessageResponse>(`/auth/admin/users/${id}`)
  },
}
