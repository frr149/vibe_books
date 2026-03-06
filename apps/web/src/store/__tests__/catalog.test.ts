import { beforeEach, describe, expect, it, vi } from 'vitest'

import { requestJson } from '../../api/client'
import { createCatalogStore } from '../catalog'

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return {
    ...actual,
    requestJson: vi.fn(),
  }
})

const requestJsonMock = vi.mocked(requestJson)

describe('catalog store', () => {
  beforeEach(() => {
    requestJsonMock.mockReset()
  })

  it('carga libros y reutiliza cache para misma query', async () => {
    requestJsonMock.mockResolvedValueOnce({
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
    })

    const store = createCatalogStore()
    await store.getState().loadBooks()
    await store.getState().loadBooks()

    expect(requestJsonMock).toHaveBeenCalledTimes(1)
    expect(store.getState().books).toHaveLength(1)
    expect(store.getState().pagination.total).toBe(1)
  })

  it('setFilters actualiza filtros y reinicia pagina a 1', () => {
    const store = createCatalogStore()
    store.getState().setPage(3)
    store.getState().setFilters({ q: 'python', language: 'ingles' })

    const state = store.getState()
    expect(state.filters.q).toBe('python')
    expect(state.filters.language).toBe('ingles')
    expect(state.pagination.page).toBe(1)
  })

  it('carga detalle y reutiliza cache por id', async () => {
    requestJsonMock.mockResolvedValueOnce({
      id: 1,
      titulo: 'Deep Learning with Python',
      editorial: 'Manning',
      idioma: 'ingles',
      isbn_13: '9781617296864',
      isbn_10: '1617296864',
      cover_url: null,
      cover_local_path: null,
      authors: [{ id: 10, nombre: 'Francois Chollet', slug: 'francois-chollet', book_count: 2 }],
      genres: [{ id: 3, nombre: 'Programacion', slug: 'programacion', book_count: 31 }],
      language: { id: 1, code: 'en', nombre: 'ingles' },
    })

    const store = createCatalogStore()
    await store.getState().loadBookDetail(1)
    await store.getState().loadBookDetail(1)

    expect(requestJsonMock).toHaveBeenCalledTimes(1)
    expect(store.getState().selectedBookId).toBe(1)
    expect(store.getState().bookDetail?.id).toBe(1)
  })

  it('carga taxonomias una vez y luego usa cache local', async () => {
    requestJsonMock.mockImplementation(async (params) => {
      if (params.path === '/api/v1/authors') {
        return {
          items: [{ id: 10, nombre: 'Francois Chollet', slug: 'francois-chollet', book_count: 2 }],
        }
      }
      if (params.path === '/api/v1/genres') {
        return {
          items: [{ id: 3, nombre: 'Programacion', slug: 'programacion', book_count: 31 }],
        }
      }
      if (params.path === '/api/v1/languages') {
        return {
          items: [{ id: 1, code: 'en', nombre: 'ingles' }],
        }
      }
      throw new Error(`unexpected path: ${params.path}`)
    })

    const store = createCatalogStore()
    await store.getState().loadTaxonomies()
    await store.getState().loadTaxonomies()

    expect(requestJsonMock).toHaveBeenCalledTimes(3)
    expect(store.getState().authors).toHaveLength(1)
    expect(store.getState().genres).toHaveLength(1)
    expect(store.getState().languages).toHaveLength(1)
  })

  it('expone error controlado cuando falla la carga de libros', async () => {
    requestJsonMock.mockRejectedValueOnce(new Error('boom'))

    const store = createCatalogStore()
    await store.getState().loadBooks()

    expect(store.getState().error).toBe('No se pudo cargar el catalogo')
    expect(store.getState().isLoadingBooks).toBe(false)
  })
})
