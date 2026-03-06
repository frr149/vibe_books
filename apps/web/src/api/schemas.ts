import { z } from 'zod'

export const AuthorSchema = z
  .object({
    id: z.number().int(),
    nombre: z.string(),
    slug: z.string(),
    book_count: z.number().int(),
  })
  .strict()

export const GenreSchema = z
  .object({
    id: z.number().int(),
    nombre: z.string(),
    slug: z.string(),
    book_count: z.number().int(),
  })
  .strict()

export const LanguageSchema = z
  .object({
    id: z.number().int(),
    code: z.string(),
    nombre: z.string(),
  })
  .strict()

export const BookListItemSchema = z
  .object({
    id: z.number().int(),
    titulo: z.string(),
    editorial: z.string().nullable(),
    idioma: z.string(),
    isbn_13: z.string().nullable(),
    isbn_10: z.string().nullable(),
    cover_url: z.string().nullable(),
  })
  .strict()

export const PaginationSchema = z
  .object({
    page: z.number().int(),
    page_size: z.number().int(),
    total: z.number().int(),
    total_pages: z.number().int(),
  })
  .strict()

export const BookListResponseSchema = z
  .object({
    items: z.array(BookListItemSchema),
    pagination: PaginationSchema,
  })
  .strict()

export const BookDetailSchema = z
  .object({
    id: z.number().int(),
    titulo: z.string(),
    editorial: z.string().nullable(),
    idioma: z.string(),
    isbn_13: z.string().nullable(),
    isbn_10: z.string().nullable(),
    cover_url: z.string().nullable(),
    cover_local_path: z.string().nullable(),
    authors: z.array(AuthorSchema),
    genres: z.array(GenreSchema),
    language: LanguageSchema,
  })
  .strict()

export const AuthorListResponseSchema = z
  .object({
    items: z.array(AuthorSchema),
  })
  .strict()

export const GenreListResponseSchema = z
  .object({
    items: z.array(GenreSchema),
  })
  .strict()

export const LanguageListResponseSchema = z
  .object({
    items: z.array(LanguageSchema),
  })
  .strict()

export const ApiErrorEnvelopeSchema = z
  .object({
    error: z
      .object({
        code: z.string(),
        message: z.string(),
        details: z.record(z.string(), z.unknown()).optional(),
      })
      .strict(),
  })
  .strict()

export type BookListResponse = z.infer<typeof BookListResponseSchema>
export type BookDetail = z.infer<typeof BookDetailSchema>
export type AuthorListResponse = z.infer<typeof AuthorListResponseSchema>
export type GenreListResponse = z.infer<typeof GenreListResponseSchema>
export type LanguageListResponse = z.infer<typeof LanguageListResponseSchema>
export type BookListItem = z.infer<typeof BookListItemSchema>
export type Author = z.infer<typeof AuthorSchema>
export type Genre = z.infer<typeof GenreSchema>
export type Language = z.infer<typeof LanguageSchema>
