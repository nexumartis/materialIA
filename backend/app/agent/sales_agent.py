"""Agente de ventas end-to-end por chat (diseño: docs/superpowers/specs/2026-10-26-agente-ventas-design.md).

Cada mensaje: entender la intención → llamar herramientas tenant-safe → responder SÓLO con datos
que devolvieron las herramientas (precio, disponible, estado del pedido, link). Nada de precios ni
stock "recordados": la memoria de la conversación (`agent_state`) guarda IDs y la confirmación
pendiente.

El planner de esta entrega es determinista (modo `mock`): entiende intención, cantidades, color,
presupuesto y referencias ("la primera", "esa negra") en español rioplatense. Un planner con LLM
puede reemplazarlo usando las mismas herramientas (`SALES_TOOLS`).

Confirmación: generar el pedido y el link de pago (irreversible) exige un "sí" explícito del
cliente sobre un resumen con total. Los productos a pedido (`custom_quote`) se derivan a una
persona del negocio.
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from ..db import tenant_tx
from ..domain import agent_profile, inventory, opportunities, orders
from ..domain.inventory import normalize
from ..payments import service as payments
from ..payments.providers import PaymentProviderError
from ..schemas import OpportunityInput
from .tools import ToolContext

# --- Herramientas (contratos; el tenant sale del ToolContext) ----------------------
SALES_TOOLS = {
    "buscar_productos": "Busca productos activos con precio vigente y disponible (texto, color, presupuesto).",
    "consultar_stock": "Disponible real de un producto (on_hand - reservado).",
    "ver_carrito": "Carrito abierto de la conversación con totales.",
    "agregar_al_carrito": "Agrega un producto (valida precio y stock; no aparta).",
    "quitar_del_carrito": "Quita un producto del carrito.",
    "comprar": "Revalida, aparta stock, crea el pedido y el link de pago. Requiere 'sí' del cliente.",
    "estado_pedido": "Estado verificado de los pedidos de la conversación.",
}


@dataclass
class SalesReply:
    reply: str
    conversation_id: str
    mode: str = "mock"
    requires_human: bool = False
    cart: Optional[dict[str, Any]] = None
    orders: list[dict[str, Any]] = field(default_factory=list)
    payment: Optional[dict[str, Any]] = None
    products: list[dict[str, Any]] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    ui: dict[str, Any] = field(default_factory=dict)


# --- Contenido interactivo ---------------------------------------------------------
# Independiente del canal: el chat web lo dibuja como tarjetas y botones; en WhatsApp se traduce
# a imagen con texto + botones de respuesta (hasta 3, 20 caracteres) o lista (hasta 10 filas).
# Cada botón ENVÍA un mensaje de texto que el agente ya entiende, así el flujo es el mismo
# si el canal no soporta botones y el cliente lo escribe a mano.
def _card(n: int, o: dict[str, Any]) -> dict[str, Any]:
    sellable = o["pricing_mode"] == "fixed" and o["price"] is not None
    if not sellable:
        action = {"label": "Consultar", "message": f"quiero la {n}"}
    elif o["available"] > 0:
        action = {"label": "Agregar", "message": f"agregame la {n}"}
    else:
        action = None
    return {"n": n, "name": o["name"], "brand": o.get("brand"), "image_url": o.get("image_url"),
            "price": o["price"] if sellable else None, "available": o["available"],
            "pricing_mode": o["pricing_mode"], "description": o.get("description") or "",
            "specs": o.get("specs") or {}, "action": action}


def _ui(turn: "_Turn") -> dict[str, Any]:
    ui: dict[str, Any] = {}
    if turn.products:
        ui["products"] = [_card(i, o) for i, o in enumerate(turn.products, 1)]
    if turn.payment:
        ui["payment"] = {"url": turn.payment["checkout_url"], "provider": turn.payment["provider"]}
    cart = orders.get_cart(turn.tenant, turn.conv)
    if turn.state.get("pending"):
        quick = [{"label": "Sí, confirmo", "message": "sí"}, {"label": "No", "message": "no"}]
    elif turn.payment:
        quick = [{"label": "¿Cómo va mi pedido?", "message": "¿cómo va mi pedido?"}]
    elif cart and cart["items"]:
        quick = [{"label": "Comprar", "message": "comprar"},
                 {"label": "Ver carrito", "message": "ver carrito"}]
    else:
        quick = []
    if quick:
        ui["quick_replies"] = quick
    return ui


# --- Lenguaje --------------------------------------------------------------------
_COLORS = {"negro": "negro", "negra": "negro", "negros": "negro", "negras": "negro",
           "cromo": "cromo", "cromada": "cromo", "cromado": "cromo", "cromadas": "cromo",
           "cromados": "cromo", "plateada": "cromo", "plateado": "cromo",
           "blanco": "blanco", "blanca": "blanco", "blancos": "blanco", "blancas": "blanco"}
_AMBIENTES = {"cocina": "cocina", "bano": "baño", "banio": "baño", "lavatorio": "baño"}
_SYNONYMS = {"grifo": "canilla", "grifos": "canilla", "griferia": "canilla", "griferias": "canilla",
             "monocomandos": "monocomando", "duchador": "ducha", "flexibles": "flexible",
             "sifones": "sifon", "inodoros": "inodoro", "lavatorio": "lavatorio"}
_STOP = set("""
hola buenas buen dia dias tardes noches che tenes tienen tendras hay venden vendes busco buscando
necesito quiero queria querria quisiera me mostras mostrame pasame pasas de la el los las un una
unos unas que para por con sin y o en a al del lo le les mi mis tu su sus algo alguna alguno algun
cual cuales cuanto cuanta cuantos sale salen cuesta cuestan precio precios valor esta este esa ese
estas estos esas esos si no gracias porfa favor recomendas recomendarias recomendame ofreces
menos mas hasta mil lucas pesos maximo barato barata baratas economica economico mejor otra otro
otras otros opciones opcion alternativa alternativas modelo modelos producto productos stock
disponible tiene tenga hay ahi
""".split())
_WORD_NUMBERS = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
                 "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "par": 2}
_ORDINALS = {"primera": 1, "primero": 1, "1ra": 1, "1ro": 1, "segunda": 2, "segundo": 2,
             "2da": 2, "2do": 2, "tercera": 3, "tercero": 3, "3ra": 3, "3ro": 3, "cuarta": 4,
             "cuarto": 4, "quinta": 5, "quinto": 5}

_RE_CONFIRM = re.compile(r"^\s*(si|sii+|dale|ok|okey|confirmo|confirmado|de una|listo|va|perfecto|"
                         r"si,? confirmo|si,? dale|dale,? si|si por favor|si porfa)\b[\s!.]*")
# Sólo una negativa a secas cancela el resumen; "no, sacame la negra" lo interpreta el agente.
_RE_DENY = re.compile(r"^\s*(no|nop|mejor no|cancela|cancelar|todavia no|espera|no gracias|"
                      r"no,? (por ahora|todavia)|dejalo|deja)[\s!.,]*$")
# "No, nada más" después de "¿sumás algo más o lo comprás?": cerrar la compra.
_RE_DONE = re.compile(r"^\s*(no|nop|nada|nada mas|no gracias|no,? gracias|eso es todo|eso nomas|es todo|"
                      r"ya esta|no,? (quiero|necesito|voy a) (sumar|agregar|llevar) nada( mas)?|"
                      r"no quiero nada mas|no,? nada mas|nada mas,? gracias)\b[\s!.,]*(gracias)?[\s!.]*$")
# Preguntas sobre el negocio (envíos, retiro, horarios, pagos, factura): responde el perfil.
_RE_INFO = re.compile(r"\b(envio|envios|envian|mandan|entrega|entregan|retiro|retirar|horario|horarios|"
                      r"abren|atienden|abierto|factura|facturan|cuotas|tarjeta|medios? de pago|formas? de pago|"
                      r"se puede pagar|puedo pagar|direccion|donde (estan|queda)|local)\b")
_RE_PAID_CLAIM = re.compile(r"\bya (te )?(pague|abone|transferi|deposite)\b")
_RE_STATUS = re.compile(r"\b(estado|salio|llego|llega|donde (esta|anda|viene)|seguimiento|tracking|"
                        r"cuando (llega|sale)|despach|como (va|viene|anda|sigue)|novedad)")
_RE_ORDER_WORD = re.compile(r"\b(pedido|orden|compra|envio|paquete)\b")
_RE_BUY = re.compile(r"\b(la compro|lo compro|las compro|los compro|comprar|compro|quiero pagar|pagar|"
                     r"link de pago|cerrar (la )?compra|finalizar|confirmar (el )?pedido|hacer el pedido)\b")
_RE_REMOVE = re.compile(r"\b(saca|sacame|sacala|sacalo|quita|quitame|quitala|borra|borrame|elimina)\b")
_RE_CART = re.compile(r"\b(carrito|que (tengo|llevo)|cuanto (es|seria|va) (el total|todo)|total)\b")
_RE_ADD = re.compile(r"\b(agrega|agregame|agregala|agregalo|agregalas|agregalos|agregar|suma|sumame|"
                     r"sumala|anota|anotame|dame|mandame|me llevo|llevo|quiero|ponele|poneme|dale)\b")
_RE_BUDGET = re.compile(r"(menos de|hasta|maximo|no mas de|por debajo de|debajo de|tope de?)\s*\$?\s*"
                        r"([\d][\d.,]*)\s*(mil|k|lucas)?")
_RE_STOCK_Q = re.compile(r"\b(stock|disponib|quedan|queda|cuantas hay|cuantos hay|hay de)\b")


def _money(amount: Optional[float]) -> str:
    if amount is None:
        return "sin precio"
    return "$" + f"{amount:,.0f}".replace(",", ".")


_RE_CHOICE = re.compile(r"(?:(?:quiero |dame |agregame |prefiero )?(?:la|el|opcion|numero|nro)\s*)?"
                        r"(\d|uno|una|dos|tres|cuatro|cinco|seis|primera|primero|segunda|segundo|"
                        r"tercera|tercero|cuarta|cuarto|quinta|quinto)")
_CHOICE_WORDS = {**_ORDINALS, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6}


def _choice(text: str) -> Optional[int]:
    """Elección de una opción listada cuando el mensaje es SÓLO eso: "2", "la 2", "la segunda"."""
    m = _RE_CHOICE.fullmatch(text.strip(" .!?¿¡,"))
    if not m:
        return None
    raw = m.group(1)
    return int(raw) if raw.isdigit() else _CHOICE_WORDS.get(raw)


def _budget(text: str) -> Optional[float]:
    m = _RE_BUDGET.search(text)
    if not m:
        return None
    raw = m.group(2).replace(".", "").replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        return None
    if m.group(3) or value < 1000:
        value *= 1000
    return value


def _qty(text: str) -> int:
    m = re.search(r"\b(\d{1,3})\b(?!\s*(mil|k|lucas))", text)
    if m:
        return max(1, int(m.group(1)))
    for word, n in _WORD_NUMBERS.items():
        if re.search(rf"\b{word}\b", text) and word not in ("un", "una", "uno"):
            return n
    return 1


def _filters(text: str) -> dict[str, Any]:
    tokens = re.findall(r"[a-z0-9]+", text)
    color = next((_COLORS[t] for t in tokens if t in _COLORS), None)
    ambiente = next((_AMBIENTES[t] for t in tokens if t in _AMBIENTES), None)
    keywords = []
    for t in tokens:
        if t in _COLORS or t in _AMBIENTES or t in _STOP or t.isdigit() or len(t) < 3:
            continue
        t = _SYNONYMS.get(t, t)
        # plural simple: canillas -> canilla, llaves -> llave
        if len(t) > 4 and t.endswith("es") and not t.endswith("ees"):
            t = t[:-2] if t[-3] not in "aeiou" else t[:-1]
        elif len(t) > 3 and t.endswith("s"):
            t = t[:-1]
        if t not in keywords:
            keywords.append(t)
    return {"keywords": keywords, "color": color, "ambiente": ambiente}


# --- Estado de la conversación ------------------------------------------------------
def _load_state(tenant_id: str, conversation_id: str) -> dict[str, Any]:
    with tenant_tx(tenant_id) as cur:
        cur.execute("select agent_state from conversations where tenant_id = %s and id = %s",
                    (tenant_id, conversation_id))
        row = cur.fetchone()
    return dict(row["agent_state"] or {}) if row else {}


def _save_state(tenant_id: str, conversation_id: str, state: dict[str, Any]) -> None:
    with tenant_tx(tenant_id) as cur:
        cur.execute("update conversations set agent_state = %s::jsonb where tenant_id = %s and id = %s",
                    (json.dumps(state), tenant_id, conversation_id))


# --- Agente ----------------------------------------------------------------------
class _Turn:
    def __init__(self, ctx: ToolContext, state: dict[str, Any]):
        self.ctx = ctx
        self.state = state
        self.trace: list[dict[str, Any]] = []
        self.products: list[dict[str, Any]] = []
        self.payment: Optional[dict[str, Any]] = None
        self.requires_human = False

    @property
    def tenant(self) -> str:
        return self.ctx.tenant_id

    @property
    def conv(self) -> str:
        return self.ctx.conversation_id or ""

    def filters(self, text: str) -> dict[str, Any]:
        """Filtros del mensaje con las palabras mal tipeadas corregidas contra el catálogo de la
        empresa ("canulla" -> "canilla"). Sólo corrige hacia palabras que existen en el catálogo."""
        f = _filters(text)
        if f["keywords"]:
            vocab = inventory.vocabulary(self.tenant)
            fixed = []
            for k in f["keywords"]:
                if len(k) >= 4 and not any(k in w for w in vocab):
                    close = difflib.get_close_matches(k, vocab, n=1, cutoff=0.75)
                    k = close[0] if close else k
                fixed.append(k)
            f["keywords"] = fixed
        return f

    @property
    def profile(self) -> dict[str, Any]:
        if not hasattr(self, "_profile"):
            self._profile = agent_profile.for_agent(self.tenant) or {}
        return self._profile

    def info(self, text: str) -> str:
        """Responde con lo que el negocio cargó en su perfil; si no lo tiene, no lo inventa."""
        p = self.profile
        words = {w for w in re.findall(r"[a-z]{4,}", text) if w not in _STOP}
        best, score = None, 0
        for item in p.get("faq") or []:
            q = set(re.findall(r"[a-z]{4,}", normalize(item["q"])))
            overlap = len({w[:5] for w in words} & {w[:5] for w in q})
            if overlap > score:
                best, score = item, overlap
        self.tool("perfil_negocio", "faq" if best else "campos")
        if best:
            return best["a"]
        topics = [("envi", "shipping"), ("entreg", "shipping"), ("mand", "shipping"), ("retir", "hours"),
                  ("horar", "hours"), ("abr", "hours"), ("atiend", "hours"), ("pag", "payment_methods"),
                  ("tarjet", "payment_methods"), ("cuota", "payment_methods")]
        for prefix, field in topics:
            if any(w.startswith(prefix) for w in words) and p.get(field):
                return p[field]
        self.requires_human = True
        return ("Eso no lo tengo cargado. Le paso tu consulta a una persona del equipo para que te "
                "responda. ¿Te ayudo con algún producto mientras tanto?")

    def tool(self, name: str, summary: str) -> None:
        self.trace.append({"name": name, "summary": summary})

    # -- referencias a productos ya mostrados --
    def _shown(self) -> list[dict[str, Any]]:
        ids = self.state.get("last_results") or []
        if not ids:
            return []
        found = {o["id"]: o for o in inventory.offers(self.tenant, ids=ids, limit=len(ids))}
        return [found[i] for i in ids if i in found]

    def resolve(self, text: str) -> Optional[dict[str, Any]]:
        shown = self._shown()
        tokens = re.findall(r"[a-z0-9]+", text)
        for t in tokens:
            if t in _ORDINALS and 0 < _ORDINALS[t] <= len(shown):
                return shown[_ORDINALS[t] - 1]
        if "ultima" in tokens or "ultimo" in tokens:
            if shown:
                return shown[-1]
        m = re.search(r"\b(?:la|el|numero|nro|opcion)\s*(\d)\b", text)
        if m and 0 < int(m.group(1)) <= len(shown):
            return shown[int(m.group(1)) - 1]
        f = self.filters(text)
        if shown and (f["color"] or f["keywords"]):
            matches = [o for o in shown
                       if (not f["color"] or o["specs"].get("color") == f["color"])
                       and all(k in normalize(f"{o['name']} {o['brand']} {json.dumps(o['specs'])}")
                               for k in f["keywords"] if k not in ("canilla",))]
            if len(matches) == 1:
                return matches[0]
        if f["keywords"]:
            found = inventory.offers(self.tenant, keywords=f["keywords"], color=f["color"],
                                     ambiente=f["ambiente"], limit=5)
            if len(found) == 1:
                return found[0]
        if len(shown) == 1:
            return shown[0]
        sel = self.state.get("selected")
        if sel and any(t in tokens for t in ("esa", "ese", "la", "lo", "agregala", "agregalo")):
            found = inventory.offers(self.tenant, ids=[sel], limit=1)
            return found[0] if found else None
        return None

    def pick(self, opcion: Optional[int] = None, consulta: str = "") -> Optional[dict[str, Any]]:
        """Producto por número de la última lista o por descripción (para el planner con LLM)."""
        if opcion is not None:
            shown = self._shown()
            return shown[opcion - 1] if 0 < opcion <= len(shown) else None
        return self.resolve(normalize(consulta)) if consulta else None

    # -- presentación --
    def _line(self, i: int, o: dict[str, Any]) -> str:
        if o["pricing_mode"] != "fixed":
            tail = "a pedido (precio y plazo los confirma una persona)"
        elif o["price"] is None:
            tail = "sin precio vigente"
        else:
            stock = (f"{o['available']} disponibles" if o["available"] > 1
                     else "última unidad" if o["available"] == 1 else "SIN STOCK")
            tail = f"{_money(o['price'])} · {stock}"
        brand = f" — {o['brand']}" if o.get("brand") else ""
        return f"{i}. {o['name']}{brand} · {tail}"

    def show(self, items: list[dict[str, Any]], intro: str) -> str:
        # Varias búsquedas en un mismo turno continúan la numeración ("la 3" no es ambigua).
        offset = len(self.products)
        ids = [o["id"] for o in items]
        self.state["last_results"] = (self.state.get("last_results") or [])[:offset] + ids if offset else ids
        self.products = self.products + items
        lines = [intro] + [self._line(i, o) for i, o in enumerate(items, offset + 1)]
        return "\n".join(lines)

    def cart_text(self, cart: Optional[dict[str, Any]]) -> str:
        if not cart or not cart["items"]:
            return "Tu carrito está vacío."
        lines = [f"• {it['qty']} × {it['name']} — {_money(it['line_total'])}" for it in cart["items"]]
        return "\n".join(lines + [f"Total: {_money(cart['total'])}"])

    # -- intenciones --
    def search(self, text: str, budget: Optional[float]) -> str:
        f = self.filters(text)
        query = {"keywords": f["keywords"], "color": f["color"], "ambiente": f["ambiente"]}
        if budget is not None and not (f["keywords"] or f["color"] or f["ambiente"]):
            # "¿cuál me recomendás por menos de 100 mil?" => sobre la última búsqueda
            query = dict(self.state.get("last_query") or query)
        if not (query["keywords"] or query["color"] or query["ambiente"]):
            if self.state.get("last_results"):
                return ("No te entendí. Si querés alguna de las opciones, decime el número "
                        "(por ejemplo \"la 2\"), o contame qué otra cosa buscás.")
            return (self.profile.get("greeting") or
                    "¡Hola! Soy el asistente de ventas. Contame qué buscás.")
        self.state["last_query"] = query
        found = inventory.offers(self.tenant, **query, max_price=budget, limit=6)
        self.tool("buscar_productos", f"{len(found)} resultado(s)")
        if not found:
            if budget is not None:
                cheaper = inventory.offers(self.tenant, **query, limit=6)
                if cheaper:
                    return self.show(cheaper, f"No tengo opciones de hasta {_money(budget)}. "
                                              "Lo más cercano que hay:")
            hint = (" Si querés alguna de las opciones de antes, decime el número (por ejemplo "
                    "\"la 2\")." if self.state.get("last_results") else "")
            return ("No encontré eso en el catálogo. ¿Me lo describís de otra forma (tipo, color, "
                    "ambiente o medida)?" + hint)
        if all(o["pricing_mode"] == "fixed" and o["available"] == 0 for o in found):
            return self.out_of_stock(found)
        if budget is not None:
            in_stock = [o for o in found if o["pricing_mode"] == "fixed" and o["available"] > 0]
            text_out = self.show(found, f"Hasta {_money(budget)} tengo:")
            if not in_stock:
                return text_out + "\nNinguna tiene stock ahora, así que no te las puedo prometer."
            best = in_stock[0]
            return (text_out + f"\nLa más conveniente con stock es la {best['name']} "
                    f"({best.get('brand') or 'sin marca'}) a {_money(best['price'])}. ¿Te la agrego?")
        return self.show(found, "Tengo estas opciones:") + "\n¿Querés que te agregue alguna?"

    def out_of_stock(self, items: list[dict[str, Any]]) -> str:
        """Escenario D: no promete disponibilidad; ofrece sustitutos REALES con stock."""
        o = items[0]
        alts = inventory.offers(self.tenant, category=o["category"],
                                ambiente=o["specs"].get("ambiente"), in_stock_only=True,
                                exclude=[i["id"] for i in items], limit=4)
        self.tool("consultar_stock", f"{o['sku']}: 0 disponibles; {len(alts)} alternativa(s)")
        head = (f"La {o['name']} está sin stock y no tengo fecha de reposición confirmada, "
                "así que no te la puedo prometer.")
        if not alts:
            self.state["last_results"] = [i["id"] for i in items]
            return head + " Si querés, le aviso al equipo para que te contacten cuando vuelva."
        return self.show(alts, head + " Te puedo ofrecer estas, que sí tienen stock:")

    def stock(self, text: str) -> str:
        o = self.resolve(text)
        if o is None:
            return self.search(text, None)
        return self.stock_offer(o)

    def stock_offer(self, o: dict[str, Any]) -> str:
        self.state["selected"] = o["id"]
        self.tool("consultar_stock", f"{o['sku']}: {o['available']} disponibles")
        if o["pricing_mode"] != "fixed":
            return f"La {o['name']} es a pedido: una persona del negocio te confirma plazo y precio."
        if o["available"] == 0:
            return self.out_of_stock([o])
        return f"Sí, de la {o['name']} hay {o['available']} disponibles, a {_money(o['price'])} c/u."

    def add(self, text: str, choice: Optional[int] = None) -> Optional[str]:
        if choice is not None:
            shown = self._shown()
            if not 0 < choice <= len(shown):
                return f"No tengo una opción {choice} en la lista. Elegí entre 1 y {len(shown)}."
            o, qty = shown[choice - 1], 1
        else:
            o = self.resolve(text)
            if o is None:
                return None
            qty = _qty(text)
        return self.add_offer(o, qty)

    def add_offer(self, o: dict[str, Any], qty: int) -> str:
        qty = max(1, int(qty))
        self.state["selected"] = o["id"]
        res = orders.add_item(self.tenant, self.conv, o["id"], qty)
        self.tool("agregar_al_carrito", f"{o['sku']} x{qty}: {res.status}")
        if res.status == "requires_human":
            self.requires_human = True
            self._lead_for_human(o)
            return (f"La {o['name']} es a pedido: no la puedo vender directo. Le paso tu consulta a "
                    "una persona del negocio para que te confirme precio y plazo.")
        if res.status == "no_price":
            self.requires_human = True
            return f"La {o['name']} no tiene precio vigente cargado; lo tiene que confirmar una persona."
        if res.status == "insufficient_stock":
            if res.available == 0:
                return self.out_of_stock([o])
            return (f"De la {o['name']} sólo hay {res.available} disponible(s). "
                    "¿Querés que te agregue esa cantidad?")
        if res.status == "not_found":
            return "Ese producto ya no está disponible en el catálogo."
        return (f"Listo, agregué {qty} × {o['name']} ({_money(res.offer['price'])} c/u).\n"
                + self.cart_text(res.cart)
                + "\nEntrega: por ahora coordinamos retiro o envío con el equipo después del pago. "
                  "¿Querés sumar algo más o lo comprás?")

    def remove(self, text: str) -> str:
        o = self.resolve(text)
        cart = orders.get_cart(self.tenant, self.conv)
        if o is None and cart and len(cart["items"]) == 1:
            o = {"id": cart["items"][0]["item_id"], "name": cart["items"][0]["name"]}
        if o is None:
            return "¿Cuál querés que saque?\n" + self.cart_text(cart)
        return self.remove_offer(o, cart)

    def remove_offer(self, o: dict[str, Any], cart: Optional[dict[str, Any]] = None) -> str:
        res = orders.remove_item(self.tenant, self.conv, o["id"])
        self.tool("quitar_del_carrito", res.status)
        if res.status != "ok":
            return f"La {o['name']} no estaba en tu carrito.\n" + self.cart_text(res.cart or cart)
        return f"Saqué la {o['name']}.\n" + self.cart_text(res.cart)

    def prepare_checkout(self, text: str) -> str:
        cart = orders.get_cart(self.tenant, self.conv)
        if not cart or not cart["items"]:
            # Con un pedido ya esperando pago, "la compro" pide ese link; no arma otro carrito.
            pending = [o for o in orders.conversation_orders(self.tenant, self.conv)
                       if o["status"] == "PENDING_PAYMENT" and not o["attention_reason"]]
            if pending:
                return self.pay_link(pending[0], f"Ya tenés el pedido #{pending[0]['number']} "
                                                 "esperando el pago.")
            o = self.resolve(text) if self.state.get("last_results") or self.state.get("selected") else None
            if o is not None:
                added = self.add(text)
                if self.requires_human or not orders.get_cart(self.tenant, self.conv):
                    return added or ""
                cart = orders.get_cart(self.tenant, self.conv)
        self.tool("ver_carrito", "vacío" if not cart or not cart["items"] else f"{len(cart['items'])} ítem(s)")
        if not cart or not cart["items"]:
            pending = [o for o in orders.conversation_orders(self.tenant, self.conv)
                       if o["status"] == "PENDING_PAYMENT"]
            if pending:
                return self.pay_link(pending[0], "Ya tenés un pedido esperando el pago.")
            return "Todavía no agregaste nada al carrito. ¿Qué producto querés llevar?"
        self.state["pending"] = {"action": "checkout", "total": cart["total"]}
        return ("Te confirmo el pedido:\n" + self.cart_text(cart)
                + "\nAl confirmar te aparto el stock y te paso el link de pago. ¿Confirmás? (sí / no)")

    def confirm_checkout(self) -> str:
        pending = self.state.pop("pending", None) or {}
        cart = orders.get_cart(self.tenant, self.conv)
        if cart and cart["items"] and abs(cart["total"] - float(pending.get("total") or 0)) > 0.005:
            # El carrito cambió después del resumen: el "sí" no vale para otro total.
            self.state["pending"] = {"action": "checkout", "total": cart["total"]}
            return ("El carrito cambió desde el resumen:\n" + self.cart_text(cart)
                    + "\n¿Confirmás este total? (sí / no)")
        res = orders.checkout(self.tenant, self.conv)
        self.tool("comprar", res.status)
        if res.status == "price_changed":
            changes = "\n".join(f"• {c['name']}: {_money(c['old'])} → {_money(c['new'])}"
                                for c in res.price_changes)
            self.state["pending"] = {"action": "checkout", "total": res.order["total"]}
            return ("Ojo: cambió el precio desde que lo agregaste.\n" + changes + "\n"
                    + self.cart_text(res.order) + "\n¿Confirmás con el precio nuevo? (sí / no)")
        if res.status == "out_of_stock":
            s = res.shortage
            return (f"Se agotó mientras lo confirmabas: de la {s['name']} quedan {s['available']} y "
                    f"pediste {s['requested']}. No aparté nada. ¿Querés ajustar la cantidad o ver "
                    "alternativas?")
        if res.status == "empty":
            return "Tu carrito está vacío. ¿Qué querés llevar?"
        if res.status == "requires_human":
            self.requires_human = True
            return (f"La {res.shortage['name']} necesita confirmación de una persona antes de "
                    "cobrarla. Ya les aviso.")
        order = res.order
        if res.status == "already_pending":
            return self.pay_link(order, f"El pedido #{order['number']} ya estaba confirmado; "
                                        f"el stock queda apartado hasta las {self._until(order)}.")
        self._lead_for_order(order)
        return self.pay_link(order, f"¡Listo! Pedido #{order['number']} por {_money(order['total'])}. "
                                    f"Te aparto el stock hasta las {self._until(order)}.")

    def pay_link(self, order: dict[str, Any], intro: str) -> str:
        try:
            pay = payments.start_payment(self.tenant, order["id"])
        except PaymentProviderError:
            self.tool("comprar", "proveedor de pago no disponible")
            return (intro + " No pude generar el link de pago ahora (el proveedor no respondió). "
                    "Escribime \"link de pago\" en un rato y lo reintento; el stock sigue apartado.")
        self.payment = pay
        mode = (" (pago SIMULADO de prueba: no se cobra nada)" if pay["provider"] == "simulated"
                else "")
        return f"{intro}\nPagá acá{mode}: {pay['checkout_url']}"

    @staticmethod
    def _until(order: dict[str, Any]) -> str:
        """Hora real de vencimiento de la reserva, en la zona del negocio demo (AR)."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        until = datetime.fromisoformat(order["reserved_until"])
        return until.astimezone(ZoneInfo("America/Argentina/Buenos_Aires")).strftime("%H:%M")

    def status(self, paid_claim: bool) -> str:
        found = orders.conversation_orders(self.tenant, self.conv)
        self.tool("estado_pedido", f"{len(found)} pedido(s)")
        if not found:
            cart = orders.get_cart(self.tenant, self.conv)
            if cart and cart["items"]:
                return "Todavía no confirmaste ningún pedido. Tenés en el carrito:\n" + self.cart_text(cart)
            return "No encuentro pedidos en esta conversación."
        o = found[0]
        if o["attention_reason"]:
            # Algo del cobro necesita a una persona: no se ofrece otro link ni se afirma un estado.
            self.requires_human = True
            if o["attention_reason"] == "paid_without_stock":
                return (f"Recibimos el pago del pedido #{o['number']}, pero el producto se agotó "
                        "mientras tanto. Una persona del equipo te va a contactar para devolverte el "
                        "dinero o ofrecerte una alternativa.")
            return (f"Hay algo para revisar en el pago del pedido #{o['number']}. Una persona del "
                    "equipo lo revisa y te contacta; no hace falta que pagues de nuevo.")
        if o["status"] == "PENDING_PAYMENT":
            if not paid_claim and o["payment"] and o["payment"]["status"] == "rejected":
                return self.pay_link(o, f"El último intento de pago del pedido #{o['number']} fue "
                                        "rechazado. Podés reintentar con el mismo link.")
            head = (f"Todavía no veo acreditado el pago del pedido #{o['number']}"
                    if paid_claim else f"Tu pedido #{o['number']} está esperando el pago")
            head += (". Apenas se acredite, te aviso por acá." if paid_claim else ".")
            return self.pay_link(o, head) if not paid_claim else head
        if o["status"] == "CANCELLED":
            why = (" porque venció la reserva sin pago" if o["cancel_reason"] == "reservation_expired"
                   else "")
            return f"El pedido #{o['number']} quedó cancelado{why}. ¿Querés que lo armemos de nuevo?"
        tracking = ("" if o["status"] in ("PAID", "PREPARING", "REFUNDED")
                    else " Todavía no tengo número de seguimiento cargado para este envío.")
        return f"Tu pedido #{o['number']} está {o['status_label']}.{tracking}"

    # -- CRM --
    def _lead_for_order(self, order: dict[str, Any]) -> None:
        opp = opportunities.upsert_opportunity(self.tenant, OpportunityInput(
            conversation_id=self.conv, stage="cotizada", origin="venta_chat",
            requirements={"pedido": order["number"],
                          "productos": [f"{i['qty']} × {i['name']}" for i in order["items"]]},
            requires_human_quote=False, estimated_amount=order["total"]))
        opportunities.log_activity(self.tenant, opp.id, "checkout",
                                   f"pedido #{order['number']} esperando pago")

    def _lead_for_human(self, o: dict[str, Any]) -> None:
        opportunities.upsert_opportunity(self.tenant, OpportunityInput(
            conversation_id=self.conv, stage="para_cotizar", origin="venta_chat",
            requirements={"producto": o["name"], "sku": o["sku"]}, requires_human_quote=True))


