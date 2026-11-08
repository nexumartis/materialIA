# WhatsApp etapa 1 (recibir y responder texto) — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que un cliente le escriba por WhatsApp al número conectado de un local y le conteste el mismo agente que hoy atiende la web, con todos los mensajes salientes de esa conversación (agente, bandeja, avisos de pago, reparto y envío) saliendo por WhatsApp.

**Architecture:** una ruta pública recibe los avisos de Meta, verifica la firma y procesa en segundo plano. El negocio sale del `phone_number_id`, buscado en `whatsapp_connections`. Cada contacto tiene una conversación (`conversations.wa_id`) y el texto va a `sales_agent.handle_sales_message(..., channel="whatsapp")`. Un trigger en `messages` encola cada mensaje saliente de una conversación de WhatsApp en `whatsapp_outbox`. `whatsapp.deliver_due()` lo manda por la Graph API, en el momento después de cada turno y con reintentos desde el worker. Es el mismo patrón de cola de `domain/webhooks.py`.

**Tech Stack:** Python 3.12, FastAPI, psycopg 3, Supabase Postgres, httpx, `cryptography` (Fernet; ya instalada como dependencia de `pyjwt[crypto]`), pytest contra Postgres real.

**Spec:** `docs/superpowers/specs/2026-11-08-whatsapp-design.md` (etapa 1 del «Orden sugerido»; las etapas 2 a 5 van en planes aparte).

## Global Constraints

- El negocio sale **sólo** del `phone_number_id` registrado en `whatsapp_connections`. Si el número no está registrado o está `disconnected`, el aviso se descarta.
- La firma `X-Hub-Signature-256` (`sha256=` + HMAC-SHA256 del cuerpo crudo con `WHATSAPP_APP_SECRET`) se verifica **antes** de parsear el JSON.
- El token de cada local se guarda cifrado (Fernet con `WHATSAPP_TOKEN_KEY`). Nunca sale en una respuesta HTTP, en los logs ni en un mensaje de error.
- Graph API: `https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{phone_number_id}/messages`, con `v25.0` por defecto.
- Un texto de WhatsApp tiene como máximo **4.096** caracteres.
- Sólo se le escribe a un cliente que escribió en las **últimas 24 horas** (`conversations.last_customer_message_at`).
- Cada mensaje de Meta se procesa **una sola vez**, identificado por su `id` (`wamid`).
- Sin dependencias nuevas. Migración idempotente (`create … if not exists`, `drop … if exists` antes de recrear), sin `DROP` de datos.
- Las reglas de `CLAUDE.md` siguen igual: precios y stock salen de la base, un pago cuenta sólo verificado, y no se fingen modelos (`mode:"mock"`).
- Tests con `PV_REQUIRE_DB=1` contra Postgres con las migraciones y el seed. LLM `mock`. Las llamadas a Meta se simulan con `httpx.MockTransport`, sin red.

## Review Focus

- **Meta manda el mismo mensaje dos veces** (reintento del aviso): el agente contesta una sola vez → test en la Tarea 4.
- **Llega un aviso de un número no conectado**, o de un local que se desconectó: no se crea conversación ni se gasta IA → test en la Tarea 4.
- **Un cliente manda decenas de mensajes por hora**: a partir del tope no se llama al agente ni se responde → test en la Tarea 4.
- **La respuesta del agente pasa los 4.096 caracteres**: se manda en partes y no se rechaza → test en la Tarea 3.
- **Un aviso de pago o de reparto sale más de 24 horas después del último mensaje del cliente**: no se manda, queda como `window_closed` y no se reintenta → test en la Tarea 3.

---

### Tarea 1: Tablas, cola y trigger

**Files:**
- Create: `supabase/migrations/0034_whatsapp.sql`
- Test: `backend/tests/test_whatsapp_schema.py`

