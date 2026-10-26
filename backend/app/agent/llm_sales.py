"""Planner con LLM para el agente de ventas: el modelo interpreta y elige herramientas; el servidor
ejecuta, decide y controla.

Garantías (las mismas que con reglas):
- Las herramientas son las del planner determinista (`_Turn`): el tenant sale del ToolContext,
  precios/stock/estados salen de la base. El modelo no ve IDs de otra empresa ni SQL.
- El modelo NO puede generar pedidos ni links de pago: sólo `preparar_compra` (resumen). El "sí"
  del cliente lo procesa el servidor de forma determinista en el turno siguiente.
- Control de la respuesta: todo precio ($), cantidad disponible, número de pedido o link que
  escriba el modelo tiene que haber salido de una herramienta en este turno (o del carrito
  vigente). Si no, se descarta lo que escribió y se responde con el texto de las herramientas.
- Si el modelo falla o no responde, `run` devuelve None y responde el planner por reglas.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Optional

import httpx

from ..config import settings
from ..db import tenant_tx
from ..domain import opportunities, orders
from .sales_agent import _Turn, _money

log = logging.getLogger(__name__)

# planner(messages, tools) -> {"content": str, "tool_calls": [{"name": str, "arguments": dict}]}
Planner = Callable[[list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]]

MAX_STEPS = 5
HISTORY = 16

_TOOLS: list[dict[str, Any]] = [
    {"name": "buscar_productos",
     "description": "Busca en el catálogo de ESTE negocio. Devuelve opciones numeradas con precio y "
                    "disponible reales. Usala para cualquier consulta de productos.",
     "parameters": {"type": "object", "properties": {
         "consulta": {"type": "string", "description": "qué busca el cliente, p. ej. 'canilla negra cocina'"},
         "precio_maximo": {"type": "number", "description": "presupuesto máximo en pesos, si lo dijo"}},
         "required": ["consulta"]}},
    {"name": "consultar_producto",
     "description": "Disponible y precio de UN producto: por número de la última lista o por descripción.",
     "parameters": {"type": "object", "properties": {
         "opcion": {"type": "integer"}, "consulta": {"type": "string"}}}},
    {"name": "agregar_al_carrito",
     "description": "Agrega un producto al carrito: por número de la última lista ('la 2') o por descripción.",
     "parameters": {"type": "object", "properties": {
         "opcion": {"type": "integer"}, "consulta": {"type": "string"},
         "cantidad": {"type": "integer", "minimum": 1}}}},
    {"name": "quitar_del_carrito",
     "description": "Quita un producto del carrito (por número de la última lista o descripción).",
     "parameters": {"type": "object", "properties": {
         "opcion": {"type": "integer"}, "consulta": {"type": "string"}}}},
    {"name": "ver_carrito", "description": "Carrito actual con total.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "preparar_compra",
     "description": "El cliente quiere comprar/pagar o no quiere sumar nada más: arma el resumen y "
                    "le pide confirmación. NO genera el pago: eso pasa sólo si el cliente responde 'sí'.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "estado_pedido",
     "description": "Estado real de los pedidos de esta conversación (pago, despacho).",
     "parameters": {"type": "object", "properties": {
         "cliente_dice_que_pago": {"type": "boolean"}}}},
]

_SYSTEM = """Sos el vendedor virtual de "{negocio}" (asistente virtual; no te hagas pasar por una persona).
Hablás en español rioplatense, cordial y breve. Texto plano: sin markdown, sin asteriscos ni tablas.

Reglas que no se rompen:
- Precios, stock, disponibilidad, pedidos y pagos SÓLO salen de las herramientas. Nunca inventes
  precios, cantidades, marcas, plazos de entrega, envíos ni compatibilidades técnicas.
- Si el cliente nombra una opción de la última lista ("la 2", "la primera", "esa negra"), usá
  agregar_al_carrito o consultar_producto con ese número.
- Si quiere comprar o dice que no quiere nada más y tiene carrito, usá preparar_compra.
  Vos no generás links de pago ni confirmás pedidos.