def _confirmation_reply(turn: _Turn, text: str) -> Optional[str]:
    """Respuesta a un resumen de compra pendiente. Determinista SIEMPRE (también con LLM): sólo un
    "sí" explícito del cliente genera el pedido y el link de pago."""
    pending = turn.state.get("pending")
    if pending and _RE_CONFIRM.match(text) and not _RE_ORDER_WORD.search(text):
        return turn.confirm_checkout()
    if pending and _RE_DENY.match(text):
        turn.state.pop("pending", None)
        return "Perfecto, no generé nada. ¿Querés cambiar algo del carrito?"
    turn.state.pop("pending", None)
    return None


def _rules_reply(turn: _Turn, text: str) -> str:
    """Planner determinista (modo mock): intención por reglas."""
    state, tenant_id, conv = turn.state, turn.tenant, turn.conv
    budget = _budget(text)
    cart_now = orders.get_cart(tenant_id, conv)
    if _RE_DONE.match(text) and cart_now and cart_now["items"]:
        reply = turn.prepare_checkout(text)
    elif _RE_INFO.search(text) and not _RE_ORDER_WORD.search(text):
        reply = turn.info(text)
    elif _RE_PAID_CLAIM.search(text):
        reply = turn.status(paid_claim=True)
    elif _RE_STATUS.search(text) and (_RE_ORDER_WORD.search(text) or "salio" in text or "llego" in text):
        reply = turn.status(paid_claim=False)
    elif _RE_BUY.search(text):
        reply = turn.prepare_checkout(text)
    elif _RE_REMOVE.search(text):
        reply = turn.remove(text)
    elif _RE_CART.search(text):
        cart = orders.get_cart(tenant_id, conv)
        turn.tool("ver_carrito", "vacío" if not cart else f"{len(cart['items'])} ítem(s)")
        reply = turn.cart_text(cart)
    elif _choice(text) and state.get("last_results"):
        reply = turn.add(text, choice=_choice(text))
    elif budget is None and _RE_STOCK_Q.search(text) and turn.state.get("last_results"):
        reply = turn.stock(text)
    else:
        reply = None
        if budget is None and _RE_ADD.search(text) and (state.get("last_results") or state.get("selected")):
            reply = turn.add(text)
        if reply is None:
            reply = turn.search(text, budget)
    return reply


