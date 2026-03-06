# Informe de Riesgos OWASP Top 10:2025

Fecha: 2026-03-06  
Alcance: API (`api/`) + Frontend (`apps/web/`) del proyecto.

## Resumen ejecutivo

Se analizo el estado actual del sistema contra OWASP Top 10:2025.

Riesgos mas relevantes detectados:

1. Exposicion sin control de acceso (A01/A07) si la API no es publica por diseno.
2. Configuracion de seguridad incompleta (A02), incluyendo exposicion de metadatos internos.
3. Cobertura limitada de seguridad en cadena de suministro (A03).
4. Manejo mejorable de condiciones excepcionales y observabilidad (A09/A10).

Puntos fuertes actuales:

1. Mitigacion de SQL injection con consultas parametrizadas.
2. Validacion de contratos en frontend con Zod.
3. Tests de API y repositorio en verde.

## Metodologia y suposiciones

- Se reviso codigo fuente y tests del repositorio.
- Se mapearon hallazgos contra categorias OWASP 2025.
- Suposicion clave: si la API debe ser privada, A01/A07 suben a severidad critica.

## Hallazgos por categoria OWASP 2025

## A01: Broken Access Control

Fallo posible:
- Endpoints de API expuestos sin autorizacion.

Evidencia:
- [api/main.py](/Users/fernando/Downloads/vibe_books/api/main.py:47)
- [api/main.py](/Users/fernando/Downloads/vibe_books/api/main.py:102)
- [api/main.py](/Users/fernando/Downloads/vibe_books/api/main.py:126)

Por que importa:
- Cualquier cliente puede enumerar datos y taxonomias.
- Si el alcance cambia a datos restringidos, la exposicion es inmediata.

Mitigacion propuesta:
1. Definir politica de acceso por endpoint (publico/privado).
2. Si privado: JWT o API key con scopes y expiracion.
3. Aplicar deny-by-default y controles de autorizacion por recurso.

## A02: Security Misconfiguration

Fallo posible:
- Hardening incompleto en API.
- Exposicion de `cover_local_path` en contrato publico.

Evidencia:
- [api/main.py](/Users/fernando/Downloads/vibe_books/api/main.py:177)
- [api/schemas.py](/Users/fernando/Downloads/vibe_books/api/schemas.py:48)
- [api/repository.py](/Users/fernando/Downloads/vibe_books/api/repository.py:201)

Por que importa:
- Filtra detalles internos de infraestructura.
- Aumenta superficie para fingerprinting y abuso.

Mitigacion propuesta:
1. Eliminar `cover_local_path` de respuestas publicas.
2. Configurar CORS por allowlist.
3. Activar `TrustedHostMiddleware` y cabeceras de seguridad en edge/proxy.
4. Restringir `/docs` y `/openapi.json` en produccion si aplica.

## A03: Software Supply Chain Failures

Fallo posible:
- Dependencias sin auditoria automatica de CVEs.

Evidencia:
- [pyproject.toml](/Users/fernando/Downloads/vibe_books/pyproject.toml:6)
- [apps/web/package.json](/Users/fernando/Downloads/vibe_books/apps/web/package.json:14)
- [justfile](/Users/fernando/Downloads/vibe_books/justfile:6)

Por que importa:
- Riesgo de introducir librerias vulnerables en backend o frontend.

Mitigacion propuesta:
1. Incluir `pip-audit` y `pnpm audit` en CI.
2. Generar SBOM y registrar versionado.
3. Automatizar actualizaciones con Dependabot/Renovate.
4. Forzar instalaciones reproducibles con lockfiles.

## A04: Cryptographic Failures

Fallo posible:
- Configuracion local por defecto en HTTP.

Evidencia:
- [apps/web/src/api/config.ts](/Users/fernando/Downloads/vibe_books/apps/web/src/api/config.ts:1)

Por que importa:
- Si se replica en entornos reales sin TLS, el trafico viaja sin cifrado.

Mitigacion propuesta:
1. En produccion, aceptar solo `https://`.
2. Redireccion HTTP a HTTPS.
3. HSTS y politicas TLS en reverse proxy.

## A05: Injection

Estado actual:
- SQL injection mitigada en consultas principales.

Evidencia positiva:
- [api/repository.py](/Users/fernando/Downloads/vibe_books/api/repository.py:48)
- [api/repository.py](/Users/fernando/Downloads/vibe_books/api/repository.py:104)
- [tests/test_api_stage4_repository.py](/Users/fernando/Downloads/vibe_books/tests/test_api_stage4_repository.py:127)

Riesgo residual:
- `cover_url` de terceros puede inyectar recursos no confiables.

Evidencia:
- [etl/covers.py](/Users/fernando/Downloads/vibe_books/etl/covers.py:230)
- [apps/web/src/App.tsx](/Users/fernando/Downloads/vibe_books/apps/web/src/App.tsx:232)

