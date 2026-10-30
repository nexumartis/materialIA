# Bandeja y toma de control humana — diseño (roadmap etapa 2)

**Origen:** [roadmap](../../roadmap.md), etapa 2. Tomi pidió avanzar sin ronda de preguntas («seguí con lo otro», 29/10/2026), así que lo marcado **(decisión de Claude)** no fue acordado: revisarlo.

## Por qué

Hoy, cuando el agente deriva (el cliente pide una persona, o el producto es a medida, sin precio o con precio vencido), sólo marca `requires_human` y crea una oportunidad. Nadie puede tomar esa conversación ni responderle al cliente, así que lo derivado queda sin atender. Es además la base para WhatsApp (etapa 3), que usará la misma conversación.

## Objetivo del corte

El dueño, desde el panel:

1. **Ve las conversaciones**, con filtros: *derivadas*, *con pedido*, *sin responder* (el último mensaje es del cliente) y *atendidas por mí*.
2. **Abre una conversación**: lee los mensajes, el carrito, los pedidos y los comprobantes.
3. **Toma el control**: el agente se pausa en esa conversación y los mensajes del cliente quedan guardados sin respuesta automática.
4. **Responde** como persona del negocio. El cliente lo ve en su chat como mensaje del equipo, distinto del asistente virtual.
5. **Devuelve la conversación al agente**: deja de estar derivada y el agente vuelve a responder.

## No-objetivos de este corte

- **Sugerencias del agente al humano.** Están en el roadmap, pero requieren correr el planner sin escribir en la conversación. Quedan para un corte siguiente **(decisión de Claude)**.
- **Notificaciones** (email, push, WhatsApp). No se promete ningún aviso que no exista.
- **Asignación entre varias personas.** Hoy una cuenta es un negocio; `taken_by` queda preparado.
- **Editar o borrar mensajes, adjuntos del humano.**

## Anti-objetivos

- Que el agente responda en una conversación tomada.
- Que el cliente crea que habla con una persona cuando responde el agente, o al revés.
- Que un negocio vea o escriba conversaciones de otro.
- Prometer en el chat tiempos o canales que no existen.

## Diseño

- **Migración 0010** (idempotente):
  - `conversations` suma `needs_human_at` (derivada desde), `taken_by` (`auth.users`, `on delete set null`) y `taken_at`.
  - Políticas `member_access`/`member_only` para `app_user` en `conversations` y `messages`.
  - `app_user` lee `conversations` **sólo por columnas**, sin `access_token_hash` ni `agent_state` **(decisión de Claude)**, y puede actualizar únicamente `needs_human_at`, `taken_by` y `taken_at`.
  - En `messages`, `app_user` tiene `select` e `insert`.
- **Derivación:** cuando un turno del agente termina con `requires_human`, se marca `needs_human_at` (si ya estaba marcada, se conserva la primera fecha).
- **Pausa:** `handle_sales_message` guarda el mensaje del cliente y, si la conversación está tomada, no corre el agente. Devuelve `reply=""` y `mode="human"`, sin escribir un mensaje del agente.
- **Mensaje humano:** `direction='outbound'` con `payload {"type": "human"}`; el actor queda en `audit_events`. Responder toma el control automáticamente si nadie lo tenía **(decisión de Claude)**.
- **Devolver:** limpia `taken_by` y `needs_human_at`. No agrega un mensaje al chat **(decisión de Claude)**.
- **Chat del comprador:**
  - las respuestas humanas se muestran como «Equipo de <negocio>»;
  - mientras la conversación está tomada, el chat se relee cada pocos segundos y avisa «Te está atendiendo una persona del negocio».
- **Panel:** página nueva «Conversaciones» (`#/conversaciones`) con lista y filtros a la izquierda y la conversación a la derecha; en celular, una debajo de la otra.

## Aceptación

- Derivar ⇒ aparece en *derivadas*. Tomar ⇒ el siguiente mensaje del cliente no recibe respuesta del agente. Responder ⇒ el cliente lo ve como «Equipo». Devolver ⇒ el agente vuelve a responder y deja de estar derivada.
- Otro negocio, una cuenta sin membresía o una UUID ajena reciben 404 o 403 y no modifican nada.
- El panel nunca expone `access_token_hash` ni `agent_state`.
- Prueba en navegador del recorrido completo y a 390 px.
