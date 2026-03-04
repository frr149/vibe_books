# Plan Detallado ETL para Catálogo de Libros

## Objetivo
Construir una ETL que tome `data/books.csv`, complete datos faltantes (`autor_o_autores`, `editorial`, `idioma`, `genero`) y genere un dataset enriquecido con trazabilidad y niveles de confianza.

## Alcance
- Entrada: `data/books.csv`.
- Salidas:
  - `data/books_normalized.csv`
  - `data/books_candidates.csv`
  - `data/books_enriched.csv`
  - `data/books_review.csv` (pendientes de revisión manual)

## Diseño de datos (Fase 0)
Definir esquema enriquecido:
- `titulo`
- `autor_o_autores`
- `editorial`
- `idioma`
- `genero`
- `isbn_13`
- `isbn_10`
- `source`
- `source_id`
- `confidence`
- `review_status` (`auto_accepted`, `needs_review`, `unresolved`)
- `enriched_at`

Umbrales de decisión:
- `confidence >= 0.90`: auto-aceptar.
- `0.75 <= confidence < 0.90`: revisión manual.
- `< 0.75`: no completar.

## Fase 1: Normalización
1. Limpiar texto (`trim`, espacios múltiples, comillas, puntuación).
2. Normalizar mayúsculas/minúsculas y acentos para matching.
3. Canonizar editoriales (`oreilly` -> `O'Reilly`, etc.).
4. Normalizar autores (separadores `;`, `,`, `and`).
5. Exportar `data/books_normalized.csv`.

## Fase 2: Resolución de ISBN
1. Buscar por `titulo + autor` en fuentes que acepten texto (Open Library y Google Books).
2. Calcular score de matching usando:
   - similitud de título (fuzzy),
   - solapamiento de autores,
   - coincidencia de idioma/editorial (si existe).
3. Guardar todos los candidatos en `data/books_candidates.csv`.
4. Seleccionar mejor candidato y rellenar `isbn_13`/`isbn_10` con `confidence`.

## Fase 3: Enriquecimiento de metadatos
1. Usar ISBN resuelto para completar campos faltantes desde fuentes disponibles.
2. Preparar adaptador de Librario para activarlo cuando tengamos flujo con ISBN estable.
3. Reglas de merge:
   - no pisar datos existentes con menor confianza,
   - marcar conflictos como `needs_review`.

## Fase 4: Carga y revisión
1. Escribir `data/books_enriched.csv`.
2. Extraer registros ambiguos en `data/books_review.csv`.
3. Generar reporte de calidad:
   - porcentaje completado por campo,
   - porcentaje auto-aceptado,
   - porcentaje pendiente de revisión.

## Fase 5: Robustez y calidad
1. Tests unitarios para:
   - normalización,
   - scoring de matching,
   - reglas de merge.
2. Tests de integración con respuestas mock de APIs.
3. Idempotencia: dos ejecuciones sobre la misma entrada producen igual salida.

## Fase 6: Operación y CLI
Crear un comando único:

```bash
uv run python -m etl.cli run --input data/books.csv --output data/books_enriched.csv
```

Capacidades operativas:
- caché local de consultas para evitar llamadas repetidas,
- límites de concurrencia y timeouts,
- reintentos con backoff para errores transitorios,
- logging estructurado por etapa.

## Estructura propuesta
```text
etl/
  __init__.py
  cli.py
  models.py
  normalize.py
  matchers.py
  sources/
    openlibrary.py
    google_books.py
    librario.py
  enrich.py
  merge.py
  report.py
tests/
  test_normalize.py
  test_matchers.py
  test_merge.py
```

## Criterios de éxito
- `books_enriched.csv` generado sin errores.
- Incremento medible de completitud en `autor_o_autores` y `editorial`.
- Trazabilidad completa (`source`, `confidence`, `enriched_at`) en registros enriquecidos.