**Interfaces:**
- Produces:
  - `whatsapp_connections(tenant_id uuid pk → tenants, phone_number_id text unique not null, waba_id text not null, display_phone text not null, token_encrypted text not null, status text not null default 'connected' check in ('connected','disconnected'), created_at, updated_at)`.
  - `conversations.wa_id text` y el índice único `(tenant_id, wa_id) where wa_id is not null`.
  - `whatsapp_inbound(wamid text primary key, tenant_id uuid not null, received_at timestamptz default now())`.
  - `whatsapp_outbox(id uuid pk, tenant_id, conversation_id, message_id uuid unique → messages on delete cascade, status text default 'pending' check in ('pending','sent','failed','window_closed'), attempts int default 0, next_attempt_at timestamptz default now(), wamid text, last_error text, created_at, sent_at)`, con un índice parcial `(next_attempt_at) where status = 'pending'`.
  - El trigger `trg_messages_whatsapp_outbox` (after insert on `messages`): si `direction = 'outbound'`, la conversación tiene `wa_id` y `coalesce(payload->>'type','') <> 'owner_app'`, inserta una fila en `whatsapp_outbox`. `owner_app` es para la etapa 3: lo que el dueño escribe desde la app no se reenvía.
  - RLS activado en las tres tablas nuevas y sin grants para `anon`, `authenticated` ni `app_user`: sólo las lee el backend.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_outbound_en_conversacion_whatsapp_se_encola(raw_conn):
    conv = _conv(raw_conn, TENANT_C, wa_id="5491100000001")
    msg = _msg(raw_conn, TENANT_C, conv, "outbound", "hola", None)
    assert _outbox(raw_conn, msg)["status"] == "pending"

def test_outbound_web_no_se_encola(raw_conn):
    conv = _conv(raw_conn, TENANT_C, wa_id=None)
    msg = _msg(raw_conn, TENANT_C, conv, "outbound", "hola", None)
    assert _outbox(raw_conn, msg) is None

def test_inbound_y_owner_app_no_se_encolan(raw_conn):
    conv = _conv(raw_conn, TENANT_C, wa_id="5491100000002")
    assert _outbox(raw_conn, _msg(raw_conn, TENANT_C, conv, "inbound", "hola", None)) is None
    assert _outbox(raw_conn, _msg(raw_conn, TENANT_C, conv, "outbound", "ya va", {"type": "owner_app"})) is None

def test_un_contacto_una_conversacion(raw_conn):
    _conv(raw_conn, TENANT_C, wa_id="5491100000003")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _conv(raw_conn, TENANT_C, wa_id="5491100000003")
```

`_conv`, `_msg` y `_outbox` son helpers del archivo de test: hacen `insert … returning id` y un `select` sobre `whatsapp_outbox where message_id = %s`.

- [ ] **Step 2: Correrlos y ver que fallan**

Run: `cd backend && PV_REQUIRE_DB=1 python -m pytest -q tests/test_whatsapp_schema.py`
Expected: FAIL, con `column "wa_id" of relation "conversations" does not exist`.

- [ ] **Step 3: Escribir `0034_whatsapp.sql`** con lo descrito en Interfaces. La función del trigger es `security definer` con `set search_path = public, pg_temp`, igual que las de `0016_team.sql`.

- [ ] **Step 4: Aplicar la migración dos veces seguidas y correr los tests**

Run: `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/0034_whatsapp.sql` (dos veces), y después `PV_REQUIRE_DB=1 python -m pytest -q tests/test_whatsapp_schema.py`
Expected: la segunda aplicación termina sin errores y queda `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0034_whatsapp.sql backend/tests/test_whatsapp_schema.py
git commit -m "feat(whatsapp): tablas de conexión, idempotencia y cola de salida"
```

### Tarea 2: Configuración, conexión de un local y firma

**Files:**
- Modify: `backend/app/config.py` (bloque nuevo `# --- WhatsApp (Cloud API de Meta) ---`)
- Modify: `backend/.env.example`
- Create: `backend/app/whatsapp.py`
- Test: `backend/tests/test_whatsapp.py`

