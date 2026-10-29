# Comprobantes T1 (correcciones) + T2 + T3 — pedido de revisión

**Rama:** `feat/comprobantes-ocr`, base `94f0c26`. **Implementó:** Claude Code (sesión de Tomi). **Revisa:** Mati con Codex, en contexto separado. **Estado: sin aprobar, sin integrar.** No se tocó Supabase remoto.

Sigue [el pase de comprobantes](../handoffs/2026-10-26-tomi-comprobantes.md): primero los cuatro hallazgos de [revision-ocr-t1](../handoffs/comprobantes/revision-ocr-t1.md) y después T2 del [plan](../handoffs/comprobantes/plan-continuacion.md). La migración es **0008** (0007 ya la usa la arquitectura).

## T1 — fuentes restauradas del ZIP (hashes del manifiesto verificados) y corregidas

| Hallazgo | Cambio en `backend/app/documents/ocr.py` | Test |
|---|---|---|
| 1. 60 s no cubrían la espera | Plazo total desde la entrada; semáforo con vencimiento; tiempo restante al hijo; `min(timeout, 60)` | `test_timeout_includes_waiting_for_the_slot`, `test_timeout_is_capped` |
| 2. Red bloqueada sólo en Python | `isolation()`: `sandbox-exec (deny network*)` en macOS, `unshare --net` en Linux, comprobado al arrancar. Sin eso (Windows) queda el bloqueo de Python ampliado y `engine` lo declara | `test_reader_has_no_network_at_os_level` (`connect_ex` a un listener local: 0 libre, ≠0 aislado) |
| 3. Importe extremo rompía `Decimal` | Más de 12 dígitos enteros ⇒ sólo candidato crudo, campo en revisión | `test_extreme_amount_goes_to_review_without_crashing` |
| 4. Referencia cruzaba páginas | Igualdad de página en la etiqueta sola | `test_reference_label_does_not_take_a_number_from_the_next_page` |
| Dimensiones finales del PDF | Escala con margen + rechazo si el render final supera 20 MP; página de tamaño 0 rechazada | — |

**Hallazgo nuevo en macOS:** el caso degradado «parcial» precargaba la referencia `…105` (real `…101`) con puntaje 0,64. Antes cumplía `needs_review` pero quedaba como valor sugerido. Ahora un valor con puntaje < 0,90 queda sólo como candidato (`test_low_score_value_is_a_candidate_not_a_suggestion`). En Windows no se había observado.

README de `backend/tools/` corregido: aislamiento por SO y sus límites, plazo total, candidatos. Sigue sin cubrir: memoria del decodificador de imágenes embebidas en PDF, aislamiento del filesystem, página con texto e imagen a la vez y comprobantes bancarios reales.

## T2 — transferencia verificada por el dueño y constancia

- **`supabase/migrations/0008_transfer_receipts.sql`:** `payments.provider` admite `transfer`; `verified_at`, `verified_by`, `reversed_at`; tabla `receipts` única por `(tenant_id, order_id)` con `snapshot jsonb`; RLS `tenant_isolation` + `member_access`/`member_only`; `app_user` sólo `select`; revoke a `anon`/`authenticated`. Aplicada dos veces seguidas sin error (idempotente).
- **`backend/app/payments/service.py`:**
  - `apply_payment` delega en `_apply(cur, …)`, compartido con `confirm_transfer`.
  - Al pasar a PAID, **en la misma transacción**: `receipts.issue` y, sólo si la constancia es nueva, el mensaje «¡Pago confirmado!» con `payload {"type":"receipt","receipt_id"}`. `_after_paid` queda sólo para auditoría y CRM.
  - `confirm_transfer(tenant, uid, order, ref, amount, currency)`: revalida la membresía (`PermissionError`) y bloquea el pedido (`LookupError` si no es del negocio). Usa el id `'<tenant>:<REF normalizada>'` y audita actor, referencia, importe y resultado. Una referencia ya usada en otro pedido choca con `uq_payments_provider_payment` ⇒ `ReferenceInUse` con rollback completo.
  - Fix de `_record_payment`: el primer UPDATE filtra por `order_id`, devuelve el id y sella `verified_at`/`verified_by`/`reversed_at`.
  - `_attention`: el aviso al comprador se persiste **una vez por motivo**, sin prometer avisos; las reversiones no lo envían. Como efecto, la auditoría `order_needs_attention` también deja de repetirse ante reintentos del mismo motivo.
- **`backend/app/domain/receipts.py`:** instantánea con negocio (nombre existente), pedido, productos, importes, `paid_at`, origen y referencia (sin prefijo interno), y la leyenda «Constancia comercial de compra — no es factura fiscal». Sin datos fiscales.
- **`backend/tests/test_receipts.py`** (13): doble confirmación y 4 hilos concurrentes ⇒ 1 constancia y 1 mensaje; webhook repetido con `_after_paid` que lanza ⇒ 1 y 1; referencia reutilizada ⇒ 409 sin tocar ninguno de los dos pedidos; importe o moneda incorrectos y pago tardío sin stock ⇒ sin PAID ni constancia y un solo aviso; reversión conserva la constancia y marca `reversed_at`; membresía revocada u otro negocio ⇒ rechazo; datos de transferencia inválidos.

