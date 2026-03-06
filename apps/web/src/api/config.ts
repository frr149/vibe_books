export const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

export function resolveApiBaseUrl(rawValue: string | undefined): string {
  const cleaned = rawValue?.trim() ?? ''
  if (cleaned === '') {
    return DEFAULT_API_BASE_URL
  }
  return cleaned.replace(/\/+$/, '')
}

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL)
