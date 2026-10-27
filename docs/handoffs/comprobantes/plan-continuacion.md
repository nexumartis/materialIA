# Diseño de continuación — checkpoint para Tomi

Propuesta de Claude, todavía sin implementar/revisar T2–T4. Los bloqueos T1 de revision-ocr-t1.md tienen prioridad. N1 ya cerró y libera sus archivos: las menciones a ownership activo y COORD del informe siguiente son históricas. Contrastar con main antes de aplicar; el esquema 0007 aún no existe.

# O2 — detalle del builder check (restaurado tras T1)

`OCR-BUILDER.md` quedó reemplazado en disco por el resumen breve de la respuesta. Este archivo restaura el detalle técnico para T2–T4 sobre la base `6290f60`, con los ajustes de T1. Fuente: misma sesión de Claude Code.

## Diseño (contrastado con el código)

1. **Constancia sin efecto perdido.** En la misma `tenant_tx` de `apply_payment` que deja el pedido en `status='PAID'`:
   - `insert into receipts` con un snapshot jsonb y `unique(tenant_id, order_id)`;
   - sólo si ese insert devolvió fila, el mensaje saliente con `payload {"type":"receipt","receipt_id"}`.

   El texto «¡Pago confirmado!» (lo afirma `test_payments.py:51`) pasa a ese insert y `_after_paid` queda sólo para CRM y auditoría. **Hoy N1b posee la copia de `_after_paid`: coordinar antes de T2.** El PDF se arma bajo demanda desde el snapshot.
2. **Transferencia = mismo efecto.** `apply_payment` se divide en `_apply(cur, tenant_id, order_id, provider, payment)` y el envoltorio actual. `confirm_transfer(tenant, uid, order_id, ref, amount, currency, doc_ids)` corre en `tenant_tx`: revalida la membresía de `uid`, registra el actor y llama a `_apply` con `ProviderPayment(status="approved")`.
3. **Fix en `_record_payment`:** su primer UPDATE no filtra por `order_id`. Hay que agregar `and order_id = %s`: así, una referencia ya usada en otro pedido choca con `uq_payments_provider_payment` y responde 409. Para transferencias, `provider_payment_id = '<tenant_id>:<ref normalizada>'`, de modo que la unicidad sea por negocio sin tocar el índice global.
4. **Aislamiento del texto OCR:** nunca va a `messages`, `agent_state` ni al LLM. El comprador lo ve en una clave `documents` aparte dentro del GET de la conversación.
5. **Originales en Postgres** (`bytea` con RLS). `shortcut: <=10 MiB, datos sintéticos; pasar a bucket privado de Supabase Storage antes del piloto.`
6. **Subida:** body crudo, `Content-Length` y lectura acotada del stream; sin `python-multipart`. Tipo con `ocr.sniff`.
7. **Mes argentino:** se calcula en SQL con `at time zone 'America/Argentina/Buenos_Aires'`.
8. **Exportación:** CSV de la stdlib, separador `;` y BOM. Las celdas de texto que empiezan con `= + - @ \t \r` llevan `'` adelante. Los importes calculados no se escapan.
9. **Reserva:** un comprobante recibido no la extiende. Una confirmación tardía usa el camino de CANCELLED que ya existe.

## Esquema `0007_payment_documents.sql` (idempotente, patrón 0003/0005)

- **`payment_documents`:** `tenant_id`, `order_id` (FK compuesta), `conversation_id`, `sha256` (`unique(tenant_id, sha256)`), `mime`, `size`, `pages`, `content bytea`, `status` (`received|processing|read|unreadable`), `attempts`, `claimed_at`, `ocr jsonb` (salida de `read_document`), `decision` (`null|linked|rejected`), `decided_by`, `decided_at`, `payment_id`, `received_at`.
- **`receipts`:** `tenant_id`, `order_id` único por tenant, `payment_id`, `snapshot jsonb`, `issued_at`.
- **`payments`:**
  - el check de `provider` se recrea con `'transfer'`;
  - nuevas columnas `verified_at` (coalesce al aprobar), `reversed_at` y `verified_by uuid`.
- **RLS:**
  - `tenant_isolation`, `member_access` y `member_only` restrictiva;
  - grants a `app_user`: select/update(decision…) en documentos y select en receipts;
  - revoke a `anon` y `authenticated`;
  - sin `security definer` nuevo.

## Matriz T2–T4 (owner O2 = Claude Code; revisor = Codex personal)

| Archivo | Tarea |
|---|---|
| `supabase/migrations/0007_payment_documents.sql` | T2 |
| `backend/app/payments/service.py` (`_apply`, `verified_at`, receipt + mensaje en tx, `confirm_transfer`, aviso de incidencia una vez, fix `_record_payment`) | T2, después del cierre de N1b |
| `backend/app/domain/receipts.py` (snapshot; PDF con reportlab en T4 → pasar reportlab de `dev` a deps) | T2/T4 |
| `backend/app/documents/store.py` (validación, dedupe, claim `for update skip locked`, proceso con `ocr.read_document`, reintento si `processing` lleva >5 min, máx. 3 intentos, registro mensual y CSV) | T3 |
| `backend/app/worker.py` (`run_once` suma `store.process_pending()`) | T3 |
| `backend/app/main.py`: rutas públicas (upload, documents en GET, PDF de la constancia con header) y de panel (lista, original, rechazo, confirmar, CSV, PDF) | T3/T4 |
| `backend/app/config.py`, `backend/.env.example` (sólo si hace falta un límite configurable) | T3 |
| `backend/tests/test_payment_documents.py`, `test_receipts.py`; `test_payments.py` sólo si cambia una aserción (coordinar con N1b) | T2–T4 |
| `web/src/pages/Sales.tsx` (lo usa `Store.tsx`), `web/src/pages/OrdersPage.tsx`, `web/src/lib/api.ts`, `web/e2e/` nuevo | T4 |

**Prohibido:** `backend/app/agent/*`, `test_sales_agent.py`, `test_llm_sales.py`, `test_natural_conversation.py`, `backend/evals/`, los specs y planes de N1, `docs/current-state.md` y las decisiones (orquestador), y `buyer_session.py` (sólo se reutiliza `owns`).

## Aceptación por tarea

- **T2:**
  - webhook repetido, doble confirmación concurrente y `_after_paid` que lanza dejan exactamente 1 constancia y 1 mensaje;
  - una referencia ya usada en otro pedido devuelve 409 y no toca ninguno de los dos;
  - importe o moneda distintos, o falta de stock: el pedido no pasa a PAID, no hay constancia y el aviso se persiste una sola vez;
  - una reversión conserva la constancia y marca `reversed_at`;
  - una membresía revocada recibe 403.
- **T3:**
  - token ajeno, UUID conocida, otro negocio o sandbox reciben 404 en upload, lista, original y PDF;
  - dedupe por archivo;
  - el texto OCR nunca aparece en `messages`;
  - rechazar un documento no altera un pago aprobado;
  - CSV: límite de mes en hora argentina, ARS y USD separados, 3 documentos de un mismo pago suman una vez, la devolución cae en su mes y una fórmula en el OCR sale escapada.
- **T4:**
  - el texto del PDF (extraído con pypdfium2) incluye negocio, pedido, productos, importe y moneda, fecha, origen y «Constancia comercial de compra — no es factura fiscal»;
  - hay control visual;
  - flujo completo en navegador; recargar o hacer doble clic no duplica nada; se ve bien a 390 px.
