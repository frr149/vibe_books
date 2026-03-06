# Proveniencia de Fixtures Reales (API)

Estos fixtures NO se escriben a mano.

Origen:
- Base SQLite local: `data/books_catalog.db`
- Script de captura/export: `scripts/export_api_fixtures.py`

Regeneración:
```bash
just export-api-fixtures
```

Archivos esperados:
- `book_detail_full.json`
- `book_detail_sparse.json`
- `books_list_page1.json`