def handle_sales_message(tenant_id: str, message: str, conversation_id: Optional[str] = None,
                         planner: Optional[Any] = None) -> SalesReply:
    """Un mensaje del cliente. Con LLM configurado (o un `planner` inyectado) el modelo elige las
    herramientas; si falla o su respuesta no pasa los controles, responde el planner por reglas."""
    from . import llm_sales

    conv = opportunities.ensure_conversation(tenant_id, conversation_id)
    opportunities.add_message(tenant_id, conv, "inbound", message)
    state = _load_state(tenant_id, conv)
    turn = _Turn(ToolContext(tenant_id=tenant_id, conversation_id=conv), state)
    text = normalize(message)
    mode = "mock"

    reply = _confirmation_reply(turn, text)
    if reply is None:
        planner = planner or llm_sales.default_planner()
        if planner is not None:
            reply = llm_sales.run(turn, message, conv, planner)
            mode = "live" if reply is not None else "mock"
        if reply is None:
            reply = _rules_reply(turn, text)

    _save_state(tenant_id, conv, state)
    ui = _ui(turn)
    opportunities.add_message(tenant_id, conv, "outbound", reply, ui or None)
    return SalesReply(
        reply=reply, conversation_id=conv, mode=mode, requires_human=turn.requires_human,
        cart=orders.get_cart(tenant_id, conv), orders=orders.conversation_orders(tenant_id, conv),
        payment=turn.payment, products=turn.products, trace=turn.trace, ui=ui,
    )