**Interfaces:**
- Consumes: las tablas de la Tarea 1.
- Produces:
  - Settings: `whatsapp_app_secret: str = Field(default="", repr=False)`, `whatsapp_verify_token: str = Field(default="", repr=False)`, `whatsapp_token_key: str = Field(default="", repr=False)`, `whatsapp_graph_version: str = "v25.0"`, `whatsapp_per_contact_hour: int = 60`.
  - `whatsapp.enabled() -> bool`: los tres secretos cargados.
  - `whatsapp.verify_signature(body: bytes, header: str | None) -> bool`: compara con `hmac.compare_digest`; `False` si falta el header o el secreto.
  - `whatsapp.connect(tenant_id: str, phone_number_id: str, waba_id: str, display_phone: str, token: str) -> None`: upsert por `tenant_id` con `status='connected'` y el token cifrado. Si el `phone_number_id` ya pertenece a otro negocio, levanta `whatsapp.NumberTaken`.
  - `whatsapp.tenant_for(phone_number_id: str) -> str | None`: devuelve el negocio sólo si la conexión está `connected`.
  - `whatsapp._token(tenant_id: str) -> str`: descifra el token. Es privado y sólo lo usa el envío.
  - CLI: `python -m app.whatsapp connect --tenant UUID --phone-number-id ID --waba-id ID --display-phone "+1 555 165 4354"`. Lee el token de la variable `WHATSAPP_CONNECT_TOKEN`, nunca de los argumentos, así no queda en el historial de la terminal.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_firma_valida_e_invalida(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "s3cr3t")
    body = b'{"a":1}'
    good = "sha256=" + hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
    assert whatsapp.verify_signature(body, good)
    assert not whatsapp.verify_signature(body, "sha256=" + "0" * 64)
    assert not whatsapp.verify_signature(body, None)

def test_connect_cifra_y_resuelve_tenant(wa_settings, raw_conn):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1 555 000 0001", "EAAtoken")
    assert whatsapp.tenant_for("PNID-C") == TENANT_C
    stored = _row(raw_conn, "select token_encrypted from whatsapp_connections where tenant_id = %s", TENANT_C)
    assert "EAAtoken" not in stored["token_encrypted"]
    assert whatsapp._token(TENANT_C) == "EAAtoken"

def test_numero_de_otro_negocio(wa_settings):
    whatsapp.connect(TENANT_C, "PNID-X", "WABA-C", "+1", "t1")
    with pytest.raises(whatsapp.NumberTaken):
        whatsapp.connect(TENANT_D, "PNID-X", "WABA-D", "+1", "t2")

def test_desconectado_no_resuelve(wa_settings, raw_conn):
    whatsapp.connect(TENANT_C, "PNID-OFF", "WABA-C", "+1", "t")
    _exec(raw_conn, "update whatsapp_connections set status = 'disconnected' where tenant_id = %s", TENANT_C)
    assert whatsapp.tenant_for("PNID-OFF") is None
```

`wa_settings` es un fixture del archivo: carga secretos de prueba (y una clave con `Fernet.generate_key()`) con `monkeypatch` y borra `whatsapp_connections`, `whatsapp_inbound` y las conversaciones con `wa_id` al terminar.

- [ ] **Step 2: Correrlos y ver que fallan**

Run: `PV_REQUIRE_DB=1 python -m pytest -q tests/test_whatsapp.py`
Expected: FAIL, con `ModuleNotFoundError: No module named 'app.whatsapp'`.

- [ ] **Step 3: Implementar** lo de Interfaces en `config.py` y `whatsapp.py`. En `.env.example`, agregar las cinco variables vacías con un comentario de dónde se sacan: App Secret en Configuración de la app → Básica; el token de verificación lo inventamos nosotros; la clave con `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

- [ ] **Step 4: Correr los tests**

