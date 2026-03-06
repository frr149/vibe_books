# Plan MVP Frontend (SPA) para Catálogo de Libros

## Objetivo
Construir un frontend web SPA para consumir la API actual del catálogo (`/api/v1/*`) con una base simple y escalable.

## Stack acordado
- `Vite + React + TypeScript`
- `Zustand` (estado global)
- `Zod` (validación de contratos API)
- `Tailwind CSS` (estilos)
- Runtime JS: `Node` (recomendado `22 LTS`)
- Gestor recomendado: `pnpm` (fallback: `npm`)

## Fase 0: Walking Skeleton (entorno + arranque)
1. Verificar prerequisitos locales:
   - `node -v` (objetivo: Node 22 LTS)
   - `pnpm -v` (o `npm -v`)
2. Crear `apps/web` con plantilla Vite React TS.
3. Añadir receta `just web-check-env` para validar prerequisitos.
4. Añadir receta `just web-dev` para levantar frontend local.
5. Probar arranque local contra API activa.

Criterio de aceptación:
- `just web-check-env` pasa.
- `just web-dev` arranca la SPA.

## Fase 1: Contrato API tipado
1. Implementar cliente HTTP con `fetch` (timeout + manejo de errores).
2. Definir esquemas `zod` para:
   - `GET /api/v1/books`
   - `GET /api/v1/books/{id}`
   - `GET /api/v1/authors`
   - `GET /api/v1/genres`
   - `GET /api/v1/languages`
   - error envelope `{error:{code,message,details?}}`
3. Configurar `VITE_API_BASE_URL`.

Criterio de aceptación:
- Todas las respuestas usadas por la app se validan por `zod`.
- Errores de contrato se muestran de forma controlada.

## Fase 2: Estado global con Zustand
1. Store de catálogo:
   - filtros (`q`, `language`, `author`, `genre`, `has_isbn`)
   - paginación
   - listado
   - detalle seleccionado
   - taxonomías
2. Acciones async:
   - `loadBooks`
   - `loadBookDetail`
   - `loadTaxonomies`
3. Caché básica en memoria por query-key.

Criterio de aceptación:
- Flujo de datos consistente y predecible.

## Fase 3: UI MVP SPA
1. Pantalla única con:
   - panel de filtros
   - listado paginado de libros
   - panel de detalle
2. Estados UI:
   - `loading`
   - `empty`
   - `error`

Criterio de aceptación:
- Se puede explorar catálogo completo sin recargar página.

## Fase 4: Calidad (sin lychee)
1. Tests unitarios de cliente/store.
2. Tests de componentes críticos.
3. Recetas `just`:
   - `web-test`
   - `web-lint`
   - `web-build`
4. Smoke funcional contra API local.

Criterio de aceptación:
- `just web-test`, `just web-lint` y `just web-build` en verde.

## Fase 5: Preparado para crecer
1. Estructura modular:
   - `features/catalog`
   - `shared/api`
   - `shared/ui`
2. Dejar base lista para introducir routing real más adelante sin refactor grande.

Criterio de aceptación:
- Nueva funcionalidad se añade sin romper arquitectura base.
