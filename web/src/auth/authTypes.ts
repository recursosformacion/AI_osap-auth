export type AuthStatus = 'anonymous' | 'authenticated' | 'loading'

/** Información mínima de sesión persistida (sin PII como el email). */
export interface StoredSession {
  user_id: string
  roles: string[]
  email_verified: boolean
}

import type { MembershipInfo, OnboardingState } from '../api/types'

export interface AuthUser {
  user_id: string
  email: string
  name?: string | null
  nickname?: string | null
  phone?: string | null
  roles: string[]
  email_verified: boolean
  status: string
  created_at: string | null
  onboarding?: OnboardingState | null
  nickname_public_consent?: boolean
  news_opt_in?: boolean
  news_language?: string
  news_languages?: string[]
  news_topics?: string[]
  memberships?: MembershipInfo[]
}
