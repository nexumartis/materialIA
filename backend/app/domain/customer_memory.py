"""Memoria del cliente entre conversaciones (por negocio).

- Identidad: por canal (web = clave del dispositivo, WhatsApp = teléfono). Se guarda sólo
  SHA-256(tenant + clave): la misma persona en dos negocios no es correlacionable.
- Memoria semántica: hasta MAX_FACTS hechos cortos ("prefiere grifería negra", "compra para una
  obra"), destilados EN SEGUNDO PLANO por el worker cuando la conversación queda inactiva.
  Nunca guarda precios, stock, medios de pago ni datos de contacto.
- Memoria episódica: los pedidos anteriores del cliente se consultan cuando hacen falta
  (herramienta `historial_cliente`), no se copian al prompt.
- El cliente puede pedir que se lo olvide.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

from ..config import settings
from ..db import system_tx, tenant_tx
from . import orders

MAX_FACTS = 8
FACT_CHARS = 120

# Lo que nunca entra a la memoria: montos y monedas, cualquier número de 3+ cifras (teléfonos,
# alturas de calle, importes, aunque vengan separados por espacios o guiones), emails, direcciones
# y medios de pago. Ante la duda se descarta el hecho entero.
_FORBIDDEN = re.compile(
    r"\$|\d(?:[\s.\-]?\d){2,}|@|\bav\.|\b(pesos?|d[oó]lares?|usd|ars|precio|pag[oó]|abon[oó]|cbu|cvu|alias|"
    r"tarjeta|contraseñ\w*|clave|calle|avenida|piso|depto|dpto|departamento|direcci[oó]n|"
    r"tel[eé]fono|celular|whatsapp|dni|cuit|cuil|mail|email)\b", re.I)


def _key_hash(tenant_id: str, key: str) -> bytes:
    return hashlib.sha256(f"{tenant_id}:{key}".encode()).digest()


def identify(tenant_id: str, channel: str, key: str, create: bool = True) -> Optional[str]:
    """Cliente de esta clave en este negocio; lo crea la primera vez (si `create`). None si la
    clave no sirve o no existe."""
    if not key or len(key) < 16 or len(key) > 200:
        return None
    digest = _key_hash(tenant_id, key)
    with tenant_tx(tenant_id) as cur:
        cur.execute("select customer_id from customer_identities "
                    "where tenant_id = %s and channel = %s and key_hash = %s",
                    (tenant_id, channel, digest))
        row = cur.fetchone()
        if row or not create:
            return str(row["customer_id"]) if row else None
        cur.execute("insert into demo_customers (tenant_id, display_name, contact_data, consent_status) "
                    "values (%s, %s, %s::jsonb, 'memory_notice') returning id",
                    (tenant_id, f"Cliente {channel}", json.dumps({"canal": channel})))
        customer_id = str(cur.fetchone()["id"])
        cur.execute("insert into customer_identities (tenant_id, channel, key_hash, customer_id) "
                    "values (%s, %s, %s, %s) on conflict do nothing",
                    (tenant_id, channel, digest, customer_id))
        cur.execute("select customer_id from customer_identities "
                    "where tenant_id = %s and channel = %s and key_hash = %s",
                    (tenant_id, channel, digest))
        winner = str(cur.fetchone()["customer_id"])
        if winner != customer_id:     # otra request creó la identidad a la vez: sin huérfanos
            cur.execute("delete from demo_customers where tenant_id = %s and id = %s", (tenant_id, customer_id))
        return winner


def link_conversation(tenant_id: str, conversation_id: str, customer_id: str) -> None:
    with tenant_tx(tenant_id) as cur:
        cur.execute("update conversations set customer_id = %s "
                    "where tenant_id = %s and id = %s and customer_id is null",
                    (customer_id, tenant_id, conversation_id))


def customer_of(tenant_id: str, conversation_id: str) -> Optional[str]:
    with tenant_tx(tenant_id) as cur:
        cur.execute("select customer_id from conversations where tenant_id = %s and id = %s",
                    (tenant_id, conversation_id))
        row = cur.fetchone()
    return str(row["customer_id"]) if row and row["customer_id"] else None


def facts(tenant_id: str, customer_id: Optional[str]) -> list[str]:
    if not customer_id:
        return []
    with tenant_tx(tenant_id) as cur:
        cur.execute("select facts from customer_memory where tenant_id = %s and customer_id = %s",
                    (tenant_id, customer_id))
        row = cur.fetchone()
    return list(row["facts"] or []) if row else []


def history(tenant_id: str, customer_id: Optional[str], limit: int = 5) -> list[dict[str, Any]]:
    """Pedidos confirmados del cliente en TODAS sus conversaciones con este negocio."""
    if not customer_id:
        return []
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            f"select {', '.join('o.' + c.strip() for c in orders._ORDER_COLUMNS.split(','))} from orders o "
            "join conversations c on c.tenant_id = o.tenant_id and c.id = o.conversation_id "
            "where o.tenant_id = %s and c.customer_id = %s and o.status <> 'CART_OPEN' "
            "order by o.created_at desc limit %s", (tenant_id, customer_id, limit))
        return [orders._view(cur, r) for r in cur.fetchall()]


def forget(tenant_id: str, customer_id: Optional[str]) -> bool:
    """"Olvidarme": borra la memoria y las identidades; los pedidos quedan (registro comercial)
    pero desvinculados de la persona."""
    if not customer_id:
        return False
    with tenant_tx(tenant_id) as cur:
        # Los resúmenes también son memoria derivada de la persona.
        # summary_until = ahora: lo ya hablado no se vuelve a resumir.
        cur.execute("update conversations set customer_id = null, summary = null, summary_until = now() "
                    "where tenant_id = %s and customer_id = %s", (tenant_id, customer_id))
        cur.execute("update orders set customer_id = null where tenant_id = %s and customer_id = %s",
                    (tenant_id, customer_id))
        # Borra la persona: arrastra (cascade) su memoria y sus identidades.
        cur.execute("delete from demo_customers where tenant_id = %s and id = %s", (tenant_id, customer_id))
    return True


# --- Destilado en segundo plano --------------------------------------------------------
def sanitize(items: Any) -> list[str]:
    out: list[str] = []
    for item in items or []:
        text = re.sub(r"\s+", " ", str(item)).strip()[:FACT_CHARS]
        if text and not _FORBIDDEN.search(text) and text.lower() not in (x.lower() for x in out):
            out.append(text)
    return out[:MAX_FACTS]


_EXTRACT = """Extraés memoria de largo plazo de un cliente de un negocio, a partir de su conversación.
Devolvé JSON {"facts": ["...", ...]} con a lo sumo 8 hechos ÚTILES PARA ATENDERLO LA PRÓXIMA VEZ:
preferencias (colores, estilos, marcas), para qué compra, ambiente u obra, zona (sólo barrio o
ciudad), cómo prefiere que lo atiendan. Fusioná con los hechos previos; si algo cambió, quedate con
lo nuevo. Frases cortas en español, en tercera persona. PROHIBIDO: precios, montos, stock, números de
pedido, medios de pago, teléfonos, emails, direcciones exactas, datos sensibles. Si no hay nada
útil, devolvé los hechos previos."""


def _deterministic(previous: list[str], convs: list[dict[str, Any]], bought: list[dict[str, Any]]) -> list[str]:
    new: list[str] = []
    for o in bought:
        for it in o["items"]:
            new.append(f"Compró {it['name']}")
    for c in convs:
        q = (c["agent_state"] or {}).get("last_query") or {}
        parts = [*(q.get("keywords") or [])]
        if q.get("color"):
            parts.append(q["color"])
        if q.get("ambiente"):
            parts.append(f"para {q['ambiente']}")
        if parts:
            new.append("Buscó " + " ".join(parts))
    return sanitize(new + previous)


def refresh(tenant_id: str, customer_id: str, model: Any = None) -> list[str]:
    """Destila la memoria del cliente con lo nuevo desde la última vez. Idempotente."""
    from ..agent import llm_tasks

    with tenant_tx(tenant_id) as cur:
        # Reclamo: si otro worker está con este cliente, no se paga el modelo dos veces.
        cur.execute("select pg_try_advisory_xact_lock(hashtext(%s)) as ok", (f"memory:{customer_id}",))
        if not cur.fetchone()["ok"]:
            return facts(tenant_id, customer_id)
        return _refresh_locked(cur, tenant_id, customer_id, model, llm_tasks)


def _refresh_locked(cur: Any, tenant_id: str, customer_id: str, model: Any, llm_tasks: Any) -> list[str]:
    cur.execute("select facts, processed_until from customer_memory where customer_id = %s", (customer_id,))
    row = cur.fetchone()
    previous = list(row["facts"] or []) if row else []
    since = row["processed_until"] if row else None
    cur.execute(
        "select m.direction, m.content, m.created_at from messages m "
        "join conversations c on c.tenant_id = m.tenant_id and c.id = m.conversation_id "
        "where m.tenant_id = %s and c.customer_id = %s and (%s::timestamptz is null or m.created_at > %s) "
        "order by m.created_at limit 200", (tenant_id, customer_id, since, since))
    msgs = cur.fetchall()
    if not msgs:
        return previous
    cur.execute("select agent_state from conversations where tenant_id = %s and customer_id = %s",
                (tenant_id, customer_id))
    convs = cur.fetchall()
    until = msgs[-1]["created_at"]
    transcript = "\n".join(("Cliente: " if m["direction"] == "inbound" else "Vendedor: ") + m["content"][:400]
                           for m in msgs)
    data = llm_tasks.ask_json(_EXTRACT, f"Hechos previos: {json.dumps(previous, ensure_ascii=False)}\n\n"
                                        f"Conversación nueva:\n{transcript}", model)
    new_facts = sanitize(data.get("facts")) if data else _deterministic(previous, convs, history(tenant_id, customer_id))
    cur.execute(
        "insert into customer_memory (customer_id, tenant_id, facts, processed_until, updated_at) "
        "values (%s, %s, %s::jsonb, %s, now()) on conflict (customer_id) do update set "
        "facts = excluded.facts, processed_until = excluded.processed_until, updated_at = now()",
        (customer_id, tenant_id, json.dumps(new_facts, ensure_ascii=False), until))
    return new_facts


def refresh_due(limit: int = 20, model: Any = None) -> int:
    """Worker: clientes con mensajes nuevos y la conversación inactiva hace MEMORY_IDLE_MINUTES."""
    with system_tx() as cur:
        cur.execute(
            "select c.tenant_id, c.customer_id from conversations c "
            "left join customer_memory mem on mem.customer_id = c.customer_id "
            "where c.customer_id is not null "
            "and c.last_customer_message_at > now() - interval '30 days' "
            "group by c.tenant_id, c.customer_id, mem.processed_until "
            "having max(c.last_customer_message_at) < now() - make_interval(mins => %s) "
            "and (mem.processed_until is null or max(c.last_customer_message_at) > mem.processed_until) "
            "limit %s", (settings.memory_idle_minutes, limit))
        due = cur.fetchall()
    for r in due:
        refresh(str(r["tenant_id"]), str(r["customer_id"]), model)
    return len(due)