- "Ya pagué" no confirma nada: usá estado_pedido con cliente_dice_que_pago=true.
- Si una herramienta devuelve "texto", respondé con ese texto (podés acortarlo o hacerlo más
  natural, pero sin cambiar ni agregar números, productos ni links). Si mostrás opciones,
  usá exactamente la numeración que devolvió la herramienta.

Contexto actual de la conversación:
{contexto}"""


def default_planner() -> Optional[Planner]:
    if settings.llm_provider != "ollama":
        return None
    return _ollama_planner


def _ollama_planner(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
    headers = {}
    key = settings.ollama_api_key or settings.llm_api_key
    if key:
        headers["Authorization"] = f"Bearer {key}"
    resp = httpx.post(
        f"{settings.ollama_base_url.rstrip('/')}/api/chat",
        json={"model": settings.ollama_model, "messages": messages, "stream": False,
              "tools": [{"type": "function", "function": t} for t in tools]},
        headers=headers, timeout=settings.llm_timeout_s,
    )
    resp.raise_for_status()
    msg = resp.json().get("message", {})
    calls = []
    for c in msg.get("tool_calls") or []:
        fn = c.get("function", {})
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        calls.append({"name": fn.get("name", ""), "arguments": args if isinstance(args, dict) else {}})
    return {"content": (msg.get("content") or "").strip(), "tool_calls": calls}


# --- Contexto y herramientas ---------------------------------------------------------
def _business_name(tenant_id: str) -> str:
    with tenant_tx(tenant_id) as cur:
        cur.execute("select name from tenants where id = %s", (tenant_id,))
        row = cur.fetchone()
    return row["name"] if row else "el negocio"


def _context(turn: _Turn) -> str:
    lines = []
    shown = turn._shown()
    if shown:
        lines.append("Última lista mostrada al cliente:")
        lines += [turn._line(i, o) for i, o in enumerate(shown, 1)]
    cart = orders.get_cart(turn.tenant, turn.conv)
    lines.append("Carrito: " + (turn.cart_text(cart).replace("\n", " | ") if cart else "vacío"))
    recent = orders.conversation_orders(turn.tenant, turn.conv, limit=1)
    if recent:
        lines.append(f"Último pedido: #{recent[0]['number']} ({recent[0]['status_label']})")
    return "\n".join(lines)


def _int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None and str(value).strip() != "" else None
    except (TypeError, ValueError):
        return None


def _execute(turn: _Turn, name: str, args: dict[str, Any]) -> str:
    """Ejecuta la herramienta pedida con las funciones tenant-safe del agente. Devuelve el texto
    verificado que se le pasa al modelo (y que sirve de respuesta de respaldo)."""
    opcion, consulta = _int(args.get("opcion")), str(args.get("consulta") or "")
    if name == "buscar_productos":
        budget = args.get("precio_maximo")
        budget = float(budget) if isinstance(budget, (int, float)) and budget > 0 else None
        from ..domain.inventory import normalize
        return turn.search(normalize(consulta), budget)
    if name in ("consultar_producto", "agregar_al_carrito", "quitar_del_carrito"):
        o = turn.pick(opcion, consulta)
        if o is None:
            return ("No identifiqué cuál producto. Pedile al cliente que elija un número de la lista "
                    "o que lo describa.")
        if name == "consultar_producto":
            return turn.stock_offer(o)
        if name == "agregar_al_carrito":
            return turn.add_offer(o, _int(args.get("cantidad")) or 1)
        return turn.remove_offer(o)
    if name == "ver_carrito":
        turn.tool("ver_carrito", "consulta")
        return turn.cart_text(orders.get_cart(turn.tenant, turn.conv))
    if name == "preparar_compra":
        return turn.prepare_checkout("")
    if name == "estado_pedido":
        return turn.status(paid_claim=bool(args.get("cliente_dice_que_pago")))
    return "Herramienta no permitida."


# Herramientas cuyo texto llega al cliente TAL CUAL: cambian el carrito o piden el "sí" para
# cobrar, y el cliente tiene que ver exactamente qué lleva y el total antes de confirmar.
_VERBATIM = {"agregar_al_carrito", "quitar_del_carrito", "preparar_compra"}

# --- Control de la respuesta ------------------------------------------------------------
_RE_MONEY = re.compile(r"\$\s?(\d[\d.,]*)")
_RE_UNITS = re.compile(r"\b(\d+)\s+(?:disponibles?|unidades?)\b")
_RE_ORDER = re.compile(r"#\s?(\d+)")
_RE_URL = re.compile(r"https?://\S+")


def _amounts(text: str) -> set[int]:
    out = set()
    for raw in _RE_MONEY.findall(text):
        digits = re.sub(r"[.,]\d{1,2}$", "", raw).replace(".", "").replace(",", "")
        if digits.isdigit():
            out.add(int(digits))
    return out


def _verified(reply: str, evidence: str) -> bool:
    """Todo dato duro de la respuesta debe estar en la evidencia de herramientas/carrito."""
    if not _amounts(reply) <= _amounts(evidence):
        return False
    if not set(_RE_UNITS.findall(reply)) <= set(_RE_UNITS.findall(evidence)) | {
            m for m in re.findall(r"\bhay (\d+)", evidence)}:
        return False
    if not set(_RE_ORDER.findall(reply)) <= set(_RE_ORDER.findall(evidence)):
        return False
    return set(_RE_URL.findall(reply)) <= set(_RE_URL.findall(evidence))


def run(turn: _Turn, message: str, conversation_id: str, planner: Planner) -> Optional[str]:
    """Bucle de herramientas. Devuelve la respuesta, o None si el modelo no está disponible y
    todavía no ejecutó nada (entonces responde el planner por reglas)."""
    history = opportunities.get_recent_messages(turn.tenant, conversation_id, limit=HISTORY)
    messages: list[dict[str, Any]] = [{"role": "system", "content": _SYSTEM.format(
        negocio=_business_name(turn.tenant), contexto=_context(turn))}] + history
    if not history or history[-1].get("content") != message:
        messages.append({"role": "user", "content": message})
    outputs: list[str] = []
    verbatim: list[str] = []
    reply = ""
    try:
        for _ in range(MAX_STEPS):
            resp = planner(messages, _TOOLS)
            calls = [c for c in resp.get("tool_calls") or [] if c.get("name")]
            if not calls:
                reply = (resp.get("content") or "").strip()
                break
            messages.append({"role": "assistant", "content": resp.get("content") or "",
                             "tool_calls": [{"function": {"name": c["name"], "arguments": c.get("arguments") or {}}}
                                            for c in calls]})
            for c in calls:
                out = _execute(turn, c["name"], c.get("arguments") or {})
                outputs.append(out)
                if c["name"] in _VERBATIM:
                    verbatim.append(out)
                messages.append({"role": "tool", "tool_name": c["name"], "content": json.dumps({"texto": out}, ensure_ascii=False)})
    except Exception:  # noqa: BLE001 - modelo caído o respuesta inválida
        log.exception("planner LLM de ventas falló")
        if not outputs:
            return None
    fallback = "\n\n".join(outputs[-2:]) if outputs else None
    if verbatim:
        return "\n\n".join(verbatim[-2:])
    if not reply:
        return fallback
    reply = reply.replace("**", "").replace("__", "")
    cart = orders.get_cart(turn.tenant, turn.conv)
    evidence = "\n".join(outputs + [_context(turn), turn.cart_text(cart)])
    if cart:
        evidence += "\n" + " ".join(_money(it["unit_price"]) for it in cart["items"])
    if not _verified(reply, evidence):
        log.warning("respuesta del LLM descartada por datos no verificados")
        turn.tool("control", "respuesta del modelo descartada: datos no verificados")
        return fallback or None
    if turn.payment and turn.payment["checkout_url"] not in reply:
        reply += f"\n{turn.payment['checkout_url']}"
    return reply
