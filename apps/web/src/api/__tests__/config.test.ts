import { describe, expect, it } from 'vitest'

import { DEFAULT_API_BASE_URL, resolveApiBaseUrl } from '../config'

describe('resolveApiBaseUrl', () => {
  it('usa el default cuando no hay variable de entorno', () => {
    expect(resolveApiBaseUrl(undefined)).toBe(DEFAULT_API_BASE_URL)
    expect(resolveApiBaseUrl('')).toBe(DEFAULT_API_BASE_URL)
    expect(resolveApiBaseUrl('   ')).toBe(DEFAULT_API_BASE_URL)
  })

  it('normaliza slash final', () => {
    expect(resolveApiBaseUrl('http://127.0.0.1:8000/')).toBe('http://127.0.0.1:8000')
    expect(resolveApiBaseUrl('https://api.example.test////')).toBe('https://api.example.test')
  })
})
