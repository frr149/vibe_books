import { useEffect } from 'react'

import './App.css'
import { useCatalogStore } from './store/catalog'

function App() {
  const filters = useCatalogStore((state) => state.filters)
  const pagination = useCatalogStore((state) => state.pagination)
  const books = useCatalogStore((state) => state.books)
  const selectedBookId = useCatalogStore((state) => state.selectedBookId)
  const bookDetail = useCatalogStore((state) => state.bookDetail)
  const authors = useCatalogStore((state) => state.authors)
  const genres = useCatalogStore((state) => state.genres)
  const languages = useCatalogStore((state) => state.languages)
  const isLoadingBooks = useCatalogStore((state) => state.isLoadingBooks)
  const isLoadingDetail = useCatalogStore((state) => state.isLoadingDetail)
  const isLoadingTaxonomies = useCatalogStore((state) => state.isLoadingTaxonomies)
  const error = useCatalogStore((state) => state.error)

  const setFilters = useCatalogStore((state) => state.setFilters)
  const setPage = useCatalogStore((state) => state.setPage)
  const setPageSize = useCatalogStore((state) => state.setPageSize)
  const clearError = useCatalogStore((state) => state.clearError)
  const loadBooks = useCatalogStore((state) => state.loadBooks)
  const loadBookDetail = useCatalogStore((state) => state.loadBookDetail)
  const loadTaxonomies = useCatalogStore((state) => state.loadTaxonomies)

  useEffect(() => {
    void loadTaxonomies()
  }, [loadTaxonomies])

  useEffect(() => {
    void loadBooks()
  }, [
    filters.author,
    filters.genre,
    filters.hasIsbn,
    filters.language,
    filters.q,
    loadBooks,
    pagination.page,
    pagination.pageSize,
  ])

  const hasIsbnValue = filters.hasIsbn === null ? 'all' : filters.hasIsbn ? 'yes' : 'no'
  const activeDetail = bookDetail?.id === selectedBookId ? bookDetail : null

  return (
    <main className="catalog-page">
      <header className="page-header">
        <h1>Catalogo de Libros</h1>
        <p>Explora libros, filtra resultados y abre detalles sin recargar la pagina.</p>
      </header>

      {error !== null ? (
        <div className="status status-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={clearError}>
            cerrar
          </button>
        </div>
      ) : null}

      <section className="catalog-layout">
        <aside className="panel panel-filters">
          <h2>Filtros</h2>
          <label>
            Buscar
            <input
              type="search"
              value={filters.q}
              onChange={(event) => {
                setFilters({ q: event.target.value })
              }}
              placeholder="titulo, editorial, isbn..."
            />
          </label>
          <label>
            Idioma
            <select
              value={filters.language}
              onChange={(event) => {
                setFilters({ language: event.target.value })
              }}
            >
              <option value="">Todos</option>
              {languages.map((language) => (
                <option key={language.id} value={language.code}>
                  {language.nombre} ({language.code})
                </option>
              ))}
            </select>
          </label>
          <label>
            Autor
            <select
              value={filters.author}
              onChange={(event) => {
                setFilters({ author: event.target.value })
              }}
            >
              <option value="">Todos</option>
              {authors.map((author) => (
                <option key={author.id} value={author.nombre}>
                  {author.nombre}
                </option>
              ))}
            </select>
          </label>
          <label>
            Genero
            <select
              value={filters.genre}
              onChange={(event) => {
                setFilters({ genre: event.target.value })
              }}
            >
              <option value="">Todos</option>
              {genres.map((genre) => (
                <option key={genre.id} value={genre.nombre}>
                  {genre.nombre}
                </option>
              ))}
            </select>
          </label>
          <label>
            ISBN
            <select
              value={hasIsbnValue}
              onChange={(event) => {
                const next = event.target.value
                setFilters({
                  hasIsbn: next === 'all' ? null : next === 'yes',
                })
              }}
            >
              <option value="all">Todos</option>
              <option value="yes">Con ISBN</option>
              <option value="no">Sin ISBN</option>
            </select>
          </label>
          {isLoadingTaxonomies ? <p className="hint">Cargando taxonomias...</p> : null}
        </aside>

        <section className="panel panel-list">
          <div className="list-header">
            <h2>Listado</h2>
            <div className="pagination-meta">
              <span>
                Pagina {pagination.page} de {Math.max(pagination.totalPages, 1)}
              </span>
              <span>{pagination.total} libros</span>
            </div>
          </div>

          {isLoadingBooks ? <div className="status">Cargando libros...</div> : null}
          {!isLoadingBooks && books.length === 0 ? (
            <div className="status">No hay resultados para los filtros actuales.</div>
          ) : null}
          {!isLoadingBooks && books.length > 0 ? (
            <ul className="book-list">
              {books.map((book) => (
                <li key={book.id}>
                  <button
                    type="button"
                    className={book.id === selectedBookId ? 'book-item is-active' : 'book-item'}
                    onClick={() => {
                      void loadBookDetail(book.id)
                    }}
                  >
                    <span className="book-title">{book.titulo}</span>
                    <span className="book-meta">{book.editorial ?? 'Editorial desconocida'}</span>
                    <span className="book-meta">
                      {book.idioma} | {book.isbn_13 ?? book.isbn_10 ?? 'sin isbn'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          <div className="pagination-controls">
            <button
              type="button"
              onClick={() => {
                setPage(Math.max(1, pagination.page - 1))
              }}
              disabled={pagination.page <= 1}
            >
              anterior
            </button>
            <button
              type="button"
              onClick={() => {
                setPage(Math.min(Math.max(1, pagination.totalPages), pagination.page + 1))
              }}
              disabled={pagination.page >= pagination.totalPages}
            >
              siguiente
            </button>
            <label>
              tamano
              <select
                value={pagination.pageSize}
                onChange={(event) => {
                  setPageSize(Number(event.target.value))
                }}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </label>
          </div>
        </section>

        <aside className="panel panel-detail">
          <h2>Detalle</h2>
          {selectedBookId === null ? (
            <div className="status">Selecciona un libro para ver su detalle.</div>
          ) : null}
          {selectedBookId !== null && isLoadingDetail && activeDetail === null ? (
            <div className="status">Cargando detalle...</div>
          ) : null}
          {selectedBookId !== null && !isLoadingDetail && activeDetail === null ? (
            <div className="status">No se pudo cargar el detalle.</div>
          ) : null}
          {activeDetail !== null ? (
            <article className="detail-content">
              <h3>{activeDetail.titulo}</h3>
              {activeDetail.cover_url !== null ? (
                <img src={activeDetail.cover_url} alt={`Portada de ${activeDetail.titulo}`} />
              ) : null}
              <p>
                <strong>Editorial:</strong> {activeDetail.editorial ?? 'desconocida'}
              </p>
              <p>
                <strong>Idioma:</strong> {activeDetail.language.nombre} ({activeDetail.language.code})
              </p>
              <p>
                <strong>ISBN-13:</strong> {activeDetail.isbn_13 ?? 'sin isbn'}
              </p>
              <p>
                <strong>ISBN-10:</strong> {activeDetail.isbn_10 ?? 'sin isbn'}
              </p>
              <p>
                <strong>Autores:</strong>{' '}
                {activeDetail.authors.length > 0
                  ? activeDetail.authors.map((author) => author.nombre).join(', ')
                  : 'sin autores'}
              </p>
              <p>
                <strong>Generos:</strong>{' '}
                {activeDetail.genres.length > 0
                  ? activeDetail.genres.map((genre) => genre.nombre).join(', ')
                  : 'sin generos'}
              </p>
            </article>
          ) : null}
        </aside>
      </section>
    </main>
  )
}

export default App
