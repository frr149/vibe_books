import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'

import { requestJson } from '../client'

const SimpleSchema = z.object({
  ok: z.boolean(),
}).strict()

describe('requestJson', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('devuelve payload validado cuando la respuesta es 2xx', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const result = await requestJson({
      baseUrl: 'http://127.0.0.1:8000',
      path: '/api/v1/health',
      schema: SimpleSchema,
      timeoutMs: 1500,
    })

    expect(result).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('lanza ApiClientError con el code del backend para 4xx/5xx', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: 'invalid_query', message: 'Parametro invalido' },
        }),
        {
          status: 422,
          headers: { 'content-type': 'application/json' },
        },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      requestJson({
        baseUrl: 'http://127.0.0.1:8000',
        path: '/api/v1/books',
        schema: SimpleSchema,
      }),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      code: 'invalid_query',
      status: 422,
    })
  })

  it('lanza invalid_response si el JSON no cumple el schema esperado', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ unexpected: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      requestJson({
        baseUrl: 'http://127.0.0.1:8000',
        path: '/api/v1/books',
        schema: SimpleSchema,
      }),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      code: 'invalid_response',
      status: 200,
    })
  })

  it('lanza network_error cuando fetch falla', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('network down'))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      requestJson({
        baseUrl: 'http://127.0.0.1:8000',
        path: '/api/v1/books',
        schema: SimpleSchema,
      }),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      code: 'network_error',
      status: 0,
    })
  })
})
