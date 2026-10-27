# Chat público — cierre de acceso y continuidad

Base: `3d0a97a8912c86eded91beecfc90e8eab00e4a9f` (PR #11), 26/10/2026. Implementación y revisión cruzada terminadas para alcance demo.

## Problema y comportamiento resultante

La UUID de una conversación pública permitía a otro comprador del mismo negocio leerla/escribir en ella. La recarga perdía su referencia y una respuesta tardía podía restaurar un hilo descartado. También había rutas sandbox alternativas para sus pedidos/oportunidades.

Ahora cada conversación pública usa un token emitido por servidor (32 bytes, sólo hash persistido), enviado por header y guardado por tienda en sessionStorage. La lectura/escritura exige pertenencia. El cliente recupera el hilo en la misma pestaña y descarta respuestas/errores de generaciones anteriores. Sandbox no muestra ni modifica los pedidos/oportunidades de hilos protegidos. Sus mutaciones administrativas requieren opt-in `SANDBOX_ADMIN=true` y `APP_ENV=local`, deshabilitadas por defecto.

## Evidencia y reproducción

| Comprobación | Resultado |
|---|---|
| Base anterior, pytest con DB requerida | 127 aprobadas, 0 fallidas, 0 saltos |
| Versión corregida, pytest con DB requerida | **136 aprobadas, 0 fallidas, 0 saltos** |
| Build React/TypeScript/Vite | correcto |
| Navegador Chrome, versión corregida | **36 aprobadas, 0 fallidas**; incluye 390 px |
| Migración 0006 en DB descartable | aplicada dos veces sin errores |

Entorno del ejecutor: Python 3.12.10, Node 24.16, Postgres Supabase 17 en contenedor descartable local. LLM mock, proveedor de pago simulado. Las pruebas insertan usuarios y firman JWT locales; no prueban el servicio Auth completo ni Supabase remoto. No se realizaron cobros reales.

Backend: desde backend, con `DATABASE_URL` de una DB local de prueba con migraciones/seed, ejecutar `PV_REQUIRE_DB=1 LLM_PROVIDER=mock PAYMENT_PROVIDER=simulated python -m pytest -q`. Las pruebas de administración demo la habilitan explícitamente donde corresponde. Frontend: `npm ci && npm run build`; [instrucciones del harness compartible](../../web/e2e/README.md) para `npm run e2e`. Sólo opera en servicios locales con datos sintéticos; cada corrida consume una unidad del stock demo y requiere una base de prueba preparada.

Se reprodujeron los fallos en la base y las nuevas regresiones fallaron antes del arreglo. El primer falso fallo del chat demo se debió al matcher de URL del harness (query string); se corrigió el harness y se repitió la comparación. Las 36 comprobaciones/build de R2b se conservaron en R2c porque sólo cambió backend/configuración/documentación; backend sí se volvió a ejecutar.

## Actores y alcance de revisión

Claude Code: `claude-opus-5-5` efectivo, high solicitado (esfuerzo efectivo no expuesto). Reutilizó una sesión para preparación/correcciones. Skills declaradas: Superpowers receiving-code-review/TDD/verification, Agent Skills frontend/security y Supabase para el esquema.

Codex personal: `gpt-6.1-sol`, high en la cabecera CLI. Primera revisión estática acotada sobre paquete de fuentes numeradas; instrucciones Agent Skills code-review-and-quality y Supabase. No ejecutó pruebas ni consultó la base. El orquestador preparó briefs, asignó el trabajo y documentó; no implementó producto. La [revisión final](2026-10-26-chat-publico-codex.md) aprobó el diff/evidencia congelados sin bloqueos P1/P2. El orquestador comprobó que los 21 archivos fijados conservaron sus hashes hasta recibirla; después sólo actualizó metadatos documentales de cierre.

## Límites

- Credencial legible por JavaScript, sin vencimiento/rotación/revocación; se pierde la referencia al cerrar la pestaña.
- Datos anteriores a 0006 no tienen token. La privacidad de pedidos/oportunidades depende de su conversación asociada; revisar esa clasificación antes de agregar borrado de conversaciones.
- Demo y checkout simulado conservan su alcance; no es aprobación para producción ni pago real.
- 0006 aplicada sólo en DB local descartable. Revalidar el remoto y autorizar migraciones antes de desplegar.

Logs de ejecución, informes completos de los agentes y herramientas de coordinación se conservan en la entrega local; las regresiones necesarias para repetir la comprobación están en el repositorio.
