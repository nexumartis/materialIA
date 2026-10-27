"""Planner con LLM para el agente de ventas: el modelo interpreta y elige herramientas; el servidor
ejecuta, decide y controla.

Garantías (las mismas que con reglas):
- Las herramientas son las del planner determinista (`_Turn`): el tenant sale del ToolContext,
  precios/stock/estados salen de la base. El modelo no ve IDs de otra empresa ni SQL.
- El modelo NO puede generar pedidos ni links de pago: sólo `preparar_compra` (resumen). El "sí"
  del cliente lo procesa el servidor de forma determinista en el turno siguiente.
- Control de la respuesta: todo precio ($), cantidad disponible, número de pedido o link que
  escriba el modelo tiene que haber salido de una herramienta en este turno (o del carrito
  vigente), asociado al producto/pedido que nombra. Lo que afirma de un pedido (pagado, a pagar,
  despachado) tiene que coincidir con su estado en la base, y no puede ofrecer canales,
  descuentos ni plazos que el negocio no informa. Si no pasa, se le pide UNA reescritura sin
  herramientas; si tampoco pasa, responde el texto de las herramientas o el planner por reglas.
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
from ..domain.inventory import normalize
from .sales_agent import _RE_COMPARE, _Turn, _budget, _money, _social, _stems

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
     "description": "Agrega un producto al carrito: por número de la última lista ('la 2') o por descripción. "
                    "Suma la cantidad a la que ya había.",
     "parameters": {"type": "object", "properties": {
         "opcion": {"type": "integer"}, "consulta": {"type": "string"},
         "cantidad": {"type": "integer", "minimum": 1}}}},
    {"name": "quitar_del_carrito",
     "description": "Quita un producto del carrito (por número de la última lista o descripción).",
     "parameters": {"type": "object", "properties": {
         "opcion": {"type": "integer"}, "consulta": {"type": "string"}}}},
    {"name": "comparar_productos",
     "description": "Compara opciones de la última lista con los datos de su ficha (precio, stock, "
                    "características cargadas). Usala para comparar o recomendar entre opciones.",
     "parameters": {"type": "object", "properties": {
         "opciones": {"type": "array", "items": {"type": "integer"},
                      "description": "números de la última lista; vacío = todas"}}}},
    {"name": "ver_carrito", "description": "Carrito actual con total.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "preparar_compra",
     "description": "El cliente quiere comprar/pagar o no quiere sumar nada más: arma el resumen y "
                    "le pide confirmación. NO genera el pago: eso pasa sólo si el cliente responde 'sí'.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "consultar_envio",
     "description": "¿Se envía a una zona? Responde con las zonas que cargó el negocio.",
     "parameters": {"type": "object", "properties": {
         "zona": {"type": "string", "description": "barrio, ciudad o provincia que dijo el cliente"}},
         "required": ["zona"]}},
    {"name": "buscar_info_negocio",
     "description": "Busca en los documentos del negocio (fichas técnicas, garantías, políticas, "
                    "instalación). Usala para preguntas que no son de precio ni stock.",
     "parameters": {"type": "object", "properties": {"consulta": {"type": "string"}},
                    "required": ["consulta"]}},
    {"name": "historial_cliente",
     "description": "Compras anteriores de ESTE cliente con el negocio (\"lo mismo que la otra vez\").",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "estado_pedido",
     "description": "Estado real de los pedidos de esta conversación (pago, despacho).",
     "parameters": {"type": "object", "properties": {
         "cliente_dice_que_pago": {"type": "boolean"}}}},
]

_TONES = {
    "cercano": "español rioplatense, con voseo, cálido y breve",
    "profesional": "español rioplatense, con voseo, claro, prolijo y breve",
    "formal": "español neutro, tratando de usted, cortés y breve",
}

_SYSTEM = """Sos {vendedor}, vendedor/a virtual de "{negocio}" (asistente virtual; no te hagas pasar por una persona).
Hablás en {tono}. Texto plano: sin markdown, sin asteriscos ni tablas.

