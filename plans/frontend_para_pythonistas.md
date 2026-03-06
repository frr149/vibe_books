# Frontend para Pythonistas (guia rapida)

Guia corta para entender el stack frontend del proyecto usando analogias con Python.

## Equivalencias directas

- `Node` = runtime, como `python`.
- `pnpm`/`npm` = gestor de paquetes, como `uv`/`pip`.
- `package.json` = `pyproject.toml`.
- `node_modules` = paquetes instalados en `.venv` (`site-packages`).
- `vite` = servidor de desarrollo + build tool (parecido a `uv run ... --reload` + empaquetado).
- `TypeScript` = Python con tipos, pero chequeados al compilar.
- `React` = componentes UI (parecido a plantillas + estado en cliente).
- `Zustand` = estado global reactivo (como modulo Python con estado compartido, pero conectado a la UI).
- `Zod` = validacion runtime de JSON (equivalente a `pydantic` en cliente).
- `Tailwind` = utilidades CSS reutilizables (estilo composable).
- `fetch` = `httpx` del navegador.
- `SPA` = app de una sola pagina (sin recargar HTML en cada accion).

## Papel de cada componente

1. FastAPI devuelve JSON.
2. El frontend llama a la API con `fetch`.
3. `Zod` valida la respuesta para evitar contratos rotos.
4. `Zustand` guarda filtros, lista, detalle y estados (`loading`, `error`).
5. `React` renderiza la interfaz en funcion del estado.
6. `Tailwind` aplica estilos.

## Flujo mental (version Python)

- Backend = servicio de datos.
- Frontend = cliente rico que consume esos datos.
- `Zod` = barrera anti-datos invalidos.
- `Zustand` = memoria de trabajo de la app.

Regla corta:

`FastAPI decide los datos; React decide como se muestran; Zustand recuerda estado; Zod evita tragarte JSON roto.`

## Comandos tipicos

- Instalar dependencias: `pnpm install` (similar a `uv sync`)
- Desarrollo local: `pnpm dev` (similar a `uv run ... --reload`)
- Tests: `pnpm test` (similar a `pytest`)
- Build: `pnpm build` (empaquetado para produccion)
