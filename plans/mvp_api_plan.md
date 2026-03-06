# Plan MVP API REST para Catálogo de Libros

## Objetivo
Publicar una API REST mínima, estable y verificable de forma autónoma (sin frontend), usando `data/books_catalog.db` como fuente.

## Alcance MVP
- API de solo lectura (sin crear/editar/borrar libros).
- Versionado base: `/api/v1`.
- Respuestas JSON con paginación y errores consistentes.

## Endpoints mínimos y por qué
1. `GET /api/v1/health`
   - Para comprobar disponibilidad de la API y de la conexión SQLite.
2. `GET /api/v1/books`
   - Endpoint principal de listado para el catálogo.
   - Soporta `page`, `page_size`, `q`, `language`, `author`, `genre`, `has_isbn`.
   - Opcionalmente puede aceptar `author_id` y `genre_id` para clientes internos o casos de rendimiento.
3. `GET /api/v1/books/{book_id}`
   - Vista de detalle (incluye autores, géneros, idioma y portadas).
4. `GET /api/v1/authors`
   - Poblar filtros/facetas del frontend y navegación por autor.
   - Debe devolver al menos: `id`, `nombre`, `slug`/`nombre_norm`, `book_count`.
5. `GET /api/v1/genres`
   - Poblar filtros por género y navegación temática.
   - Debe devolver al menos: `id`, `nombre`, `slug`/`nombre_norm`, `book_count`.
6. `GET /api/v1/languages`
   - Poblar selector de idioma desde catálogo normalizado (`languages`).

## Modelo de respuesta (MVP)
- Listados: `{items: [...], pagination: {page, page_size, total, total_pages}}`
- Errores: `{error: {code, message, details?}}`

## Fases de implementación
### Fase 0: Walking Skeleton (arranque técnico)
1. Instalar dependencias backend con `uv`:
   - runtime: `fastapi`, `uvicorn`.
   - test: `pytest`, `httpx`.
2. Crear app mínima FastAPI con estructura base y router versionado `/api/v1`.
3. Implementar endpoint mínimo `GET /api/v1/health`.
4. Añadir ejecución local y receta `just` para levantar la API.
5. Crear primer test de endpoint (`health`) para validar que el esqueleto funciona extremo a extremo.

### Fase 1: Contrato y base API
1. Definir esquemas Pydantic de `BookListItem`, `BookDetail`, `Author`, `Genre`, `Language`.
2. Definir convención de errores y límites de paginación.
3. Definir política de identificadores públicos:
   - IDs expuestos en API se consideran estables a nivel de contrato.
   - Filtros legibles (`author`, `genre`) disponibles para no obligar al cliente a conocer IDs.
4. Crear capa de acceso SQLite (queries parametrizadas).

### Fase 2: Catálogo de libros
1. Implementar `GET /api/v1/books` con filtros y paginación.
2. Implementar `GET /api/v1/books/{book_id}`.
3. Añadir índices SQL faltantes si alguna query crítica supera latencia objetivo.

### Fase 3: Taxonomías
1. Implementar `GET /api/v1/authors`.
2. Implementar `GET /api/v1/genres`.
3. Implementar `GET /api/v1/languages`.

### Fase 4: Calidad y operativa
1. Tests de integración de endpoints (casos felices + errores).
2. Documentación OpenAPI revisada (`/docs`).
3. Añadir receta `just` para comprobar que no hay endpoints rotos en la API publicada localmente.
4. Añadir receta `just api-test` para ejecutar solo la batería de tests de API.

## Recetas `just` objetivo para API MVP
1. `just api-dev`
   - Levanta servidor local (`uvicorn`) para desarrollo.
2. `just api-test`
   - Ejecuta tests de endpoints de la API.
3. `just api-check-links`
   - Valida endpoints críticos del servicio (`/api/v1/health`, `/openapi.json`, `/docs`, `/api/v1/books`, etc.).

## Estrategia de validación autónoma (sin frontend)
1. Validación funcional del API:
   - Tests de integración (`pytest` + cliente HTTP) para contrato, filtros, paginación y errores.
2. Smoke checks del servicio en ejecución local:
   - `just api-check-links` para confirmar que endpoints críticos responden `2xx`.
3. Regla de decisión:
   - Sin frontend, se priorizan tests HTTP + smoke checks de endpoints.

## Criterios de aceptación del MVP
1. La API responde correctamente sin depender de frontend.
2. Los 6 endpoints mínimos están implementados y cubiertos por tests de integración.
3. Paginación, filtros y formato de errores son consistentes y verificables por tests.
4. `just api-check-links` pasa en local (sin endpoints rotos en superficie API).
5. OpenAPI (`/openapi.json`) refleja el contrato real de los endpoints.

## Para más tarde (post-MVP)
- Validar enlaces de documentación con `lychee`.
- Checklist de rendimiento básico y observabilidad mínima (logs de request).

## Fuera de alcance (por ahora)
- Autenticación/autorización.
- Escrituras (`POST`, `PUT`, `DELETE`).
- Búsqueda full-text avanzada y recomendaciones.
