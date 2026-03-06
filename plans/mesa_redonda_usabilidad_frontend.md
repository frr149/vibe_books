# Mesa Redonda de Usabilidad Frontend

Participantes: Steve Krug, Peter Morville, Louis Rosenfeld y Jakob Nielsen.

Objetivo: decidir mejoras de diseno y usabilidad del frontend actual (SPA con filtros, listado y detalle), discutiendo hasta llegar a consenso en 6 rondas.

## Ronda 1: Problema principal

- Krug: demasiadas decisiones visibles a la vez; prioridad en claridad de tarea (buscar y elegir libro).
- Nielsen: reforzar visibilidad del estado y prevencion de errores en filtros y paginacion.
- Morville: la encontrabilidad depende de etiquetas y facetas comprensibles.
- Rosenfeld: la arquitectura base es correcta, pero falta jerarquia mas explicita.

Resultado: acuerdo en simplificar la interaccion inicial.

## Ronda 2: Filtros

- Krug: anadir boton `Limpiar filtros`.
- Morville: usar terminos de usuario y corregir etiquetas (`Genero` -> `Género`).
- Rosenfeld: ordenar facetas por utilidad: busqueda, idioma, autor, genero, ISBN.
- Nielsen: favorecer reconocimiento frente a recuerdo con placeholders claros.

Resultado: consenso en labels, orden y reseteo rapido.

## Ronda 3: Listado

- Krug: cada item debe responder rapido que es y por que importa.
- Nielsen: consistencia en estado activo y foco por teclado.
- Morville: destacar metadatos utiles para decidir (autor, idioma, ISBN) sin ruido.
- Rosenfeld: estructura fija por tarjeta para escaneo rapido.

Resultado: consenso en mejorar escaneabilidad del listado.

## Ronda 4: Detalle

- Krug: detalle mas legible, separado por bloques de prioridad.
- Nielsen: correspondencia con el mundo real (idioma legible, no solo codigo).
- Morville: incluir navegacion semantica por autor y genero relacionados.
- Rosenfeld: mantener continuidad terminologica entre listado y detalle.

Resultado: consenso en priorizar lectura y continuidad semantica.

## Ronda 5: Estados y feedback

- Nielsen: hay `loading`, `empty`, `error`, pero falta granularidad y recuperacion.
- Krug: error con accion clara (`Reintentar`) en vez de solo `cerrar`.
- Morville: `empty state` debe sugerir como ajustar filtros.
- Rosenfeld: feedback contextual cerca del componente afectado.

Resultado: consenso en mejorar recuperacion y guidance.

## Ronda 6: Movil, accesibilidad y medicion

- Krug: en movil, primero tarea principal: busqueda y resultados.
- Nielsen: cumplir basicos WCAG: contraste, foco visible y teclado.
- Morville: taxonomias largas necesitan busqueda o mejor seleccion.
- Rosenfeld: definir metricas de exito de arquitectura de informacion.

Resultado: consenso final y backlog priorizado.

## Recomendaciones consensuadas

1. Anadir `Limpiar filtros` y `Reintentar` (P0).
2. Mejorar labels y textos (`Género`, mensajes de vacio accionables) (P0).
3. Reforzar estado activo, foco y navegacion por teclado (P0).
4. Mejorar tarjetas del listado para lectura rapida en 2-3 lineas (P1).
5. Reordenar panel de detalle por prioridad de lectura (P1).
6. En movil, mostrar primero busqueda y listado, dejando detalle debajo (P1).
7. Medir tiempo a primer click util, tasa de vacio y reintentos tras error (P2).