## T3 — comprobantes del comprador, revisión del dueño y registro mensual

- **0008 suma `payment_documents`:** original en `bytea` privado (atajo para la demo, como pide el plan) y `unique(tenant_id, sha256)`. FK compuestas a pedido y conversación del mismo negocio; estado de lectura, intentos y reclamo; `ocr jsonb`; decisión auditada (`linked`/`rejected`, actor y fecha) y `payment_id`. RLS igual que `receipts`. `app_user` tiene `select` y `update` sólo de las columnas de decisión.
- **`backend/app/documents/store.py`:**
  - `receive`: tipo por firma, pedido de ESA conversación y no `CART_OPEN`. El mismo archivo en el mismo pedido devuelve el registro existente; en otro pedido, 409. Máximo 10 por pedido.
  - `process_pending`: reclamo con `for update skip locked` y OCR fuera de la transacción. Un fallo se reintenta en la vuelta **siguiente**, no en la misma. Máximo 3 intentos; un `processing` de más de 5 min se retoma.
  - Vista del comprador: sólo campos sugeridos con sus candidatos; las líneas del archivo nunca salen.
  - Panel: `list_month`, `original`, `reject` (no toca pagos ni un comprobante ya `linked`) y `link`.
  - `month_csv`: `;` y BOM, hora argentina. Una fila por pago verificado (con la cantidad de comprobantes) y las devoluciones con signo negativo en su mes. Los comprobantes son filas aparte, sin sumarse, y hay un total por moneda. Las celdas de texto no confiable que empiezan con `= + - @ \t \r` llevan `'` adelante.
- **`backend/app/main.py`:**
  - `POST /public/{slug}/conversations/{id}/orders/{order}/documents`: cuerpo crudo; el token del comprador se valida antes de leer; `Content-Length` y lectura acotada a 10 MiB (413); tipo inválido 415; ajeno 404.
  - `GET /public/.../conversations/{id}` suma `documents`.
  - Panel: `GET /app/payment-documents?month=`, `GET …/{id}/original` (attachment, `nosniff`, `no-store`), `POST …/{id}/reject`, `POST /app/orders/{id}/confirm-transfer` (`TransferConfirm`, con `document_ids`) y `GET /app/payments/register.csv?month=`.
- **`backend/app/worker.py`:** `run_once` agrega `payment_documents_read`.
- **`backend/tests/test_payment_documents.py`** (9 tests): recepción, dedupe y lectura sin acreditar pago, sin texto del archivo en `messages` ni en la vista; OCR real a través del worker; 404 sin token, con token ajeno, pedido ajeno u otro negocio; 415, 413 y 409 por archivo reutilizado; dueño que lista, descarga, confirma y asocia, contra un ajeno que recibe 404; rechazo que no altera un pago aprobado; validaciones y membresía revocada (403); reintentos y reclamo caído; CSV con límite de mes argentino, ARS y USD, 3 comprobantes de un pago contados una vez, devolución en su mes y fórmula escapada.

Sin UI todavía: T4 suma el chat, el panel y el PDF de la constancia, con prueba en navegador.

## Evidencia (macOS, Python 3.14, 28/10/2026)

- OCR: `pytest --noconftest tests/test_document_ocr.py` ⇒ **26 passed**, tres corridas. `python -m tools.prepare_ocr` ⇒ lectura real sin red, aislamiento por SO.
- Suite completa en DB descartable `127.0.0.1:55436` (contenedor `materialia-test-pg`, `supabase/postgres:17.11.0.003`, migraciones 0001–0008 + seed):
  - con T2: **308 passed**, dos corridas;
  - con T3: **317 passed, 0 failed, 0 skipped**, tres corridas.

  Una corrida tardó 15 min de reloj con 36 s de ejecución y 3% de CPU: el proceso quedó suspendido por el SO, no por un bloqueo. Warnings históricos: httpx/Starlette y JWT corto de tests.
- Demo local (54322): se aplicaron 0004–0007, que faltaban en el historial aunque las tablas existían, y 0008, reaplicada a mano tras sumar `payment_documents`. Sin reset. La API levanta y expone las rutas nuevas.

## Para el revisor

1. ¿Alcanza `sandbox-exec` (deprecado por Apple, pero funcional) o se prefiere fallar cerrado cuando no hay aislamiento del SO?
2. ¿Puntaje < 0,90 ⇒ sin valor sugerido es el criterio correcto, o se precarga marcado?
3. `verified_by` referencia `auth.users` con `on delete set null`: la auditoría conserva el actor en `audit_events`.
4. Deduplicar `order_needs_attention` por motivo cambia el conteo de auditorías ante reintentos del proveedor.
