import { type ZodType } from 'zod'

import { ApiErrorEnvelopeSchema } from './schemas'

type RequestJsonParams<T> = {
  baseUrl: string
  path: string
  schema: ZodType<T>
  timeoutMs?: number
  init?: RequestInit
}

type ApiClientErrorParams = {
  code: string
  message: string
  status: number
  details?: Record<string, unknown>
}

const DEFAULT_TIMEOUT_MS = 8_000

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '')
}

function normalizePath(path: string): string {
  if (path.startsWith('/')) {
    return path
  }
  return `/${path}`
}

function buildUrl(baseUrl: string, path: string): string {
  return `${normalizeBaseUrl(baseUrl)}${normalizePath(path)}`
}

export class ApiClientError extends Error {
  readonly code: string
  readonly status: number
  readonly details?: Record<string, unknown>

  constructor(params: ApiClientErrorParams) {
    super(params.message)
    this.name = 'ApiClientError'
    this.code = params.code
    this.status = params.status
    this.details = params.details
  }
}

async function parseJsonSafe(response: Response): Promise<unknown> {
  const text = await response.text()
  if (text.trim() === '') {
    return {}
  }
  try {
    return JSON.parse(text) as unknown
  } catch {
    return {}
  }
}

export async function requestJson<T>(params: RequestJsonParams<T>): Promise<T> {
  const timeoutMs = params.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const requestInit: RequestInit = {
    ...params.init,
    signal: AbortSignal.timeout(timeoutMs),
    headers: {
      accept: 'application/json',
      ...(params.init?.headers ?? {}),
    },
  }
  const url = buildUrl(params.baseUrl, params.path)

  let response: Response
  try {
    response = await fetch(url, requestInit)
  } catch {
    throw new ApiClientError({
      code: 'network_error',
      message: 'No se pudo conectar con la API',
      status: 0,
    })
  }

  const payload = await parseJsonSafe(response)
  if (!response.ok) {
    const parsedError = ApiErrorEnvelopeSchema.safeParse(payload)
    if (parsedError.success) {
      throw new ApiClientError({
        code: parsedError.data.error.code,
        message: parsedError.data.error.message,
        details: parsedError.data.error.details,
        status: response.status,
      })
    }
    throw new ApiClientError({
      code: 'http_error',
      message: `HTTP ${response.status}`,
      status: response.status,
    })
  }

  const parsed = params.schema.safeParse(payload)
  if (!parsed.success) {
    throw new ApiClientError({
      code: 'invalid_response',
      message: 'La respuesta no cumple el contrato esperado',
      status: response.status,
      details: { issues: parsed.error.issues },
    })
  }
  return parsed.data
}
