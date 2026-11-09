# Audio web: contrato backend, 04/11/2026

> **Actualización documental 09/11:** el código de audio web se integró en main con el PR #67 el 04/11. El contrato y los pendientes que siguen son el handoff histórico de esa entrega, no el estado técnico actual. Consultar [current-state.md](current-state.md). Esta actualización no acredita pruebas reales de ElevenLabs.

Entrega coordinada sobre base `562a6383ba57e6e0b83769ff853c89b0335f45f9`.
Owner del patch: Codex personal; revisor pendiente: Claude en contexto fresco.
Este documento describe implementación propuesta, no evidencia de ejecución ni revisión independiente.
Sin herramientas, DB, proveedor real, commits, publicación ni cambios a `.env` en este corte.
Modelo/esfuerzo solicitados: gpt-6.1-sol high; no verificados mediante herramientas.

## API para la UI

- `GET /public/{slug}/audio`: capacidades públicas, `Cache-Control: no-store`.
  Devuelve `enabled`, `input_mime: "audio/wav"`, `sample_rate_hz: 16000`, `channels: 1`,
  `sample_width_bits: 16`, `max_upload_bytes`, `max_duration_seconds`,
  `max_tts_characters` y `max_transcript_characters: 2000`.
  Slug inexistente: 404. Audio incompleto o tenant no habilitado: `enabled: false`.
- `POST /public/{slug}/audio/transcriptions`: cuerpo binario WAV, `Content-Type: audio/wav`.
  Único query permitido: `conversation_id` UUID opcional. Con conversación exige su
  `X-Conversation-Token` y comprueba que no esté bloqueada. Sin conversación no crea ninguna.
  Respuesta: `{ "text": "...", "duration_seconds": 0.1 }`. Texto vacío representa silencio.
  Duración calculada desde frames PCM realmente leídos, no desde una duración del cliente.
- `POST /public/{slug}/conversations/{conversation_id}/messages/{message_id}/audio`:
  sin query ni cuerpo; exige `X-Conversation-Token`. Sólo mensajes outbound persistidos
  del tenant y conversación acreditados. Respuesta binaria `audio/mpeg`, sin caché y con nosniff.
  No acepta texto, URL, voz o modelo. No sintetiza textos mayores al límite ni los trunca.
- La lectura existente `GET /public/{slug}/conversations/{conversation_id}` agrega `id`
  UUID de servidor a cada mensaje; conserva role/content/ui y orden. El helper compartido
  también agrega ese campo a sus otros consumidores. La respuesta de chat no cambia:
  después de enviar, la UI debe recuperar el historial acreditado para obtener IDs persistidos.

Errores conservan `{ "detail": "..." }`: 400 subida inválida/interrumpida; 403 conversación
bloqueada; 404 audio apagado/recurso no acreditado; 408 timeout total de subida; 413 tamaño
o texto excesivo/cuerpo TTS no vacío; 415 MIME, codificación o WAV inválido; 422 parámetros
no admitidos, UUID inválida o mensaje vacío; 429 cuota con Retry-After; 502 respuesta externa
inválida/error; 503 DB/cuota no disponible; 504 timeout total de proveedor.
No reintentar automáticamente: un timeout puede haber consumido créditos.

## Límites y privacidad

Opt-in `AUDIO_DEMO_ENABLED`, tenant C/D exacto, key, voice y modelo backend válidos.
Sin esos datos no se abre el cliente HTTP. Límites numéricos positivos y acotados validados
al cargar Settings; una configuración numérica inválida impide arrancar.

Entrada limitada por chunks y deadline total, sin confiar en Content-Length. Sólo RIFF/WAVE
PCM mono 16 kHz/16 bits. Se valida tamaño RIFF y cantidad real de frames; se reconstruye un
WAV nuevo con ese PCM, descartando metadatos y chunks adicionales. No se interpreta audio
comprimido. La UI siguiente deberá convertir grabaciones/adjuntos a este formato, verificar
tamaño final y limitar su duración local; el backend vuelve a comprobarla antes del proveedor.

Reservas atómicas en `rate_limits`, sin migración: IP/min y conversación/hora cuando existe,
llamadas combinadas por tenant/día y global/día, bytes WAV normalizados STT por tenant/global
y caracteres TTS por tenant/global. Ventanas fijas UTC; pueden permitir ráfagas en sus bordes.
UPSERT condicional en orden estable y rollback completo si un eje falla. DB caída falla cerrado.
No devuelve reservas por error, cancelación ni timeout; no hay retries ni caché de resultados.
Los contadores son compartidos entre instancias y no almacenan IP/IDs en claro.
Conservar TRUSTED_PROXY_HOPS correcto; límites IP dependen de la topología existente.

Los bytes STT corresponden a PCM de tasa fija cuya duración se verificó. Estas unidades y
llamadas acotan uso, pero no prometen dinero ni tarifas: configurar un freno de gasto en el
proveedor antes de habilitar consumo real. TTS tiene límite de texto y respuesta MP3.
Respuestas externas se leen incrementalmente con límite de bytes y deadline total; STT JSON
también tiene límite de texto. MIME y magic MP3 se verifican; no se verifica duración MP3.
HTTP fijo oficial, sin redirects, proxies del entorno, SDK adicional o URLs del cliente.

Audio/transcripción sólo viven en memoria de la request y se envían al proveedor al solicitarlo.
No se guardan originales, ni transcripciones automáticamente, ni logs de cuerpos/secretos.
La UI envía la transcripción al chat como mensaje del comprador. No se promete zero-retention en
ElevenLabs: `enable_logging=false` es exclusivo enterprise y no se envía.

## Validación y continuación

Primero aplicar sólo pruebas y ejecutar desde backend `python -m pytest -q audio_tests`;
registrar la falla de colección por módulo ausente. Aplicar producto y repetir ese comando.
No hay resultados ejecutados en esta entrega. Integración preparada, sólo cuando se autorice
DB dedicada: `python -m pytest -q tests/test_audio_web.py tests/test_public_conversation_access.py tests/test_limits.py`
con `PV_REQUIRE_DB=1`; después suite backend `python -m pytest -q audio_tests tests`.
Los transportes de pruebas son httpx MockTransport y todo contenido es sintético.
Pendientes: evidencia roja/verde, revisión Claude, UI, build/navegador, aceptación e integración.
`current-state.md` no fue adjuntado: coordinación debe registrar allí este handoff y la evidencia
real posterior. No se ejecutó indexación derivada.

## UI web (tienda pública)

`web/src/components/VoiceInput.tsx` sobre el chat de `Sales.tsx`; sólo en la tienda pública y sólo
si `GET /public/{slug}/audio` responde `enabled: true` (si falla o es `false`, no se muestra nada).
Nota de voz estilo WhatsApp: `Mandar audio` → `Enviar audio` (o tope `max_duration_seconds`, o `Adjuntar`
archivo ≤ 25 MB) → `web/src/lib/wav.ts` convierte a WAV PCM mono 16 kHz/16 bits → se transcribe y el texto
se manda solo al chat, sin revisión (nada sale antes; `Cancelar` descarta; vacío da error). La burbuja
muestra «Tu audio» y lo entendido entre «…»; tras responder se relee el historial y se pide TTS de la última
respuesta con autoplay. Mensajes escritos: `Escuchar` manual. Sin reintentos; deshabilitado mientras envía.

Pruebas: `node --test src/lib/wav.test.mjs` (cabecera WAV) y `e2e/audio-web.mjs` (Chrome headless
propio, micrófono falso y frontera HTTP del backend simulada; ver cabecera del script). No validan
STT/TTS reales de ElevenLabs.