Run: `PV_REQUIRE_DB=1 python -m pytest -q tests/test_whatsapp.py`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/.env.example backend/app/whatsapp.py backend/tests/test_whatsapp.py
git commit -m "feat(whatsapp): conexión de un local con token cifrado y verificación de firma"
```

### Tarea 3: Envío, reintentos y ventana de 24 horas

**Files:**
- Modify: `backend/app/whatsapp.py`
- Modify: `backend/app/worker.py` (`"whatsapp_messages": whatsapp.deliver_due()` en `run_once`)
- Modify: `backend/app/main.py` (después de `inbox.reply` en `POST /app/inbox/{conversation_id}/reply`, llamar `whatsapp.deliver_due(conversation_id=...)` fuera de la transacción)
- Test: `backend/tests/test_whatsapp.py`

**Interfaces:**
- Consumes: `whatsapp_outbox` (Tarea 1), `_token` (Tarea 2).
- Produces:
  - `whatsapp.conversation_for(tenant_id: str, wa_id: str) -> str`: busca o crea la conversación (canal `whatsapp`) con `insert … on conflict do nothing` y un `select` después.
  - `whatsapp.deliver_due(limit: int = 20, budget_s: float = 20.0, conversation_id: str | None = None) -> int`: reclama de a una las filas `pending` vencidas, como `webhooks.deliver_due` (corre `next_attempt_at` 2 minutos con `for update skip locked` y hace el POST fuera de la transacción). Devuelve cuántas procesó.
  - `whatsapp.RETRY_DELAYS_S = (30, 120, 600)`: con un error, reintenta con esas esperas. Después del último intento queda `failed`.
  - `whatsapp.split_text(text: str, limit: int = 4096) -> list[str]`: corta en saltos de línea cuando puede y nunca devuelve una parte de más de `limit` caracteres.
  - El texto a mandar es `messages.content`. Si `payload.payment.url` existe y no está en el texto, se agrega al final en una línea propia. Cada parte va como `{"messaging_product": "whatsapp", "to": wa_id, "type": "text", "text": {"body": parte}}`.
  - Si `last_customer_message_at` tiene más de 24 horas (o es null), la fila pasa a `window_closed` sin llamar a Meta y no se reintenta.
  - Si sale bien, guarda `status='sent'`, `wamid` (el `messages[0].id` de la respuesta de Meta) y `sent_at`.
  - `whatsapp._client() -> httpx.Client`: `timeout=15`, `follow_redirects=False`, `trust_env=False`. Es lo que reemplazan los tests.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_split_text():
    parts = whatsapp.split_text("a" * 5000)
    assert [len(p) for p in parts] == [4096, 904]
    assert whatsapp.split_text("hola") == ["hola"]

def test_respuesta_larga_en_partes(wa_settings, sent):
    conv = _wa_conv(TENANT_C, "5491100000020")   # connect + conversación + mensaje entrante reciente
    opportunities.add_message(TENANT_C, conv, "outbound", "x" * 5000)
    whatsapp.deliver_due(conversation_id=conv)
    assert [len(m["text"]["body"]) for m in sent] == [4096, 904]

def test_ventana_cerrada_no_se_manda(wa_settings, sent, raw_conn):
    conv = _wa_conv(TENANT_C, "5491100000021")
    _exec(raw_conn, "update conversations set last_customer_message_at = now() - interval '25 hours' where id = %s", conv)
    opportunities.add_message(TENANT_C, conv, "outbound", "tu pedido salió")
    whatsapp.deliver_due(conversation_id=conv)
    assert sent == [] and _outbox_status(conv) == "window_closed"

def test_error_de_meta_reintenta_y_despues_falla(wa_settings, failing_sent, raw_conn):
    conv = _wa_conv(TENANT_C, "5491100000022")
    opportunities.add_message(TENANT_C, conv, "outbound", "hola")
    for _ in range(len(whatsapp.RETRY_DELAYS_S) + 1):
        _exec(raw_conn, "update whatsapp_outbox set next_attempt_at = now() where conversation_id = %s", conv)
        whatsapp.deliver_due(conversation_id=conv)
    assert _outbox_status(conv) == "failed"

def test_link_de_pago_se_agrega(wa_settings, sent):
    conv = _wa_conv(TENANT_C, "5491100000023")
    opportunities.add_message(TENANT_C, conv, "outbound", "Te dejo el link.", {"payment": {"url": "https://pago.test/x"}})
    whatsapp.deliver_due(conversation_id=conv)
    assert sent[0]["text"]["body"].endswith("https://pago.test/x")

def test_respuesta_de_la_bandeja_sale_por_whatsapp(wa_settings, sent, owner_client):
    conv = _wa_conv(TENANT_C, "5491100000024")
    r = owner_client.post(f"/app/inbox/{conv}/reply", json={"text": "Hola, soy Juan del local"})
    assert r.status_code == 200 and sent[-1]["text"]["body"] == "Hola, soy Juan del local"
```

