# Asistente paso a paso — revisión y correcciones

**Rama:** `feat/asistente-agente`. **Implementó:** Claude Code (sesión de Tomi). **Diseño:** [spec](../superpowers/specs/2026-10-29-asistente-agente-design.md). **Estado:** sin revisión de Mati.

## Revisión en contexto fresco (Claude, 29/10/2026)

La hizo `/code-review high` sobre el diff de la rama, en un contexto separado. No aporta diversidad de modelo ni de cuenta. Encontró 10 hallazgos, todos corregidos:

| # | Hallazgo | Corrección |
|---|---|---|
| 1 | Elegir el rubro aplicaba la plantilla **en vivo**, sin confirmación si era el actual, y borraba envíos, horarios y pagos | `GET /app/agent-templates/{key}` devuelve la plantilla sin aplicarla; el asistente la vuelca al borrador, siempre con confirmación, y no toca envíos, horarios ni pagos |
| 2 | Por eso, «nada se guarda hasta Publicar» era falso, se salteaban las pruebas y «Publicar» figuraba hecho sin publicar | Sólo «Publicar» guarda el perfil. El paso queda hecho cuando el perfil guardado es el que publicó el asistente y coincide con el borrador |
| 3 | El registro nunca llegaba al asistente, porque Signup redirigía antes | `Signup.tsx` (y el link del correo de confirmación) van a `#/asistente` |
| 4 | Un borrador viejo del navegador podía pisar cambios guardados en «Mi agente», incluido el link | El borrador recuerda sobre qué versión se armó; si el perfil cambió, se descarta y se avisa |
| 5 | La vista previa reproducía toda la charla en cada mensaje (costo cuadrático, respuestas que cambiaban) | Vista previa con estado: una conversación de prueba, un mensaje por llamada, `DELETE` al reiniciar o salir y limpieza del worker |
| 6 | Pasos que el sistema completa solo figuraban hechos | Link, rubro y «cómo habla» cuentan recién cuando el dueño pasó por el paso |
| 7 | La vista previa no decía cuándo respondía por reglas (`CLAUDE.md`: nunca fingir modelo real) | «Respuesta por reglas (sin IA)» con `mode = mock`; el paso Cobro no afirma el medio de pago si no pudo consultarlo |
| 8 | Si fallaba el primer turno, la conversación de prueba quedaba (también en `evals.run`) | La conversación se crea antes del turno y se borra si falla; `run` igual |
| 9 | La vista previa y las pruebas mandaban el link del borrador: un link a medio escribir rompía «Probar» | Se prueba sin `public_slug`; el mensaje escrito se conserva si falla el envío |
| 10 | «Publicar igual» dependía del texto del error | Header `X-Error-Code: evals_failed` (expuesto por CORS) en el 409; lo usan el asistente y «Mi agente». `MAX_PREVIEW_MESSAGES` vive en `schemas` |

## Evidencia (29/10/2026)

- **Backend:** **344 passed** en una DB descartable (0001–0010 + seed). `test_agent_preview.py` cubre borrador, aislamiento, tope, limpieza tras fallo y abandono, plantilla sin aplicar y 409 estructurado.
- **Navegador**, en un entorno aislado:
  - `e2e:asistente` **15/15** (dos corridas): incluye «elegir rubro no publica» y «sin IA»;
  - `e2e:bandeja` **11/11**, `e2e:comprobantes` **17/17**, `e2e` **36 PASS, 0 FAIL**.

## Límites

- El registro no se recorre en el e2e: en el entorno aislado, el Auth local y la base de la API son distintos.
- La cantidad de productos se obtiene cargando el catálogo completo.