Mitigacion propuesta:
1. Validar esquema y dominio de URLs de portada.
2. Aplicar allowlist de dominios conocidos.
3. Preferir proxy backend para servir imagenes remotas.

## A06: Insecure Design

Fallo posible:
- Controles antiabuso incompletos (consultas repetidas y scraping).

Evidencia:
- [api/contracts.py](/Users/fernando/Downloads/vibe_books/api/contracts.py:31)
- [apps/web/src/App.tsx](/Users/fernando/Downloads/vibe_books/apps/web/src/App.tsx:32)

Por que importa:
- Facilita degradacion de servicio y consumo excesivo de recursos.

Mitigacion propuesta:
1. Rate limiting por IP/API key.
2. Debounce en busqueda del frontend.
3. Limites de longitud para filtros de texto.
4. Limite superior para `page` y controles de abuso por patron.

## A07: Authentication Failures

Fallo posible:
- No existe autenticacion en endpoints de negocio.

Evidencia:
- [api/main.py](/Users/fernando/Downloads/vibe_books/api/main.py:47)

Por que importa:
- Si no se pretende API publica, hay exposicion total de datos.

Mitigacion propuesta:
1. Definir modelo de identidad (API key/JWT).
2. Implementar expiracion, rotacion y revocacion de credenciales.
3. Aplicar bloqueo gradual ante abuso.

## A08: Software or Data Integrity Failures

Fallo posible:
- Ingestion de datos externos con validacion limitada de integridad/confianza.

Evidencia:
- [etl/sources/openlibrary.py](/Users/fernando/Downloads/vibe_books/etl/sources/openlibrary.py:68)
- [etl/sources/google_books.py](/Users/fernando/Downloads/vibe_books/etl/sources/google_books.py:57)
- [etl/covers.py](/Users/fernando/Downloads/vibe_books/etl/covers.py:145)

Por que importa:
- Datos de proveedor comprometido pueden contaminar catalogo.

Mitigacion propuesta:
1. Registrar trazabilidad por fuente para cada campo.
2. Validar dominios y formatos de contenido.
3. Cuarentena para cambios sospechosos antes de publicar.

## A09: Security Logging and Alerting Failures

Fallo posible:
- Falta de logging de seguridad estructurado y alertas operativas.

Evidencia:
- [api/main.py](/Users/fernando/Downloads/vibe_books/api/main.py:80)

Por que importa:
- Deteccion tardia de incidentes y baja capacidad de respuesta.

Mitigacion propuesta:
1. Logging JSON con `request_id`, endpoint, latencia y estado.
2. Registro de errores de DB/red con contexto.
3. Alertas sobre picos de 4xx/5xx y timeouts.

## A10: Mishandling of Exceptional Conditions

Fallo posible:
- Excepciones amplias absorbidas en ETL y respuestas de error no uniformes.

Evidencia:
- [etl/sources/openlibrary.py](/Users/fernando/Downloads/vibe_books/etl/sources/openlibrary.py:71)
- [etl/sources/google_books.py](/Users/fernando/Downloads/vibe_books/etl/sources/google_books.py:60)
- [etl/sources/librario.py](/Users/fernando/Downloads/vibe_books/etl/sources/librario.py:59)
- [api/main.py](/Users/fernando/Downloads/vibe_books/api/main.py:21)

Por que importa:
- Oculta fallos reales y reduce capacidad de observacion.

Mitigacion propuesta:
1. Politica central de errores con envelope consistente.
2. Logging obligatorio de excepciones.
3. Reintentos con presupuesto y backoff definidos.

## Priorizacion recomendada

## P0 (inmediato)
1. Definir si la API es publica o privada y aplicar auth/acl segun modelo.
2. Quitar `cover_local_path` del contrato publico.
3. Cerrar o proteger docs/openapi en produccion.
4. Implementar rate limiting basico.

## P1 (corto plazo)
1. Hardening de configuracion (CORS allowlist, TrustedHost, cabeceras).
2. Debounce en busqueda y limites de entrada.
3. Logging estructurado y alertas minimas.

## P2 (medio plazo)
1. Pipeline SCA completo con auditoria automatica.
2. Controles de integridad y cuarentena para datos externos.
3. Metrica de seguridad operacional y revisiones periodicas.

## Referencias oficiales OWASP 2025

- https://owasp.org/Top10/
- https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/
- https://owasp.org/Top10/2025/A02_2025-Security_Misconfiguration/
- https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/
- https://owasp.org/Top10/2025/A04_2025-Cryptographic_Failures/
- https://owasp.org/Top10/2025/A08_2025-Software_or_Data_Integrity_Failures/
- https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/
