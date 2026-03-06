import { useStore } from 'zustand'
import { createStore, type StateCreator, type StoreApi } from 'zustand/vanilla'

import { ApiClientError, requestJson } from '../api/client'
import { API_BASE_URL } from '../api/config'
import {
  AuthorListResponseSchema,
  BookDetailSchema,
  BookListResponseSchema,
  GenreListResponseSchema,
  LanguageListResponseSchema,
  type Author,
  type BookDetail,
  type BookListItem,
  type BookListResponse,
  type Genre,
  type Language,
} from '../api/schemas'

const DEFAULT_PAGE = 1
const DEFAULT_PAGE_SIZE = 20

export type CatalogFilters = {
  q: string
  language: string
  author: string
  genre: string
  hasIsbn: boolean | null
}

export type CatalogPagination = {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export type CatalogState = {
  filters: CatalogFilters
  pagination: CatalogPagination
  books: BookListItem[]
  selectedBookId: number | null
  bookDetail: BookDetail | null
  authors: Author[]
  genres: Genre[]
  languages: Language[]
  isLoadingBooks: boolean
  isLoadingDetail: boolean
  isLoadingTaxonomies: boolean
  error: string | null
}

export type CatalogActions = {
  setFilters: (patch: Partial<CatalogFilters>) => void
  setPage: (page: number) => void
  setPageSize: (pageSize: number) => void
  clearError: () => void
  loadBooks: () => Promise<void>
  loadBookDetail: (bookId: number) => Promise<void>
  loadTaxonomies: () => Promise<void>
}

export type CatalogStore = CatalogState & CatalogActions

function emptyFilters(): CatalogFilters {
  return {
    q: '',
    language: '',
    author: '',
    genre: '',
    hasIsbn: null,
  }
}

function normalizeText(value: string): string {
  return value.trim()
}

function buildBooksPath(filters: CatalogFilters, pagination: CatalogPagination): string {
  const params = new URLSearchParams()
  params.set('page', String(pagination.page))
  params.set('page_size', String(pagination.pageSize))

  const q = normalizeText(filters.q)
  const language = normalizeText(filters.language)
  const author = normalizeText(filters.author)
  const genre = normalizeText(filters.genre)

  if (q !== '') {
    params.set('q', q)
  }
  if (language !== '') {
    params.set('language', language)
  }
  if (author !== '') {
    params.set('author', author)
  }
  if (genre !== '') {
    params.set('genre', genre)
  }
  if (filters.hasIsbn !== null) {
    params.set('has_isbn', String(filters.hasIsbn))
  }
  return `/api/v1/books?${params.toString()}`
}

function toPaginationFromApi(payload: BookListResponse): CatalogPagination {
  return {
    page: payload.pagination.page,
    pageSize: payload.pagination.page_size,
    total: payload.pagination.total,
    totalPages: payload.pagination.total_pages,
  }
}

function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError) {
    return `${error.code}: ${error.message}`
  }
  return fallback
}

const createCatalogState: StateCreator<CatalogStore> = (set, get) => {
  const booksCache = new Map<string, BookListResponse>()
  const detailsCache = new Map<number, BookDetail>()
  let taxonomiesLoaded = false

  return {
    filters: emptyFilters(),
    pagination: {
      page: DEFAULT_PAGE,
      pageSize: DEFAULT_PAGE_SIZE,
      total: 0,
      totalPages: 0,
    },
    books: [],
    selectedBookId: null,
    bookDetail: null,
    authors: [],
    genres: [],
    languages: [],
    isLoadingBooks: false,
    isLoadingDetail: false,
    isLoadingTaxonomies: false,
    error: null,

    setFilters: (patch) => {
      set((state) => ({
        filters: {
          ...state.filters,
          ...patch,
        },
        pagination: {
          ...state.pagination,
          page: DEFAULT_PAGE,
        },
      }))
    },

    setPage: (page) => {
      set((state) => ({
        pagination: {
          ...state.pagination,
          page,
        },
      }))
    },

    setPageSize: (pageSize) => {
      set((state) => ({
        pagination: {
          ...state.pagination,
          pageSize,
          page: DEFAULT_PAGE,
        },
      }))
    },

    clearError: () => {
      set({ error: null })
    },

    loadBooks: async () => {
      const state = get()
      const path = buildBooksPath(state.filters, state.pagination)
      const cached = booksCache.get(path)
      if (cached !== undefined) {
        set({
          books: cached.items,
          pagination: toPaginationFromApi(cached),
          isLoadingBooks: false,
          error: null,
        })
        return
      }

      set({
        isLoadingBooks: true,
        error: null,
      })
      try {
        const payload = await requestJson({
          baseUrl: API_BASE_URL,
          path,
          schema: BookListResponseSchema,
        })
        booksCache.set(path, payload)
        set({
          books: payload.items,
          pagination: toPaginationFromApi(payload),
          isLoadingBooks: false,
          error: null,
        })
      } catch (error: unknown) {
        set({
          isLoadingBooks: false,
          error: toErrorMessage(error, 'No se pudo cargar el catalogo'),
        })
      }
    },

    loadBookDetail: async (bookId) => {
      set({
        selectedBookId: bookId,
      })
      const cached = detailsCache.get(bookId)
      if (cached !== undefined) {
        set({
          bookDetail: cached,
          isLoadingDetail: false,
          error: null,
        })
        return
      }

      set({
        isLoadingDetail: true,
        error: null,
      })
      try {
        const payload = await requestJson({
          baseUrl: API_BASE_URL,
          path: `/api/v1/books/${bookId}`,
          schema: BookDetailSchema,
        })
        detailsCache.set(bookId, payload)
        set({
          bookDetail: payload,
          isLoadingDetail: false,
          error: null,
        })
      } catch (error: unknown) {
        set({
          isLoadingDetail: false,
          error: toErrorMessage(error, 'No se pudo cargar el detalle del libro'),
        })
      }
    },

    loadTaxonomies: async () => {
      if (taxonomiesLoaded) {
        return
      }
      set({
        isLoadingTaxonomies: true,
        error: null,
      })
      try {
        const [authors, genres, languages] = await Promise.all([
          requestJson({
            baseUrl: API_BASE_URL,
            path: '/api/v1/authors',
            schema: AuthorListResponseSchema,
          }),
          requestJson({
            baseUrl: API_BASE_URL,
            path: '/api/v1/genres',
            schema: GenreListResponseSchema,
          }),
          requestJson({
            baseUrl: API_BASE_URL,
            path: '/api/v1/languages',
            schema: LanguageListResponseSchema,
          }),
        ])
        taxonomiesLoaded = true
        set({
          authors: authors.items,
          genres: genres.items,
          languages: languages.items,
          isLoadingTaxonomies: false,
          error: null,
        })
      } catch (error: unknown) {
        set({
          isLoadingTaxonomies: false,
          error: toErrorMessage(error, 'No se pudieron cargar las taxonomias'),
        })
      }
    },
  }
}

export function createCatalogStore(): StoreApi<CatalogStore> {
  return createStore<CatalogStore>(createCatalogState)
}

export const catalogStore = createCatalogStore()

export function useCatalogStore<T>(selector: (state: CatalogStore) => T): T {
  return useStore(catalogStore, selector)
}
