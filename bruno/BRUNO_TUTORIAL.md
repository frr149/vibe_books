# Tutorial rápido de Bruno para `vibe_books`

Este tutorial explica cómo usar Bruno para probar la API sin frontend.

## ¿Qué es una colección en Bruno?

Una **colección** es un conjunto de peticiones HTTP guardadas como archivos en una carpeta del proyecto.  
En este repo, la colección está en:

- `bruno/vibe-books/`

Ventajas:

- Puedes versionarla con Git.
- Todo el equipo comparte las mismas requests.
- No dependes de exportar/importar JSON manualmente.

## Estructura de la colección de este proyecto

- `bruno/vibe-books/bruno.json`: metadatos de la colección.
- `bruno/vibe-books/Health/health.bru`: endpoint de salud.
- `bruno/vibe-books/Books/list-books.bru`: listado con búsqueda.
- `bruno/vibe-books/Books/book-detail.bru`: detalle por ID.

Los archivos `.bru` son las peticiones que Bruno ejecuta.

## Requisitos

1. Tener Bruno instalado.
2. Tener la API levantada localmente.

Para levantar la API en este repo:

```bash
just api-dev
```

## Cómo abrir y ejecutar la colección

1. Abre Bruno.
2. Haz clic en `Open Collection`.
3. Selecciona la carpeta `bruno/vibe-books`.
4. En el panel izquierdo verás las carpetas `Health` y `Books`.
5. Ejecuta `Health` para comprobar que la API responde.
6. Ejecuta `List Books` para ver resultados paginados.
7. Ejecuta `Book Detail` para ver un libro concreto (`/books/1`).

## Ajustes habituales

- Si cambias el puerto/host de la API, edita la URL en cada `.bru`.
- Puedes duplicar una request para probar otros filtros (`q`, `author`, `genre`, `page`, `page_size`).

Ejemplo de URL con filtros:

```text
http://127.0.0.1:8000/api/v1/books?q=python&page=1&page_size=10
```

## Flujo recomendado

1. Arranca API: `just api-dev`
2. Prueba endpoints en Bruno
3. Si haces cambios en backend: vuelve a ejecutar requests clave (`health`, `list`, `detail`)
4. Antes de commit: `just lint` y `just test`
