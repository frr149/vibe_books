import { describe, expect, it } from 'vitest'

import {
  ApiErrorEnvelopeSchema,
  AuthorListResponseSchema,
  BookDetailSchema,
  BookListResponseSchema,
  GenreListResponseSchema,
  LanguageListResponseSchema,
} from '../schemas'

describe('schemas de API', () => {
  it('valida la respuesta de listado de libros', () => {
    const payload = {
      items: [
        {
          id: 1,
          titulo: 'Deep Learning with Python',
          editorial: 'Manning',
          idioma: 'ingles',
          isbn_13: '9781617296864',
          isbn_10: '1617296864',
          cover_url: null,
        },
      ],
      pagination: {
        page: 1,
        page_size: 20,
        total: 1,
        total_pages: 1,
      },
    }

    const parsed = BookListResponseSchema.parse(payload)
    expect(parsed.items).toHaveLength(1)
    expect(parsed.items[0]?.id).toBe(1)
  })

  it('rechaza campos fantasma en book detail', () => {
    const payload = {
      id: 1,
      titulo: 'Deep Learning with Python',
      editorial: 'Manning',
      idioma: 'ingles',
      isbn_13: '9781617296864',
      isbn_10: '1617296864',
      cover_url: null,
      cover_local_path: null,
      authors: [
        { id: 10, nombre: 'Francois Chollet', slug: 'francois-chollet', book_count: 2 },
      ],
      genres: [
        { id: 3, nombre: 'Programacion', slug: 'programacion', book_count: 31 },
      ],
      language: { id: 1, code: 'en', nombre: 'ingles' },
      phantom: 'no_deberia_existir',
    }

    expect(() => BookDetailSchema.parse(payload)).toThrow()
  })

  it('valida taxonomias y envelope de error', () => {
    expect(
      AuthorListResponseSchema.parse({
        items: [{ id: 1, nombre: 'Autor', slug: 'autor', book_count: 3 }],
      }),
    ).toBeDefined()
    expect(
      GenreListResponseSchema.parse({
        items: [{ id: 1, nombre: 'Genero', slug: 'genero', book_count: 5 }],
      }),
    ).toBeDefined()
    expect(
      LanguageListResponseSchema.parse({
        items: [{ id: 1, code: 'en', nombre: 'ingles' }],
      }),
    ).toBeDefined()
    expect(
      ApiErrorEnvelopeSchema.parse({
        error: { code: 'invalid_query', message: 'Parametro invalido' },
      }),
    ).toBeDefined()
  })
})