Reglas que no se rompen:
- Precios, stock, disponibilidad, pedidos y pagos SÓLO salen de las herramientas. Nunca inventes
  precios, cantidades, marcas, plazos de entrega, envíos ni compatibilidades técnicas.
- Sólo actuás en este chat con estas herramientas: no mandás emails, WhatsApp ni SMS, no llamás
  y no das descuentos, plazos ni promesas que no figuren en lo que informa el negocio.
- El "Contexto actual" (carrito, pedidos y su estado) manda sobre lo dicho antes en la charla:
  a un pedido pagado no se le pide pagar; uno en revisión lo resuelve una persona.
- Si el cliente nombra una opción de la última lista ("la 2", "la primera", "esa negra"), usá
  agregar_al_carrito o consultar_producto con ese número.
- Si quiere comprar o dice que no quiere nada más y tiene carrito, usá preparar_compra.
  Vos no generás links de pago ni confirmás pedidos.
- "Ya pagué" no confirma nada: usá estado_pedido con cliente_dice_que_pago=true.
- Si una herramienta devuelve "texto", respondé con ese texto (podés acortarlo o hacerlo más
  natural, pero sin cambiar ni agregar números, productos ni links). Si mostrás opciones,
  usá exactamente la numeración que devolvió la herramienta. Si cambiaste el carrito,
  incluí el total real.

Cómo conversar:
- Si el cliente agradece o se despide, respondé breve y cálido, sin herramientas ni preguntas de venta.
- Para comparar o recomendar entre opciones usá comparar_productos: sale de la ficha; no describas
  rasgos, usos ni ventajas que no figuren.
- Recomendá con la ficha (tipo, color, características), el precio y su presupuesto. Si un dato
  (medida, compatibilidad) no figura, decilo y ofrecé que lo confirme una persona.
- Si corrige algo (color, cantidad, presupuesto), conservá el resto de lo que pidió; si cambia de
  tipo de producto, buscá de cero. Cambiar una cantidad: quitar_del_carrito y agregar_al_carrito.
- Preguntá sólo lo que haga falta para avanzar.
Ejemplos de estilo (orientan, no se copian): «¡Gracias a vos! Que la disfrutes.» · «Con tu
presupuesto, la negra mate es la que entra y tiene stock.» · «En cromo para cocina no tengo;
¿te sirve negra?»

Lo que el negocio informa de sí mismo (podés repetirlo tal cual; si algo no está acá, decí que
lo confirma una persona del equipo):
{perfil}