`failing_sent` es como `sent`, pero contesta 500. Para `owner_client`, reusar el fixture de cuentas y JWT que ya usan los tests de la bandeja (`tests/test_inbox*.py`).

- [ ] **Step 2: Correrlos y ver que fallan**

Run: `PV_REQUIRE_DB=1 python -m pytest -q tests/test_whatsapp.py -k "split or larga or ventana or reintenta or link or bandeja"`
Expected: FAIL (`AttributeError: split_text` / `deliver_due` / `conversation_for`).

- [ ] **Step 3: Implementar** `conversation_for`, `deliver_due`, `split_text` y `_client`. Agregar la línea en `worker.run_once` y la llamada en la ruta de la bandeja.

- [ ] **Step 4: Correr toda la suite**

Run: el mismo comando.
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/whatsapp.py backend/app/worker.py backend/app/main.py backend/tests/test_whatsapp.py
git commit -m "feat(whatsapp): envío por la Graph API con reintentos y ventana de 24 h"
```

### Tarea 4: Ruta de avisos y mensajes entrantes

**Files:**
- Create: `backend/app/whatsapp_routes.py`
- Modify: `backend/app/whatsapp.py`
- Modify: `backend/app/main.py` (`app.include_router(whatsapp_routes.router)` junto al de audio)
- Modify: `backend/app/domain/privacy.py` (`redact_conversation`)
- Test: `backend/tests/test_whatsapp.py`

**Interfaces:**
- Consumes: `verify_signature`, `tenant_for` (Tarea 2); `conversation_for` y `deliver_due` (Tarea 3); `sales_agent.handle_sales_message(tenant_id, message, conversation_id, channel=...)`; `customer_memory.identify(tenant, channel, key)` y `link_conversation`; `privacy.is_blocked`; `limits.hit(scope, key, limit, window_s)`.
- Produces:
  - `GET /channels/whatsapp/webhook`: si `hub.mode == "subscribe"` y `hub.verify_token` coincide con la configuración, responde `hub.challenge` en texto plano con 200. Si no, 403. La ruta no es `/webhooks/whatsapp` porque `POST /webhooks/{provider}` ya es la de pagos.
  - `POST /channels/whatsapp/webhook`: con firma inválida o WhatsApp apagado responde 403 sin leer el JSON. Con firma válida responde 200 `{"ok": true}` y programa `whatsapp.process_payload(payload)` con `BackgroundTasks`.
  - `whatsapp.process_payload(payload: dict) -> int`: recorre `entry[].changes[].value`, procesa `messages[]` y `statuses[]` y devuelve cuántos mensajes nuevos procesó.
  - `whatsapp.UNSUPPORTED_REPLY = "Por ahora entiendo mensajes de texto. ¿Me lo escribís?"`. La etapa 2 suma fotos y audios.
- Por cada mensaje:
  1. Se resuelve el negocio con `metadata.phone_number_id`. Si da `None`, se saltea.
  2. Se inserta el `wamid` en `whatsapp_inbound` con `on conflict do nothing`. Si ya estaba, se saltea.
  3. Se obtiene la conversación con `conversation_for`. Se identifica al cliente con la clave `f"whatsapp:{wa_id}"` (`identify` exige 16 caracteres o más) y se vincula.
  4. Si la conversación está bloqueada (`privacy.is_blocked`) o el contacto pasó `whatsapp_per_contact_hour` mensajes en la hora (`limits.hit("wa-contact", f"{tenant}:{wa_id}", …, 3600)`), se saltea.
  5. Si es `type == "text"`, se llama a `handle_sales_message(tenant, text.body, conv, channel="whatsapp")`. Si es otro tipo, se agrega el mensaje entrante `"[{type}]"` y la respuesta `UNSUPPORTED_REPLY` con `opportunities.add_message`.
  6. Al final, `deliver_due(conversation_id=conv)`.
- Por cada `statuses[]` con `status == "failed"`: se marca la fila de `whatsapp_outbox` con ese `wamid` como `failed`, con `last_error` = `errors[0].code` + `title`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_verificacion_get(client, wa_settings):
    r = client.get("/channels/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "42"})
    assert r.status_code == 200 and r.text == "42"
    assert client.get("/channels/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "42"}).status_code == 403

def test_post_firma_invalida_403(client, wa_settings):
    assert client.post("/channels/whatsapp/webhook", content=b"{}", headers={"X-Hub-Signature-256": "sha256=00"}).status_code == 403

def test_texto_lo_contesta_el_agente(wa_settings, sent):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    assert whatsapp.process_payload(_payload("PNID-C", "wamid.1", "5491100000010", "hola, tienen canillas?")) == 1
    conv = whatsapp.conversation_for(TENANT_C, "5491100000010")
    assert _directions(conv) == ["inbound", "outbound"]
    assert sent[0]["to"] == "5491100000010"

def test_mismo_wamid_dos_veces_una_respuesta(wa_settings, sent):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    p = _payload("PNID-C", "wamid.dup", "5491100000011", "hola")
    whatsapp.process_payload(p); whatsapp.process_payload(p)
    assert len(sent) == 1

def test_numero_no_conectado_se_ignora(wa_settings, sent):
    assert whatsapp.process_payload(_payload("PNID-NADIE", "wamid.2", "5491100000012", "hola")) == 0
    assert sent == []

def test_tope_por_contacto(wa_settings, sent, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_per_contact_hour", 2)
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    for i in range(4):
        whatsapp.process_payload(_payload("PNID-C", f"wamid.f{i}", "5491100000013", "hola"))
    assert len(sent) == 2

def test_redactar_conversacion_borra_el_numero(wa_settings, sent, raw_conn):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    whatsapp.process_payload(_payload("PNID-C", "wamid.r", "5491100000015", "hola"))
    conv = whatsapp.conversation_for(TENANT_C, "5491100000015")
    with tenant_tx(TENANT_C) as cur:
        privacy.redact_conversation(cur, TENANT_C, OWNER_UID, conv)
    assert _row(raw_conn, "select wa_id from conversations where id = %s", conv)["wa_id"] is None

def test_imagen_respuesta_amable(wa_settings, sent):
    whatsapp.connect(TENANT_C, "PNID-C", "WABA-C", "+1", "t")
    whatsapp.process_payload(_payload("PNID-C", "wamid.3", "5491100000014", None, type_="image"))
    assert sent[0]["text"]["body"] == whatsapp.UNSUPPORTED_REPLY
```

