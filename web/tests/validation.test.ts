import { describe, expect, it } from 'vitest'

import { isValidEmail, passwordMessage } from '../src/utils/validation'

describe('validation', () => {
  it('valida emails', () => {
    expect(isValidEmail('a@b.com')).toBe(true)
    expect(isValidEmail('not-an-email')).toBe(false)
    expect(isValidEmail('')).toBe(false)
  })

  it('valida longitud de contraseña', () => {
    expect(passwordMessage('short')).toBeTruthy()
    expect(passwordMessage('01234567')).toBeNull()
    expect(passwordMessage('con-8-caracteres')).toBeNull()
  })
})