{memoria}Contexto actual de la conversación:
{contexto}"""


def _memory_text(turn: _Turn) -> str:
    """Memoria de largo plazo y resumen: orientan, no son datos verificados (no son evidencia)."""
    parts = []
    facts = turn.memory()
    if facts:
        parts.append("Lo que sabemos de este cliente por conversaciones anteriores (orientativo, puede "
                     "haber cambiado; no lo afirmes como dato de stock o precio):\n"
                     + "\n".join(f"- {f}" for f in facts))
    summary = _summary(turn)
    if summary:
        parts.append(f"Resumen de la parte anterior de esta conversación: {summary}")
    return "".join(p + "\n\n" for p in parts)


def _summary(turn: _Turn) -> Optional[str]:
    with tenant_tx(turn.tenant) as cur:
        cur.execute("select summary from conversations where tenant_id = %s and id = %s",
                    (turn.tenant, turn.conv))
        row = cur.fetchone()
    return row["summary"] if row else None


def _tools_for(turn: _Turn) -> list[dict[str, Any]]:
    """Las herramientas que el negocio apagó ni se le ofrecen al modelo."""
    from ..domain import agent_profile
    return [t for t in _TOOLS if agent_profile.tool_enabled(turn.profile, t["name"])]


def _profile_text(profile: dict[str, Any]) -> str:
    lines = []
    for label, key in (("Envíos", "shipping"), ("Horarios", "hours"), ("Medios de pago", "payment_methods")):
        if profile.get(key):
            lines.append(f"{label}: {profile[key]}")
    for item in profile.get("faq") or []:
        lines.append(f"P: {item['q']} R: {item['a']}")
    for rule in profile.get("rules") or []:
        lines.append(f"Regla del negocio: {rule}")
    return "\n".join(lines) or "(sin datos cargados)"


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
        lines.append("Última lista mostrada al cliente (con su ficha):")
        for i, o in enumerate(shown, 1):
            ficha = ", ".join(f"{k}: {v}" for k, v in (o.get("specs") or {}).items())
            desc = (o.get("description") or "")[:160]
            lines.append(turn._line(i, o) + "".join(f" | {x}" for x in (ficha, desc) if x))
    query = turn.state.get("last_query")
    if query:
        prefs = query["keywords"] + [f"color {query['color']}" if query["color"] else "",
                                     f"ambiente {query['ambiente']}" if query["ambiente"] else "",
                                     f"hasta {_money(query['budget'])}" if query.get("budget") else ""]
        lines.append("Búsqueda vigente: " + ", ".join(p for p in prefs if p))
    cart = orders.get_cart(turn.tenant, turn.conv)
    lines.append("Carrito: " + (turn.cart_text(cart).replace("\n", " | ") if cart else "vacío"))
    from ..domain import agent_profile
    # Si el negocio apagó "estado del pedido", el modelo tampoco ve estados para repetirlos.
    recent = (orders.conversation_orders(turn.tenant, turn.conv, limit=3)
              if agent_profile.tool_enabled(turn.profile, "estado_pedido") else [])
    for o in recent:
        note = ("lo revisa una persona: no pidas pagar ni ofrezcas link" if o["attention_reason"]
                else "ya pagado: no pidas pagar" if o["status"] in _PAID else "")
        lines.append(f"Pedido #{o['number']}: {o['status_label']}" + (f" ({note})" if note else ""))
    if len(recent) > 1:
        lines.append("Hay varios pedidos: si el cliente no aclara cuál, preguntá o resumí cada uno.")
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
    if name == "comparar_productos":
        picks = [n for n in (_int(x) for x in args.get("opciones") or []) if n is not None]
        budget = _budget(turn.text)
        if not turn._shown():
            return "No hay una lista de opciones para comparar: buscá primero."
        # Ninguna opción entra en el presupuesto: la búsqueda real con ese tope.
        return turn.compare("", picks, budget) or turn.search(turn.text, budget)
    from ..domain import agent_profile
    if not agent_profile.tool_enabled(turn.profile, name):
        return "Herramienta no habilitada por el negocio: decí que lo confirma una persona del equipo."
    if name == "consultar_envio":
        return turn.shipping(str(args.get("zona") or ""))
    if name == "buscar_info_negocio":
        return turn.knowledge(consulta) or "No hay información cargada sobre eso: lo confirma una persona."
    if name == "historial_cliente":
        return turn.customer_history()
    if name == "preparar_compra":
        return turn.prepare_checkout("")
    if name == "estado_pedido":
        return turn.status(paid_claim=bool(args.get("cliente_dice_que_pago")))
    return "Herramienta no permitida."


# El resumen que pide el "sí" para cobrar llega TAL CUAL: el cliente tiene que ver exactamente
# qué lleva y el total antes de confirmar. La comparación también: sus rasgos salen de la ficha
# y una redacción libre podría agregar otros. Un cambio de carrito puede redactarlo el modelo si
# muestra el total real; si la herramienta no pudo cambiarlo, va su explicación tal cual.
_VERBATIM = {"preparar_compra", "comparar_productos"}
_CART_TOOLS = {"agregar_al_carrito", "quitar_del_carrito"}
_PAID = {"PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"}


def _cart_key(turn: _Turn) -> tuple:
    cart = orders.get_cart(turn.tenant, turn.conv)
    return tuple(sorted((it["item_id"], it["qty"]) for it in cart["items"])) if cart else ()

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


# Afirmación sobre un pedido -> condición que la hace cierta según la base.
_CLAIMS = [
    (re.compile(r"\b(pagar|paga|pagues|abonar|abona|abones|link (de|para) pago|esperando (el|tu) pago|"
                r"espera el pago|pendiente de pago|falta (el )?pago)\b"),
     "pide pagar", lambda o: o["status"] == "PENDING_PAYMENT" and not o["attention_reason"]),
    (re.compile(r"\b(pagad[oa]s?|acreditad[oa]s?|recibimos (el|tu) pago|pago (fue |esta )?(aprobado|confirmado))\b"),
     "lo da por pagado", lambda o: o["status"] in _PAID or o["attention_reason"] == "paid_without_stock"),
    (re.compile(r"\b(despachad[oa]s?|en camino|ya salio|entregad[oa]s?|ya (te )?llego)\b"),
     "lo da por despachado", lambda o: o["status"] in {"DISPATCHED", "IN_TRANSIT", "DELIVERED"}),
]
# Canales, descuentos y plazos: el agente no los ejecuta; sólo puede repetir lo que informa el negocio.
_UNBACKED = re.compile(r"\b(e-?mail|mail|correo|whatsapp|sms|llamad[oa]|llamarte|te llamo|descuentos?|"
                       r"rebajas?|bonificacion|gratis|sin cargo|te aviso|te avise|te avisamos|avisarte|"
                       r"manana|hoy mismo|\d+\s?(?:hs|horas|dias|semanas)\b|\d+\s?%)")
# El modelo deriva a una persona: el pedido tiene que quedar marcado para que alguien lo vea.
_RE_HANDOFF = re.compile(r"\b(una persona|el equipo te (confirma|avisa|contacta|responde)|"
                         r"(lo|te lo|te) (confirma|consulta|responde) (el equipo|alguien))\b")
# Acción que se atribuye el agente («te lo envié por WhatsApp», «te apliqué el 10%»): no tiene
# herramienta de envío ni de descuento, así que no vale aunque el perfil informe el canal o la regla.
_RE_AGENT_DOES = re.compile(
    r"\b(te (lo |la |los |las )?(envio|envie|mando|mande|paso|pase|escribo|escribi|aplico|aplique|hago|hice|dejo|deje)|"
    r"(voy a|vamos a|puedo) (enviar|mandar|pasar|escribir|aplicar|hacer)(te|telo|tela)?|"
    r"(enviar|mandar|escribir|aplicar|hacer)(te|telo|tela)|aplicad[oa])\b")
_RE_VIA = re.compile(r"\b(por|al|a tu|via) (e-?mail|mail|correo|whatsapp|sms)\b")
_RE_DISCOUNT = re.compile(r"\b(descuentos?|rebajas?|bonificacion)\b|\d+\s?%")
_SPLIT = re.compile(r"(?<!\d)[.,](?!\d)|[;:\n!?¡¿]|\s(?:y|o|pero)\s")
_RE_AVAIL = re.compile(r"\b(\d+)\s+disponibles?\b|\b(?:hay|quedan)\s+(\d+)\b")


_NEG = {"no", "ni", "nunca", "sin"}
_COND = {"si", "cuando", "apenas", "vez", "cuanto", "hasta", "despues"}   # «una vez pagado…»


def _negated(clause: str, start: int, words: set[str] = _NEG) -> bool:
    return bool(words & set(clause[:start].split()[-4:]))


def _marks(refs: dict[str, Any]) -> dict[str, set[str]]:
    """Palabras que distinguen a cada producto de los demás ("mate", "pico", "llaves")."""
    return {n: _stems(n) - set().union(*(_stems(m) for m in refs if m != n)) for n in refs}


def _mentions(clause: str, marks: dict[str, set[str]]) -> list[tuple[int, str]]:
    return sorted((m.start(), n) for n, ws in marks.items() for w in ws
                  for m in re.finditer(rf"\b{re.escape(w)}", clause))


def _catalog(turn: _Turn) -> dict[str, tuple[set[int], set[int]]]:
    """Producto visible -> (importes, disponibles) que le corresponden."""
    refs: dict[str, tuple[set[int], set[int]]] = {}
    for o in turn._shown() + turn.products:
        if o["pricing_mode"] == "fixed" and o["price"] is not None:
            amounts, units = refs.setdefault(o["name"], (set(), set()))
            amounts.add(round(o["price"]))
            units.add(o["available"])
    cart = orders.get_cart(turn.tenant, turn.conv)
    for order in ([cart] if cart else []) + orders.conversation_orders(turn.tenant, turn.conv):
        for it in order["items"]:
            refs.setdefault(it["name"], (set(), set()))[0].update(
                {round(it["unit_price"]), round(it["line_total"])})
    return refs


def _problem(reply: str, turn: _Turn, evidence: str, allowed: str) -> Optional[str]:
    """Motivo por el que la respuesta no puede llegar al cliente, o None si pasa los controles."""
    if not _verified(reply, evidence):
        return "usa precios, cantidades, pedidos o links que no salieron de las herramientas"
    found = orders.conversation_orders(turn.tenant, turn.conv)
    by_number = {str(o["number"]): o for o in found}
    cart = orders.get_cart(turn.tenant, turn.conv)
    refs = _catalog(turn)
    marks = _marks(refs)
    for clause in _SPLIT.split(normalize(reply)):
        named = [by_number[n] for n in _RE_ORDER.findall(clause) if n in by_number]
        for rx, what, holds in _CLAIMS:
            for m in rx.finditer(clause):
                # Una condición futura («una vez pagado») no afirma el estado; pedir pagar sí.
                if _negated(clause, m.start(), _NEG if what == "pide pagar" else _NEG | _COND):
                    continue
                if what != "lo da por pagado" and not named and (not found or (cart and cart["items"])):
                    continue        # sin pedido nombrado puede hablar del carrito o de la política
                # Sin número tiene que valer para todos: con un pedido pagado y otro pendiente,
                # «tu pedido está pagado» es ambiguo aunque uno lo esté.
                ok = bool(named or found) and all(holds(o) for o in named or found)
                if not ok:
                    return f"{what} y eso contradice el estado real del pedido"
        for m in _UNBACKED.finditer(clause):
            if m.group(0) not in allowed and not _negated(clause, m.start()):
                return f"ofrece «{m.group(0)}», que ni las herramientas ni el negocio informan"
        act = _RE_AGENT_DOES.search(clause)
        if act and not _negated(clause, act.start()) and (_RE_VIA.search(clause) or _RE_DISCOUNT.search(clause)):
            return f"se atribuye «{act.group(0)}», una acción que el sistema no realizó"
        mentions = _mentions(clause, marks)
        if not mentions:
            continue
        # Un importe junto a un producto vale sólo con sus valores (precio o línea del carrito/pedido);
        # un total de carrito sin producto nombrado no entra en este vínculo.
        for rx, idx in ((_RE_MONEY, 0), (_RE_AVAIL, 1)):
            for m in rx.finditer(clause):
                value = next(iter(_amounts(m.group(0))), None) if idx == 0 else int(m.group(1) or m.group(2))
                before = [n for p, n in mentions if p < m.start()]
                name = before[-1] if before else mentions[0][1]
                if refs[name][idx] and value not in refs[name][idx]:
                    return f"atribuye «{m.group(0)}» a {name} y no le corresponde"
    return None


def _fallback(turn: _Turn, message: str, outputs: list[str], cart_changed: bool) -> Optional[str]:
    """Respaldo según el turno: un agradecimiento lo cierra el planner por reglas (no una búsqueda);
    si no, el texto real de las herramientas de este turno, o las reglas si no se ejecutó nada."""
    if not outputs or (_social(normalize(message)) and not cart_changed):
        turn.products = []
        return None
    return "\n\n".join(outputs[-2:])


def run(turn: _Turn, message: str, conversation_id: str, planner: Planner) -> Optional[str]:
    """Bucle de herramientas. Devuelve la respuesta, o None si el modelo no está disponible y
    todavía no ejecutó nada (entonces responde el planner por reglas)."""
    history = opportunities.get_recent_messages(turn.tenant, conversation_id, limit=HISTORY)
    profile = turn.profile
    perfil = _profile_text(profile)
    messages: list[dict[str, Any]] = [{"role": "system", "content": _SYSTEM.format(
        vendedor=profile.get("seller_name") or "el asistente", negocio=_business_name(turn.tenant),
        tono=_TONES.get(profile.get("tone") or "cercano", _TONES["cercano"]),
        perfil=perfil, memoria=_memory_text(turn), contexto=_context(turn))}] + history
    if not history or history[-1].get("content") != message:
        messages.append({"role": "user", "content": message})
    outputs: list[str] = []
    verbatim: list[str] = []
    cart_changed = False
    reply = ""
    try:
        for _ in range(MAX_STEPS):
            resp = planner(messages, _tools_for(turn))
            calls = [c for c in resp.get("tool_calls") or [] if c.get("name")]
            if not calls:
                reply = (resp.get("content") or "").strip()
                break
            messages.append({"role": "assistant", "content": resp.get("content") or "",
                             "tool_calls": [{"function": {"name": c["name"], "arguments": c.get("arguments") or {}}}
                                            for c in calls]})
            for c in calls:
                before = _cart_key(turn) if c["name"] in _CART_TOOLS else None
                out = _execute(turn, c["name"], c.get("arguments") or {})
                outputs.append(out)
                if before is not None and _cart_key(turn) != before:
                    cart_changed = True
                elif before is not None or c["name"] in _VERBATIM:
                    verbatim.append(out)
                messages.append({"role": "tool", "tool_name": c["name"], "content": json.dumps({"texto": out}, ensure_ascii=False)})
            if verbatim:
                break       # va tal cual: no se pide una redacción que se descartaría
    except Exception:  # noqa: BLE001 - modelo caído o respuesta inválida
        log.exception("planner LLM de ventas falló")
        if not outputs:
            return _fallback(turn, message, outputs, cart_changed)
    if verbatim:
        return "\n\n".join(verbatim[-2:])
    cart = orders.get_cart(turn.tenant, turn.conv)
    evidence = "\n".join(outputs + [_context(turn), turn.cart_text(cart), perfil])
    if cart:
        evidence += "\n" + " ".join(_money(it["unit_price"]) for it in cart["items"])
    allowed = normalize("\n".join([perfil] + outputs))
    total = _money(cart["total"]) if cart_changed and cart and cart["items"] else None

    def problem(text: str) -> Optional[str]:
        if total and total not in text:
            return f"cambió el carrito y no muestra el total real ({total})"
        return _problem(text, turn, evidence, allowed)

    reply = reply.replace("**", "").replace("__", "")
    asks_choice = bool(_RE_COMPARE.search(normalize(message)))      # con o sin presupuesto

    def free_choice(text: str) -> bool:
        # Comparó o recomendó en texto libre nombrando productos: rasgos, usos y ventajas no se pueden
        # verificar. Responde la comparación de las reglas (mismos productos, sólo datos de ficha).
        if asks_choice and text and _mentions(normalize(text), _marks(_catalog(turn))):
            turn.tool("control", "comparación/recomendación libre: responde la ficha")
            turn.products = []
            return True
        return False

    if free_choice(reply):
        return None
    why = problem(reply) if reply else "sin respuesta"
    if why and reply:
        # Una sola reescritura, SIN herramientas: lo ejecutado no se repite aunque el modelo lo pida.
        log.warning("respuesta del LLM descartada: %s", why)
        turn.tool("control", f"respuesta del modelo descartada: {why}")
        note = (f"Control del servidor: tu respuesta no se envió porque {why}. Reescribila breve, sólo "
                "con datos del contexto y de las herramientas ya usadas. No llames herramientas.")
        try:
            again = planner(messages + [{"role": "assistant", "content": reply},
                                        {"role": "system", "content": note}], [])
            reply = (again.get("content") or "").strip().replace("**", "").replace("__", "")
            if free_choice(reply):
                return None
            why = problem(reply) if reply else "sin respuesta"
        except Exception:  # noqa: BLE001 - modelo caído al reescribir
            log.exception("reescritura del LLM de ventas falló")
        if why:
            turn.tool("control", f"reescritura descartada: {why}")
    if why:
        return _fallback(turn, message, outputs, cart_changed)
    if _RE_HANDOFF.search(normalize(reply)):
        turn.requires_human = True
    if turn.payment and turn.payment["checkout_url"] not in reply:
        reply += f"\n{turn.payment['checkout_url']}"
    return reply