`sent` es un fixture que reemplaza `whatsapp._client` por un `httpx.Client(transport=httpx.MockTransport(...))`. Guarda cada JSON enviado y contesta 200 con `{"messages": [{"id": "wamid.out.N"}]}`. `_payload` arma el JSON con la forma documentada por Meta (`object`, `entry[].changes[].value.metadata.phone_number_id`, `contacts[].wa_id`, `messages[]`). `limits` está en 0 en `conftest` para los límites de la web; el de WhatsApp usa su propio setting.

- [ ] **Step 2: Correrlos y ver que fallan**

Run: `PV_REQUIRE_DB=1 python -m pytest -q tests/test_whatsapp.py -k "verificacion or firma_invalida or agente or wamid or conectado or tope or imagen"`
Expected: FAIL (404 en la ruta y `AttributeError: process_payload`).

- [ ] **Step 3: Implementar** las rutas en `whatsapp_routes.py`: el cuerpo crudo con `await request.body()` y la firma antes de `json.loads`. Implementar `process_payload` en `whatsapp.py`. En `privacy.redact_conversation` (`backend/app/domain/privacy.py`), poner también `conversations.wa_id = null`. El número del cliente es un dato personal (spec, «Seguridad y privacidad»). Una vez redactada, si el contacto vuelve a escribir, empieza una conversación nueva.

