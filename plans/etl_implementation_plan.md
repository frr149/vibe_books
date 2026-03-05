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
  - `data/books_catalog.db` (SQLite para consulta de catálogo)

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

## Fase 4.5: Fallback automático para casos ambiguos
1. Tomar `data/books_review.csv` y `data/books_candidates.csv`.
2. Aplicar reglas deterministas de autoaceptación:
   - score mínimo configurable,
   - diferencia mínima entre primer y segundo candidato,
   - ISBN válido (checksum),
   - compatibilidad básica de idioma/editorial cuando existan.
3. Generar `data/books_manual_overrides.csv` con decisiones trazables:
   - `id`, `isbn_13`, `isbn_10`, `source`, `confidence`, `reason`, `rule`.
4. Aplicar overrides sobre `data/books_enriched.csv` y regenerar:
   - `data/books_review_remaining.csv`,
   - `data/books_fallback_report.json`.
5. Nunca sobreescribir datos existentes de alta confianza; solo completar faltantes o promover `needs_review` cuando las reglas se cumplan.

## Fase 5: Robustez y calidad
1. Tests unitarios para:
   - normalización,
   - scoring de matching,
   - reglas de merge/fallback.
2. Tests de integración con respuestas mock de APIs.
3. Idempotencia: dos ejecuciones sobre la misma entrada producen igual salida.

## Fase 6: Descarga de portadas (fase final)
1. Tomar `data/books_enriched.csv` y resolver portada por ISBN con prioridad:
   - Librario (si hay token),
   - Google Books (`q=isbn`),
   - Open Library (`covers.openlibrary.org`) como fallback.
2. Descargar imagen local en `data/covers/` con nombre estable por `id` e `isbn`.
3. Escribir manifiesto `data/covers_manifest.csv` con:
   - `id`, `isbn`, `cover_url`, `cover_source`, `local_path`, `status`, `error`, `downloaded_at`.
4. Actualizar `data/books_enriched.csv` con:
   - `cover_url`, `cover_source`, `cover_local_path`.
5. No fallar toda la ETL por una portada: registrar error por fila y continuar.

## Fase 7: Operación y CLI
Crear un comando único:

```bash
uv run python -m etl.cli run --input data/books.csv --output data/books_enriched.csv
```

Capacidades operativas:
- caché local de consultas para evitar llamadas repetidas,
- límites de concurrencia y timeouts,
- reintentos con backoff para errores transitorios,
- logging estructurado por etapa.

## Fase 8: Carga en SQLite
1. Crear `data/books_catalog.db`.
2. Definir tabla `books` con columnas del CSV enriquecido (`id`, `titulo`, `autor_o_autores`, `editorial`, `idioma`, `genero`, `isbn_13`, `isbn_10`, `source`, `source_id`, `confidence`, `review_status`, `metadata_source`, `metadata_confidence`, `conflict_notes`, `cover_url`, `cover_source`, `cover_local_path`, `enriched_at`).
3. Cargar/actualizar datos desde `data/books_enriched.csv` (modo idempotente por `id`).
4. Añadir comando CLI dedicado (`load-sqlite`) y dejar trazabilidad de filas insertadas/actualizadas.

## Implementación inmediata (siguiente iteración)
- [ ] Fase 7: comando único `run` que encadene fases 1 -> 6.
- [ ] Logging estructurado por etapa (normalización, resolución ISBN, enrich, revisión, fallback, portadas, sqlite).
- [ ] Fase 5: tests de integración con mocks de APIs de fuentes.
- [ ] Fase 5: test de idempotencia end-to-end.
- [ ] Fase 8: carga de `books_enriched.csv` a SQLite.

## Para más tarde
- [ ] (2) Caché local de consultas para evitar llamadas repetidas.
- [ ] (3) Límites de concurrencia (workers/semaforización) además de retries y timeouts.
- [ ] (6) Refactor de estructura para separar `merge.py`/`test_merge.py` si compensa frente al diseño actual.

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
  fallback_review.py
  covers.py
tests/
  test_normalize.py
  test_matchers.py
  test_merge.py
  test_fallback_review.py
  test_covers.py
```

## Criterios de éxito
- `books_enriched.csv` generado sin errores.
- Incremento medible de completitud en `autor_o_autores` y `editorial`.
- Trazabilidad completa (`source`, `confidence`, `enriched_at`) en registros enriquecidos.