- [ ] **Step 4: Correr los tests**

Run: el mismo comando, con `or redactar` agregado al `-k`, y después toda la suite: `PV_REQUIRE_DB=1 python -m pytest -q`.
Expected: `8 passed`, y la suite completa en verde (unos 600 tests) sin fallas nuevas.

- [ ] **Step 5: Commit**

```bash
git add backend/app/whatsapp.py backend/app/whatsapp_routes.py backend/app/main.py backend/tests/test_whatsapp.py
git commit -m "feat(whatsapp): avisos de Meta firmados y mensajes de texto al agente"
```

### Tarea 5: Prueba real con el número de prueba de Meta

Requiere que Meta haya desbloqueado la cuenta (hoy da el error 131031) y que alguno de los dos esté con la app de Meta abierta. No lleva código nuevo, sólo documentación y una verificación manual.

**Files:**
- Create: `docs/whatsapp-pruebas.md` (paso a paso)

- [ ] **Step 1: Escribir `docs/whatsapp-pruebas.md`** con estos pasos:
  1. Cargar en `backend/.env` las variables de la Tarea 2. El App Secret sale de Configuración de la app → Básica.
  2. Levantar la API local y exponerla con un túnel HTTPS (`cloudflared tunnel --url http://127.0.0.1:8077`).
  3. En la app de Meta, en WhatsApp → Configuración, poner como URL de devolución de llamada `https://<túnel>/channels/whatsapp/webhook`, el mismo token de verificación, y suscribirse al campo `messages`.
  4. Conectar el número de prueba al negocio C: `WHATSAPP_CONNECT_TOKEN=<token> python -m app.whatsapp connect --tenant 0000000c-0000-0000-0000-00000000000c --phone-number-id 1389172324285219 --waba-id 2571440663368022 --display-phone "+1 555 165 4354"`.
  5. Desde un celular de la lista de destinatarios, escribirle «hola, tienen canillas?» al +1 555 165 4354.
- [ ] **Step 2: Verificar a mano.** Esperado: llega la respuesta del agente con productos del catálogo del negocio C, y en el panel del negocio C la conversación aparece en la bandeja con los dos mensajes.
- [ ] **Step 3: Commit**

```bash
git add docs/whatsapp-pruebas.md
git commit -m "docs(whatsapp): cómo probar con el número de prueba de Meta"
```

---

**Fuera de este plan** (planes aparte, en el orden del spec): etapa 2 (botones y listas, fotos, audios OGG/Opus, comprobantes por WhatsApp), etapa 3 (mensajes del dueño desde la app, pausa, timer, vencimiento a las 2 h, el agente lee todo al retomar, interruptor del local, y mostrar en la bandeja los envíos que fallaron o quedaron fuera de la ventana), etapa 4 (Embedded Signup y desconexión) y etapa 5 (piloto con coexistencia).

*Ponytail:* los avisos que salen fuera de un turno (pago, reparto, envío) esperan al worker, que corre cada 60 s. Si hace falta inmediatez, se llama a `deliver_due(conversation_id=…)` también en esos lugares.
