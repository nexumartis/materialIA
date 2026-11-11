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
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Optional

from ..db import tenant_tx
from ..domain import agent_profile, ai_usage, booking, campaigns, reparto, shipping, customer_memory, delivery, georef, inventory, knowledge, limits, opportunities, orders, privacy, webhooks
from ..domain.inventory import normalize
from ..payments import service as payments
from ..payments.providers import PaymentAccountMissing, PaymentProviderError
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
            "specs": o.get("specs") or {}, "datasheet_url": o.get("datasheet_url"), "action": action}


def _ui(turn: "_Turn") -> dict[str, Any]:
    ui: dict[str, Any] = {}
    if turn.products:
        ui["products"] = [_card(i, o) for i, o in enumerate(turn.products, 1)]
        # Variantes del mismo modelo que no se mostraron: «También en: Cromo · Blanco».
        groups = sorted({o["variant_group"] for o in turn.products if o.get("variant_group")})
        if groups:
            with tenant_tx(turn.tenant) as cur:
                siblings = inventory.variant_siblings(cur, turn.tenant, groups)
            shown = {o["id"] for o in turn.products}
            for card, o in zip(ui["products"], turn.products):
                card["variant_label"] = o.get("variant_label")
                card["variants"] = [{"label": s["label"], "available": s["available"],
                                     "message": f"quiero la {s['name']}"}
                                    for s in siblings if s["group"] == o.get("variant_group") and s["id"] not in shown]
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
def _color_forms() -> dict[str, str]:
    """Colores de cualquier rubro (ropa, muebles, griferías…) con sus formas: «roja», «rojos» -> rojo."""
    base = {"negro": [], "blanco": [], "rojo": [], "azul": ["azules"], "verde": ["verdes"],
            "amarillo": [], "gris": ["grises"], "marron": ["marrones"], "beige": [],
            "rosa": ["rosado", "rosada", "rosados", "rosadas"], "violeta": ["violetas", "lila", "lilas"],
            "naranja": ["naranjas"], "celeste": ["celestes"], "dorado": [], "plateado": [],
            "bordo": ["bordeaux"], "crema": ["cremas"], "turquesa": ["turquesas"], "nude": [],
            "fucsia": ["fucsias"], "camel": [], "natural": ["naturales"], "transparente": ["transparentes"],
            "cromo": ["cromada", "cromado", "cromadas", "cromados"], "multicolor": []}
    out: dict[str, str] = {}
    for color, extra in base.items():
        forms = {color, *extra}
        if color.endswith("o"):
            stem = color[:-1]
            forms |= {stem + "a", stem + "os", stem + "as"}
        elif not color.endswith(("s", "z")):
            forms.add(color + "s")
        out.update({f: color for f in forms})
    out["plateada"] = out["plateado"] = "plateado"
    return out


_COLORS = _color_forms()
# «lo de siempre», «repetí mi pedido», «lo mismo que la otra vez», «mi último pedido».
_RE_REORDER = re.compile(r"\b(lo de siempre|(quiero|dame|mandame|pasame|haceme|armame)( de nuevo)? lo mismo"
                         r"|repet\w*( el| mi| lo)? (pedido|compra|ultimo)|como la (otra|ultima) vez|otra vez lo mismo"
                         r"|(repetir|volver a pedir|quiero|dame) (mi|el) (ultimo|anterior) pedido)\b")
# «¿cómo va mi último pedido?» es seguimiento, no recompra.
_RE_STATUS_Q = re.compile(r"\b(como va|estado|llego|llega|donde esta|seguimiento|cuando llega|ya salio)\b")


def _detail(o: dict[str, Any]) -> str:
    """Lo que distingue a variantes con el mismo nombre (color, talle, sabor), si el nombre no lo dice:
    «Remera básica (Roja, talle M)»."""
    specs, name = o.get("specs") or {}, normalize(o["name"])
    parts = [o.get("variant_label")] if o.get("variant_label") else [specs.get("color"), specs.get("sabor")]
    parts = [p for p in parts if p and normalize(str(p)) not in name]
    if specs.get("talle") and f"talle {normalize(str(specs['talle']))}" not in name:
        parts.append(f"talle {specs['talle']}")
    return f" ({', '.join(str(p) for p in parts)})" if parts else ""
# Talle de ropa o calzado: «talle M», «talle 42» (la letra sola es ambigua: sólo después de «talle»).
_RE_TALLE = re.compile(r"\btalles?\s+(xxxl|xxl|xl|xxs|xs|s|m|l|u|unico|\d{1,2})\b")
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
agrega agregame agregala agregalo agregalas agregalos agregar agregas suma sumame sumala sumalo sumas
anota anotame dame mandame llevo pone poneme ponele saca sacame sacala sacalo sacalas sacalos quita
quitame quitala quitalo borra borrame elimina dejame deja dejala dejalo nomas solo sola sean todas
todos uno dos tres cuatro cinco seis siete ocho nueve diez par unidad unidades decime total queda
bien tambien ademas nueva nuevo nuevas nuevos moderna moderno modernas modernos saldria saldrian
costaria costarian cuanto armar carrito todavia comprar hoy numero nro disponibles
espera perdon mmm bueno dale listo mira fijate igual porfa
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
_RE_INFO = re.compile(r"\b(envio|envios|envian|mandan|entrega|entregan|llega|llegan|avisas|avisame|whatsapp|"
                      r"mail|email|correo|retiro|retirar|horario|horarios|"
                      r"abren|atienden|abierto|factura|facturan|cuotas|tarjeta|medios? de pago|formas? de pago|"
                      r"se puede pagar|puedo pagar|direccion|donde (estan|queda)|local)\b")
_MONEY_IN_DOCS = re.compile(r"(\$|\bars\b|\busd\b|u\$s)\s?\d[\d.,]*|\d[\d.,]*\s?(pesos|dolares|dólares|ars\b|usd\b)", re.I)
# "Busco/tenés/quiero…": pedido de productos, aunque mencione una palabra de documentos.
_RE_PRODUCT_ASK = re.compile(r"\b(busco|buscando|quiero|necesito|me mostras|mostrame)\b")
# Preguntas que suelen responder los documentos del negocio (garantías, instalación, fichas).
_RE_DOCS = re.compile(r"\b(garantia|garantias|instal\w*|manual|ficha|medidas?|compatib\w*|devolucion\w*|"
                      r"cambio|cambios|mantenimiento|limpi\w*|repuesto para|como se (usa|coloca|instala))\b")
# "Lo mismo que la otra vez", "mis compras anteriores": historial del cliente.
_RE_HISTORY = re.compile(r"\b(lo mismo que (la otra vez|antes|la ultima)|(mi|mis) (ultima|ultimas|anterior|"
                         r"anteriores) compras?|que (te|les) compre|compre antes|la otra vez)\b")
_RE_SHIP_TO = re.compile(r"\b(?:envi\w*|llega\w*|manda\w*|entrega\w*|reparte\w*|despacha\w*)\b"
                         r"(?:\s+\w+){0,2}?\s+(?:a|hasta|para)\s+(?P<place>[a-z0-9 ]{3,40}?)\s*[?.!]*$")
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
_RE_STOCK_Q = re.compile(r"\b(stock|disponib\w*|quedan|queda|cuantas hay|cuantos hay|hay de)\b")
# Agradecimiento o despedida sin otro pedido ("gracias!", "listo, muchas gracias, chau").
_SOCIAL = set("""gracias muchas muchisimas mil genial perfecto buenisimo barbaro joya listo excelente
bueno ok dale no chau saludos hasta luego nos vemos igualmente a vos por todo un abrazo crack capo
igual despues veo vuelvo lo pienso adios nada""".split())

# --- Consentimiento: qué puede cambiar el carrito en este mensaje -------------------------------
# Una consulta, una pregunta o un "todavía no" no cambian el carrito; una orden explícita sí; un
# "sí", "la 2" o "la Aquaflux" sólo acepta la última propuesta de agregar (state["offer"]).
# Heurístico: cubre las formas habituales en español rioplatense, no toda la lengua.
_RE_NO_CART = re.compile(r"\b(no (quiero|voy a|necesito|vamos a)\b|"
                         r"todavia no|aun no|sin (agregar|armar|comprar)|"
                         r"no (me )?(lo |la |los |las )?(agregues|sumes|pongas|anotes)|"
                         r"solo (pregunto|consulto|queria saber|para saber)|por ahora no)\b")
_RE_ADD_ORDER = re.compile(r"\b(agrega\w*|suma(me|la|lo|las|los|s)?|anota\w*|dame|mandame|me (llevo|quedo con)|"
                           r"llevo|pone(me|le)|quiero|queria|necesito)\b")
# Dentro de una pregunta sólo cuenta el pedido directo ("¿me agregás dos?"), no "¿hay para comprar?".
_RE_IMPERATIVE = re.compile(r"\b(agrega\w*|suma(me|la|lo|las|los|s)?|anota\w*|pone(me|le)|saca\w*|quita\w*|"
                            r"borra\w*|elimina\w*|deja(me|la|lo)?)\b")
# "quiero alguna canilla", "qué tenés en negro": explorar, no agregar.
_RE_EXPLORE = re.compile(r"\b(algun[ao]?s?|algo|opciones|que (tengas|tenes|tienen|haya)|mostra\w*|ver|busco|buscando)\b")
_RE_YES = re.compile(r"^\s*(si|sii+|dale|ok|okey|de una|listo|va|perfecto)\b[\s,.!]*")
_RE_PARTS = re.compile(r",?\s*\b(?:y tambien|y ademas|tambien|ademas)\b")
_RE_SET = re.compile(r"\b(deja(me|la|lo)?|que sean?|mejor|solo|nomas|cambia\w*|en total)\b")
_RE_LESS = re.compile(r"\b(\d+|una?|uno|dos|tres) menos\b(?!\s+de)")
_RE_PRONOUN = re.compile(r"\b(saca|quita|borra)(la|lo|las|los)\b|\b(esa|ese|esas|esos)\b")
# Números que no son unidades: precios, medidas, pesos, la opción elegida y "dos llaves".
_RE_NOT_QTY = re.compile(r"\$\s?\d[\d.,]*|\d[\d.,]*\s?(mil|k|lucas|pesos|g|gr|grs|gramos|kg|kilos?|cm|mm|m|mts|"
                         r"metros?|l|lts|litros?|w|watts?|v|pulgadas?|\"|%)(?![a-z])|\d+/\d+|"
                         r"\b(la|el|opcion|numero|nro)\s*\.?\s*((numero|nro)\s*\.?\s*)?\d\b|\b(?:dos|2) llaves\b")
_RE_OPTION = re.compile(r"\b(?:la|el|opcion|numero|nro)\s*\.?\s*(?:(?:numero|nro)\s*\.?\s*)?(\d)\b(?![/.,]\d)")
_RE_PRICE_Q = re.compile(r"\b(cuanto|sale|salen|saldria|saldrian|cuesta|cuestan|costaria|costarian|precio)\b")
_RE_CATALOG = re.compile(r"\b(que (productos|cosas|articulos)|que (tenes|tienen|venden|vendes|manejan)\b|catalogo)")
# Pedido explícito de una persona; "es para una persona mayor" no lo es.
_RE_HUMAN = re.compile(r"\b(pasa\w*|habla\w*|comunica\w*|deriva\w*|atiend\w*|atienda|contact\w*)\b[^.?!]{0,25}?"
                       r"\b(persona|humano|alguien|vendedor\w*|asesor\w*|encargad\w*|dueno|duena)\b")
_RE_NOTIFY = re.compile(r"\b(como|cuando|por donde|quien) (me )?(avisan|avisas|contactan|contactas|llaman|escriben|"
                        r"responden|entero)\b|\bme (van a|vas a) (avisar|contactar|llamar|escribir)\b")


def _parts(text: str) -> list[str]:
    """«quiero un flexible y también alguna canilla» -> un pedido por parte."""
    return [p.strip(" ,.") for p in _RE_PARTS.split(text) if p.strip(" ,.")] or [text]


def _adds(part: str) -> bool:
    """Orden de agregar: verbo explícito o "uno solo"/"que sean 2" sobre algo que se elige."""
    edit = _edit(part)
    return (not _RE_NO_CART.search(part)
            and bool(_RE_ADD_ORDER.search(part) or (edit and edit[0] == "set"))
            and not _RE_EXPLORE.search(part))


def _consent(message: str, text: str, offer: Optional[dict[str, Any]]) -> str:
    """'order' (orden de cambiar el carrito o comprar), 'pick' (puede aceptar la propuesta vigente) o
    'read' (consulta: no cambia el carrito)."""
    parts = [part for part in _parts(text) if not _RE_NO_CART.search(part)]
    if not parts:
        return "read"
    text = " ".join(parts)
    if "?" in message or "¿" in message:
        buys = _RE_BUY.search(text) and not re.search(r"\b(para|puedo|se puede) (comprar|pagar)\b", text)
        return "order" if _RE_IMPERATIVE.search(text) or buys else "read"
    if (_RE_ADD_ORDER.search(text) or _RE_IMPERATIVE.search(text) or _RE_BUY.search(text)
            or _RE_DONE.match(text) or _edit(text)):
        return "order"
    return "pick" if offer else "read"


def _edit(text: str) -> Optional[tuple[str, int]]:
    """Cambio de cantidad de una línea: ('set', n) fija, ('sub', n) resta, ('del', 0) la quita."""
    if _RE_REMOVE.search(text):
        n = _qty(text)
        return ("del", 0) if n is None or re.search(r"\b(todas?|todos?)\b", text) else ("sub", n)
    less = _RE_LESS.search(text)
    if less:
        return ("sub", _qty(less.group(0)) or 1)
    n = _qty(text)
    return ("set", n) if n is not None and _RE_SET.search(text) else None


# Pedido de comparar o recomendar entre opciones: se responde con la ficha (no con rasgos libres).
_RE_COMPARE = re.compile(r"\b(diferencias?|compar\w*|recomend\w*|cual (me )?(conviene|sirve)|cual es mejor|"
                         r"cual (elijo|llevo)|versus|vs)\b")
# Palabras del pedido de comparar que no son un dato a buscar en la ficha.
_INTENT = set("""diferencia diferencias compara comparar comparas comparame comparacion recomendas
recomendarias recomendame recomienda conviene sirve elijo llevo entre versus tiene tienen cual mejor
para usar usarla usarlo""".split())
_RE_NO_BUDGET = re.compile(r"\b(sin (limite|tope|presupuesto)( de precio)?|cualquier precio|no importa el precio)\b")


# Renglón de una lista: «40cm» es la medida «40 cm»; «1/2» (pulgadas) también tiene que coincidir.
_RE_GLUED_UNIT = re.compile(r"(\d)(cm|mm|m|g|kg|w)\b")
_RE_FRACTION = re.compile(r"\b\d+/\d+\b")


def _haystack(o: dict[str, Any]) -> str:
    """Texto del producto donde tiene que estar cada palabra de un renglón (como la búsqueda)."""
    return normalize(" ".join([o["name"], o.get("brand") or "", o["category"], o.get("variant_group") or "",
                               o.get("variant_label") or "", json.dumps(o.get("specs") or {}, ensure_ascii=False)]))


def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z0-9]+", normalize(text)) if len(w) >= 4}


def _social(text: str) -> bool:
    words = re.findall(r"[a-z]+", text)
    return any(w in ("gracias", "chau", "saludos") for w in words) and all(w in _SOCIAL for w in words)


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


def _option(text: str) -> Optional[int]:
    """Número de opción mencionado: "la 2", "la nro3", "nro. 3", "la tercera"."""
    full = _choice(text)
    if full is not None:
        return full
    m = _RE_OPTION.search(text)
    if m:
        return int(m.group(1))
    return next((_ORDINALS[t] for t in re.findall(r"[a-z0-9]+", text) if t in _ORDINALS), None)


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


def _units(text: str) -> Optional[int]:
    """Unidades de un pedido; un mensaje que es sólo una opción ("2", "la 2") no las dice."""
    return None if _choice(text) is not None else _qty(text)


def _qty(text: str) -> Optional[int]:
    """Unidades dichas en el texto, o None. Precios, medidas y el número de opción no cuentan."""
    text = _RE_NOT_QTY.sub(" ", text)
    m = re.search(r"\b(\d{1,3})\b", text)
    if m:
        return int(m.group(1))
    for word, n in _WORD_NUMBERS.items():
        if n > 1 and re.search(rf"\b{word}\b", text):
            return n
    return 1 if re.search(r"\b(un|una|uno)\b", text) else None


def _filters(text: str) -> dict[str, Any]:
    tokens = re.findall(r"[a-z0-9]+", text)
    color = next((_COLORS[t] for t in tokens if t in _COLORS), None)
    ambiente = next((_AMBIENTES[t] for t in tokens if t in _AMBIENTES), None)
    talle_m = _RE_TALLE.search(text)
    talle = talle_m.group(1).upper() if talle_m else None
    if talle_m:
        tokens = re.findall(r"[a-z0-9]+", text[:talle_m.start()] + " " + text[talle_m.end():])
    # Una medida ("40 cm", "500 g") describe el producto: es un filtro, no una cantidad.
    keywords = [f"{n} {u}" for n, u in re.findall(r"\b(\d+(?:,\d+)?)\s?(cm|mm|m|g|kg|w)\b", text)]
    for t in tokens:
        if t in _COLORS or t in _AMBIENTES or t in _STOP or t.isdigit() or len(t) < 3:
            continue
        t = _SYNONYMS.get(t, t)
        # plural simple: canillas -> canilla, llaves -> llave
        if len(t) > 4 and t.endswith("es") and not t.endswith("ees"):
            t = t[:-2] if t[-3] not in "aeiou" else t[:-1]
        elif len(t) > 3 and t.endswith("s"):
            t = t[:-1]
        if t not in keywords and t not in _STOP:
            keywords.append(t)
    return {"keywords": keywords, "color": color, "ambiente": ambiente, "talle": talle}


# --- Estado de la conversación ------------------------------------------------------
def _load_state(tenant_id: str, conversation_id: str) -> tuple[dict[str, Any], bool]:
    """Estado del agente y si una persona del negocio tomó la conversación (bandeja)."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("select agent_state, taken_by from conversations where tenant_id = %s and id = %s",
                    (tenant_id, conversation_id))
        row = cur.fetchone()
    return (dict(row["agent_state"] or {}) if row else {}), bool(row and row["taken_by"])


def _finish_turn(tenant_id: str, conversation_id: str, state: dict[str, Any], reply: str,
                 ui: Optional[dict[str, Any]], profile_version: Optional[int], handoff: Optional[str]) -> bool:
    """Cierra el turno en UNA transacción con la conversación bloqueada: estado, derivación y
    respuesta. Si una persona tomó la conversación mientras el agente pensaba, no se guarda nada
    (el agente no habla encima de una persona). `handoff`: 'asked' | 'quote' | None."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("select taken_by, needs_human_at from conversations where tenant_id = %s and id = %s for update",
                    (tenant_id, conversation_id))
        row = cur.fetchone()
        if row and row["taken_by"]:
            return False
        if handoff and row and row["needs_human_at"] is None:
            webhooks.enqueue(cur, tenant_id, "conversation.needs_human",
                             {"conversation_id": conversation_id, "reason": handoff})
            cur.execute("insert into handoff_events (tenant_id, conversation_id, reason) values (%s, %s, %s)",
                        (tenant_id, conversation_id, handoff))
        cur.execute(
            "update conversations set agent_state = %(state)s::jsonb, "
            "needs_human_at = case when %(why)s::text is null then needs_human_at else coalesce(needs_human_at, now()) end, "
            "needs_human_reason = case when %(why)s::text = 'asked' then 'asked' "
            "else coalesce(needs_human_reason, %(why)s::text) end "
            "where tenant_id = %(tenant)s and id = %(conv)s",
            {"state": json.dumps(state), "why": handoff, "tenant": tenant_id, "conv": conversation_id})
        opportunities._add_message(cur, tenant_id, conversation_id, "outbound", reply, ui or None, profile_version)
    return True


# --- Agente ----------------------------------------------------------------------
class _Turn:
    def __init__(self, ctx: ToolContext, state: dict[str, Any]):
        self.ctx = ctx
        self.state = state
        self.trace: list[dict[str, Any]] = []
        self.products: list[dict[str, Any]] = []
        self.payment: Optional[dict[str, Any]] = None
        self.requires_human = False
        self.asked_for_person = False     # derivó porque el cliente pidió una persona (no por cotización)
        self.by_topic = False             # derivó por un tema configurado por el negocio
        self.dry_run = False
        self.text = ""          # mensaje normalizado del turno (el comparador ve qué dato se pidió)
        self.raw = ""           # el mensaje tal como lo escribió el cliente (nombres, direcciones)
        self.offer: Optional[dict[str, Any]] = None   # propuesta de agregar del turno anterior
        self.slots: Optional[dict[str, Any]] = None   # turnos ofrecidos en el mensaje anterior
        self.delivery_state: Optional[dict[str, Any]] = None   # paso de entrega pendiente
        self.booking_ask = False
        self.consent = "read"   # ver _consent
        self.no_cart = False    # "todavía no quiero carrito": no se propone agregar
        self.blocked = False    # la última herramienta del modelo fue rechazada por el servidor
        self.model_answered = False   # el modelo respondió al menos una vez (si no, el modo es mock)
        self.quote: Optional[dict[str, Any]] = None   # última cotización de lista de este turno
        self._plan: Optional[tuple[dict[str, int], list[tuple[list[dict[str, Any]], Optional[int]]]]] = None
        self._edits: Optional[dict[str, int]] = None
        self._added: set[str] = set()

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

    # -- memoria y conocimiento (ver docs/research/2026-10-27-arquitectura-agentes-personalizados.md) --
    @property
    def customer(self) -> Optional[str]:
        if not hasattr(self, "_customer"):
            self._customer = customer_memory.customer_of(self.tenant, self.conv) if self.conv else None
        return self._customer

    def memory(self) -> list[str]:
        return customer_memory.facts(self.tenant, self.customer)

    def customer_history(self) -> str:
        """Memoria episódica just-in-time: pedidos anteriores del cliente con este negocio."""
        past = [o for o in customer_memory.history(self.tenant, self.customer) if o.get("id")]
        self.tool("historial_cliente", f"{len(past)} pedido(s) anterior(es)")
        if not self.customer:
            return "No tengo historial de este cliente (no lo reconozco de antes)."
        if not past:
            return "No tiene compras anteriores registradas con nosotros."
        lines = [f"Pedido #{o['number']} ({o['status_label']}): "
                 + ", ".join(f"{i['qty']} × {i['name']}" for i in o["items"]) for o in past]
        return "Compras anteriores:\n" + "\n".join(lines)

    def knowledge(self, query: str) -> Optional[str]:
        """Documentos del negocio (RAG). None si no hay nada relevante."""
        hits = knowledge.search(self.tenant, query)
        self.tool("buscar_info_negocio", f"{len(hits)} fragmento(s)")
        if not hits:
            return None
        # Los precios salen sólo del catálogo (vigencia, a pedido): un monto en un documento puede
        # estar viejo, así que no se repite.
        return "\n\n".join(f"Según «{h['title']}»: {_MONEY_IN_DOCS.sub('[precio: consultar]', h['content'][:600])}"
                             for h in hits)

    def info(self, text: str) -> str:
        """Responde con lo que el negocio cargó en su perfil; si no lo tiene, no lo inventa."""
        p = self.profile
        zones = (p.get("policies") or {}).get("delivery_zones") or []
        named = next((z for z in zones if normalize(z) in text), None)
        if named and agent_profile.tool_enabled(p, "consultar_envio"):
            return self.shipping(named)
        if not named and zones and agent_profile.tool_enabled(p, "consultar_envio"):
            # «¿envían a Bernal?»: el lugar no es una zona cargada; `shipping` lo ubica con Georef.
            m = _RE_SHIP_TO.search(text)
            if m:
                return self.shipping(m.group("place").strip())
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
        topics = [("envi", "shipping"), ("entreg", "shipping"), ("mand", "shipping"), ("lleg", "shipping"),
                  ("retir", "hours"),
                  ("horar", "hours"), ("abr", "hours"), ("atiend", "hours"), ("pag", "payment_methods"),
                  ("tarjet", "payment_methods"), ("cuota", "payment_methods")]
        for prefix, field in topics:
            if any(w.startswith(prefix) for w in words) and p.get(field):
                return p[field]
        found = self.knowledge(text) if agent_profile.tool_enabled(p, "buscar_info_negocio") else None
        if found:
            return found
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

    def _named(self, text: str) -> bool:
        """¿El texto nombra un producto (número de opción, rasgo, marca, color)?"""
        f = self.filters(text)
        return _option(text) is not None or bool(f["keywords"] or f["color"])

    def matches(self, text: str) -> list[dict[str, Any]]:
        """Productos a los que se refiere el texto: número de la última lista, rasgos o marca dentro
        de ella y, si ahí no hay, el catálogo. Varias coincidencias = ambiguo: no se elige al azar."""
        shown = self._shown()
        n = _option(text)
        if n is not None:
            return [shown[n - 1]] if 0 < n <= len(shown) else []
        tokens = re.findall(r"[a-z0-9]+", text)
        if shown and ("ultima" in tokens or "ultimo" in tokens):
            return [shown[-1]]
        f = self.filters(text)
        found: list[dict[str, Any]] = []
        if shown and (f["color"] or f["keywords"]):
            found = [o for o in shown
                     if (not f["color"] or o["specs"].get("color") == f["color"])
                     and all(k in normalize(f"{o['name']} {o['brand']} {json.dumps(o['specs'])}")
                             for k in f["keywords"] if k not in ("canilla",))]
        if not found and f["keywords"]:
            found = inventory.offers(self.tenant, keywords=f["keywords"], color=f["color"],
                                     ambiente=f["ambiente"], talle=f["talle"], limit=5)
        # Entre varias, las que no se pueden llevar (sin stock) no compiten, y "un flexible" es el
        # producto que ES un flexible, no la ducha "con flexible".
        sellable = [o for o in found if o["pricing_mode"] != "fixed" or o["available"] > 0]
        found = sellable if len(found) > 1 and sellable else found
        kind = [o for o in found if normalize(o["name"]).split()[0] in f["keywords"]]
        return kind if len(found) > 1 and len(kind) == 1 else found

    def focus(self) -> Optional[dict[str, Any]]:
        """El producto del que se viene hablando cuando el mensaje no nombra ninguno ("agregame
        dos"): la única propuesta vigente, el último elegido o la única opción mostrada."""
        ids = (self.offer or {}).get("ids") or []
        pick = (ids[0] if len(ids) == 1 else None) if ids else self.state.get("selected")
        if pick:
            found = inventory.offers(self.tenant, ids=[pick], limit=1)
            return found[0] if found else None
        shown = self._shown()
        return shown[0] if len(shown) == 1 else None

    def _candidates(self, text: str) -> list[dict[str, Any]]:
        return self.matches(text) if self._named(text) else [o for o in [self.focus()] if o]

    def resolve(self, text: str) -> Optional[dict[str, Any]]:
        found = self._candidates(text)
        return found[0] if len(found) == 1 else None

    def pick(self, opcion: Optional[int] = None, consulta: str = "") -> Optional[dict[str, Any]]:
        """Producto por número de la última lista o por descripción (para el planner con LLM)."""
        if opcion is not None:
            shown = self._shown()
            return shown[opcion - 1] if 0 < opcion <= len(shown) else None
        return self.resolve(normalize(consulta)) if consulta else None

    # -- qué autorizó el cliente en este mensaje (lo usan las reglas y el planner con LLM) --
    def _offer_qty(self, o: dict[str, Any]) -> Optional[int]:
        offer = self.offer or {}
        return offer.get("qty") if o["id"] in (offer.get("ids") or []) else None

    def _picked(self, text: str) -> list[dict[str, Any]]:
        """Lo que elige un "sí, la Aquaflux" / "la 2" entre la propuesta vigente."""
        ids = (self.offer or {}).get("ids") or []
        rest = _RE_YES.sub("", text, count=1).strip(" ,.!")
        if rest and self._named(rest):
            return [o for o in self.matches(rest) if o["id"] in ids]
        return inventory.offers(self.tenant, ids=ids, limit=len(ids)) if ids and len(rest) < len(text) else []

    def add_plan(self) -> tuple[dict[str, int], list[tuple[list[dict[str, Any]], Optional[int]]]]:
        """Lo que el cliente pidió agregar según el servidor: {id: cantidad} y las elecciones que
        quedaron ambiguas. El modelo sólo puede agregar eso."""
        if self._plan is None:
            ok: dict[str, int] = {}
            unclear: list[tuple[list[dict[str, Any]], Optional[int]]] = []
            parts = ([self.text] if self.consent == "pick" else
                     [p for p in _parts(self.text) if _adds(p)] if self.consent == "order" else [])
            if self.edit_plan():        # "dejame dos" corrige una línea: no autoriza agregar otra cosa
                parts = [p for p in parts if _RE_ADD_ORDER.search(p)]
            for part in parts:
                found = self._picked(part) if self.consent == "pick" else self._candidates(part)
                if len(found) == 1:
                    ok[found[0]["id"]] = _units(part) or self._offer_qty(found[0]) or 1
                elif found:
                    unclear.append((found, _units(part)))
            self._plan = (ok, unclear)
        return self._plan

    def edit_line(self, op: tuple[str, int], cart: Optional[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], str]:
        """Línea del carrito a la que se aplica un cambio de cantidad: (línea, "") o (None, motivo):
        'absent' (nombra algo que no está), 'unclear' (varias posibles)."""
        lines = cart["items"] if cart else []
        if self._named(self.text):
            ids = {o["id"] for o in self.matches(self.text)}
            hit = [it for it in lines if it["item_id"] in ids]
            return (hit[0], "") if len(hit) == 1 else (None, "unclear" if hit else "absent")
        kind, n = op
        hit = lines if len(lines) == 1 else [it for it in lines if kind == "set" and it["qty"] > n]
        if len(hit) != 1:
            # Sin producto nombrado: la línea que se viene corrigiendo o la que señala "sacala".
            focus = self.state.get("edited") or (self.state.get("selected") if _RE_PRONOUN.search(self.text) else None)
            hit = [it for it in lines if it["item_id"] == focus]
        return (hit[0], "") if len(hit) == 1 else (None, "unclear")

    def edit_plan(self) -> dict[str, int]:
        """{línea: cantidad final} del cambio pedido. Se calcula una vez, con el carrito previo:
        "sacá una" resta una aunque el modelo llame a dos herramientas."""
        if self._edits is None:
            self._edits = {}
            op = _edit(self.text) if self.consent == "order" else None
            line = self.edit_line(op, orders.get_cart(self.tenant, self.conv))[0] if op else None
            if op and line:
                kind, n = op
                self._edits[line["item_id"]] = n if kind == "set" else max(0, line["qty"] - n) if kind == "sub" else 0
        return self._edits

    def refuse(self, name: str, why: str) -> str:
        """Acción del modelo que el cliente no pidió: no se ejecuta y el modelo lo sabe."""
        self.blocked = True
        self.tool("control", f"{name} rechazada: {why}")
        return f"No se ejecutó {name}: {why}."

    def cart_tool(self, name: str, o: dict[str, Any]) -> str:
        """Carrito pedido por el modelo. Qué producto y cuántas unidades lo decide el mensaje del
        cliente (add_plan/edit_plan), no la propuesta del modelo."""
        if self.consent == "read":
            return self.refuse(name, "el cliente consultó o no pidió cambiar el carrito; respondé sin tocarlo")
        edits = self.edit_plan()
        if o["id"] in edits:
            cart = orders.get_cart(self.tenant, self.conv)
            current = next((it["qty"] for it in (cart or {}).get("items", []) if it["item_id"] == o["id"]), 0)
            if current == edits[o["id"]]:
                self.blocked = True         # ya hecho en este turno (p. ej. "quitar y volver a agregar")
                return f"Ya quedó: {current} × {o['name']}."
            return self.set_qty(o["id"], o["name"], edits[o["id"]])
        if name == "agregar_al_carrito":
            ok, unclear = self.add_plan()
            if o["id"] in ok:
                return self.add_offer(o, ok[o["id"]])
            if unclear and not self.products:
                return self.ask_which(*unclear[0])
            return self.refuse(name, "el cliente no pidió agregar ese producto o no está claro cuál; preguntale")
        return self.refuse(name, "no está claro qué línea ni cuántas unidades; preguntale")

    def apply_plan(self) -> list[str]:
        """Con LLM, lo que el cliente ordenó sin ambigüedad lo ejecuta el servidor antes del modelo:
        el modelo podía omitirlo o apuntar a una lista que cambió en el mismo turno. Lo ambiguo
        queda para que el modelo pregunte."""
        if self.consent == "read":
            return []
        ok, unclear = self.add_plan()       # antes de cambiar nada: el foco todavía es el del turno
        cart = orders.get_cart(self.tenant, self.conv)
        names = {it["item_id"]: it["name"] for it in (cart or {}).get("items", [])}
        out = [self.set_qty(i, names[i], qty) for i, qty in self.edit_plan().items()]
        for o in inventory.offers(self.tenant, ids=list(ok), limit=len(ok)) if ok else []:
            out.append(self.add_offer(o, ok[o["id"]], tail=False))
        if unclear:     # la pregunta "¿cuál?" con la lista real: tarjetas, texto y "sí, la X" coinciden
            out.append(self.ask_which(*unclear[0]))
        return out

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
        return f"{i}. {o['name']}{_detail(o)}{brand} · {tail}"

    def show(self, items: list[dict[str, Any]], intro: str) -> str:
        # Repetir una búsqueda conserva las posiciones y actualiza cada producto una sola vez.
        by_id = {o["id"]: o for o in self.products}
        by_id.update((o["id"], o) for o in items)
        self.products = list(by_id.values())
        ids = [o["id"] for o in self.products]
        self.state["last_results"] = ids
        if not self.no_cart:        # mostrar opciones es proponerlas: "la 2" / "sí, esa" las acepta
            self.state["offer"] = {"ids": ids, "qty": None}
        lines = [intro] + [self._line(i, o) for i, o in enumerate(self.products, 1)]
        return "\n".join(lines)

    def ask_which(self, items: list[dict[str, Any]], qty: Optional[int] = None) -> str:
        text = self.show(items, f"¡Tengo {len(items)} que te pueden servir!")
        if qty and self.state.get("offer"):
            self.state["offer"]["qty"] = qty          # "tres de esa": al elegir, van las tres
        return text + "\n¿Cuál te agrego? Decime el número."

    def no_option(self, n: int) -> str:
        shown = self._shown()
        if not shown:
            return "No tengo una lista de opciones abierta. ¿Qué estás buscando?"
        if not self.no_cart:        # la pregunta vuelve a proponer la lista: "la 1" la responde
            self.state["offer"] = {"ids": [o["id"] for o in shown], "qty": None}
        return (f"No tengo una opción {n} en la última lista: hay {len(shown)}. "
                f"¿Cuál querés? Elegí entre 1 y {len(shown)}.")

    def overview(self) -> str:
        """"¿Qué tenés?": las categorías reales del catálogo, sin suponer productos por el rubro."""
        cats: dict[str, int] = {}
        for o in inventory.offers(self.tenant, limit=500):
            cats[o["category"]] = cats.get(o["category"], 0) + 1
        self.tool("buscar_productos", f"categorías: {len(cats)}")
        if not cats:
            return "Todavía no hay productos cargados en el catálogo."
        listed = ", ".join(f"{c.capitalize()} ({n})" for c, n in sorted(cats.items(), key=lambda x: (-x[1], x[0])))
        return (f"Esto es lo que tenemos en el catálogo: {listed}. ¿Qué estás buscando? Contame el tipo de "
                "producto o para qué lo necesitás y te muestro opciones.")

    def cart_text(self, cart: Optional[dict[str, Any]]) -> str:
        if not cart or not cart["items"]:
            return "Tu carrito está vacío."
        lines = [f"• {it['qty']} × {it['name']} — {_money(it['line_total'])}" for it in cart["items"]]
        return "\n".join(lines + [f"Total: {_money(cart['total'])}"])

    # -- intenciones --
    def search(self, text: str, budget: Optional[float]) -> str:
        drop_budget = bool(_RE_NO_BUDGET.search(text))
        f = self.filters(_RE_NO_BUDGET.sub(" ", text))
        query = {"keywords": f["keywords"], "color": f["color"], "ambiente": f["ambiente"], "talle": f["talle"]}
        last = self.state.get("last_query")
        if last and not f["keywords"] and (budget is not None or f["color"] or f["ambiente"] or f["talle"] or drop_budget):
            # Corrección parcial ("¿y en cromo?", "hasta 150 mil", "sin límite de precio") => sobre la
            # última búsqueda, con su tope salvo que lo cambie o lo quite. Otro tipo de producto
            # arranca de cero (sin tope).
            query = {k: query[k] or last.get(k) for k in query}
            if budget is None and not drop_budget:
                budget = last.get("budget")
        if not (query["keywords"] or query["color"] or query["ambiente"] or query["talle"]):
            if _RE_CATALOG.search(text) or not text.strip():
                return self.overview()
            if self.state.get("last_results"):
                return ("No te entendí. Si querés alguna de las opciones, decime el número "
                        "(por ejemplo \"la 2\"), o contame qué otra cosa buscás.")
            if _RE_STOCK_Q.search(text) or _RE_PRICE_Q.search(text):
                return "¿De qué producto querés saber? Decime cuál y te digo precio y disponible."
            return (self.profile.get("greeting") or
                    "¡Hola! Soy el asistente de ventas. Contame qué buscás.")
        self.state["last_query"] = {**query, "budget": budget}
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
                    "talle, medida o modelo)?" + hint)
        if all(o["pricing_mode"] == "fixed" and o["available"] == 0 for o in found):
            return self.out_of_stock(found)
        if budget is not None:
            in_stock = [o for o in found if o["pricing_mode"] == "fixed" and o["available"] > 0]
            text_out = self.show(found, f"Hasta {_money(budget)} tengo:")
            if not in_stock:
                return text_out + "\nNinguna tiene stock ahora, así que no te las puedo prometer."
            best = in_stock[0]
            return (text_out + f"\nLa más conveniente con stock es la {best['name']} "
                    f"({best.get('brand') or 'sin marca'}) a {_money(best['price'])}."
                    + ("" if self.no_cart else " ¿Te la agrego?"))
        one = len(found) == 1
        listed = self.show(found, "¡Mirá, tengo esta que te puede servir!" if one
                           else f"¡Tengo {len(found)} que te pueden servir!")
        if self.no_cart:
            return listed
        places = sorted({o["specs"].get("ambiente") for o in found} - {None})
        if not query["ambiente"] and len(places) > 1:
            # Falta el dato que cambia la elección: una pregunta concreta, sin descartar opciones.
            return listed + f"\n¿Es para {' o para '.join(places)}? Si alguna ya te sirve, decime el número."
        sizes = sorted({str(o["specs"].get("talle")) for o in found if o["specs"].get("talle")})
        if not query.get("talle") and len(sizes) > 1:
            return listed + f"\n¿Qué talle buscás? Hay {', '.join(sizes)}."
        return listed + ("\n¿Te la agrego?" if one else "\n¿Querés que te agregue alguna?")

    def out_of_stock(self, items: list[dict[str, Any]]) -> str:
        """Escenario D: no promete disponibilidad; ofrece sustitutos REALES con stock."""
        o = items[0]
        skip = [i["id"] for i in items]
        # Primero, las otras variantes del mismo modelo con stock («no hay en negro, sí en cromo»);
        # después, alternativas reales de la misma categoría.
        siblings = (inventory.offers(self.tenant, variant_group=o["variant_group"], in_stock_only=True,
                                     exclude=skip, limit=4) if o.get("variant_group") else [])
        alts = siblings + inventory.offers(self.tenant, category=o["category"],
                                           ambiente=o["specs"].get("ambiente"), in_stock_only=True,
                                           exclude=skip + [s["id"] for s in siblings], limit=4 - len(siblings))
        self.tool("consultar_stock", f"{o['sku']}: 0 disponibles; {len(alts)} alternativa(s)")
        head = (f"La {o['name']} está sin stock y no tengo fecha de reposición confirmada, "
                "así que no te la puedo prometer.")
        if not alts:
            self.state["last_results"] = [i["id"] for i in items]
            return head + " Si querés, le aviso al equipo para que te contacten cuando vuelva."
        return self.show(alts, head + " Te puedo ofrecer estas, que sí tienen stock:")

    def compare(self, text: str, picks: Optional[list[int]] = None,
                budget: Optional[float] = None) -> Optional[str]:
        """Comparación con hechos de la ficha (nombre, precio, stock, specs, descripción); nada
        que no esté cargado. Productos: los números dados, los nombrados o toda la última lista,
        hasta el presupuesto si lo hay. None si ninguno entra (entonces se busca de nuevo)."""
        if not agent_profile.tool_enabled(self.profile, "comparar_productos"):
            self.requires_human = True
            self.tool("comparar_productos", "deshabilitada por el negocio")
            return "Para recomendarte entre estas opciones te ayuda una persona del equipo. Ya les aviso."
        shown = self._shown()
        if not shown:
            return None
        if picks is None:
            picks = [int(n) for n in re.findall(r"\b(\d)\b", text)]
            picks += [_ORDINALS[t] for t in re.findall(r"[a-z0-9]+", text) if t in _ORDINALS]
            words = _stems(text)
            for i, o in enumerate(shown, 1):
                others = set().union(*(_stems(x["name"]) for x in shown if x is not o))
                if (_stems(o["name"]) - others) & words:
                    picks.append(i)
        nums = sorted({n for n in picks if 0 < n <= len(shown)})
        if len(nums) < 2:
            nums = list(range(1, min(len(shown), 4) + 1))
        if budget is not None:
            nums = [n for n in nums if shown[n - 1]["price"] is not None and shown[n - 1]["price"] <= budget]
            if not nums:
                return None
        items = [shown[n - 1] for n in nums]
        self.tool("comparar_productos", ", ".join(o["sku"] for o in items))
        lines = ["Te las comparo con lo que figura en la ficha"
                 + (f" (hasta {_money(budget)}):" if budget is not None else ":")]
        for n, o in zip(nums, items):
            ficha = ", ".join(f"{k}: {v}" for k, v in (o.get("specs") or {}).items())
            lines.append(self._line(n, o) + (f" ({ficha})" if ficha else "")
                         + (f". {o['description']}" if o.get("description") else ""))
        keys = sorted({k for o in items for k in (o.get("specs") or {})})
        diff = [f"{k}: " + " / ".join(str(o["specs"].get(k, "sin dato")) for o in items)
                for k in keys if len({str(o["specs"].get(k)) for o in items}) > 1]
        lines.append("Diferencias en la ficha: " + "; ".join(diff) + "." if diff else
                     "En la ficha no hay otras diferencias cargadas además del nombre, el precio y el stock.")
        sellable = [(n, o) for n, o in zip(nums, items)
                    if o["pricing_mode"] == "fixed" and o["price"] is not None and o["available"] > 0]
        if sellable:
            n, o = min(sellable, key=lambda x: x[1]["price"])
            lines.append(f"La más económica con stock es la {n} ({_money(o['price'])}).")
        # Lo que pidió (uso, prestación, dato) y no figura en ninguna ficha comparada: lo ve una persona.
        known = _stems(" ".join(f"{o['name']} {o.get('brand') or ''} {json.dumps(o.get('specs') or {}, ensure_ascii=False)} "
                                f"{o.get('description') or ''}" for o in items))
        asked = [w for w in re.findall(r"[a-z]+", self.text or text)
                 if len(w) >= 4 and w not in _STOP and w not in _INTENT and w[:5] not in known]
        if asked:
            self.requires_human = True
            lines.append(f"Lo que preguntás («{' '.join(asked)}») no figura en la ficha: lo confirma una "
                         "persona del equipo.")
        else:
            lines.append("Si necesitás otro dato (medida, caudal, compatibilidad), preguntame y te digo "
                         "si figura.")
        return "\n".join(lines)

    def stock(self, text: str) -> str:
        o = self.resolve(text)
        if o is None:
            return self.search(text, None)
        return self.stock_offer(o, _qty(text))

    def stock_offer(self, o: dict[str, Any], qty: Optional[int] = None) -> str:
        """Disponible y precio; con cantidad, cotiza sin tocar el carrito y propone agregarla."""
        self.state["selected"] = o["id"]
        self.tool("consultar_stock", f"{o['sku']}: {o['available']} disponibles")
        if o["pricing_mode"] != "fixed":
            return f"La {o['name']} es a pedido: una persona del negocio te confirma plazo y precio."
        if o["available"] == 0:
            return self.out_of_stock([o])
        qty = min(qty or 1, o["available"])
        text = f"Sí, de la {o['name']} hay {o['available']} disponibles, a {_money(o['price'])} c/u."
        if qty > 1 and o["price"] is not None:
            text += f" {qty} salen {_money(o['price'] * qty)}."
        if self.no_cart or o["price"] is None:
            return text
        self.state["offer"] = {"ids": [o["id"]], "qty": qty}
        return text + (f" ¿Te agrego {qty}?" if qty > 1 else " ¿Te la agrego?")

    def _quote_pick(self, desc: str, qty: int) -> Optional[dict[str, Any]]:
        """Producto de un renglón: uno que tenga TODAS las palabras y medidas del renglón (nunca uno
        «parecido»); entre esos, el más económico con precio y stock para la cantidad pedida."""
        text = _RE_GLUED_UNIT.sub(r"\1 \2", normalize(desc))
        f = self.filters(text)
        words = f["keywords"] + [w for w in _RE_FRACTION.findall(text) if w not in f["keywords"]]
        if not words:
            return None
        found = inventory.offers(self.tenant, keywords=words, color=f["color"], ambiente=f["ambiente"],
                                 talle=f["talle"], limit=10)
        found = [o for o in found if all(w in _haystack(o) for w in words)]
        priced = [o for o in found if o["pricing_mode"] == "fixed" and o["price"] is not None]
        return (next((o for o in priced if o["available"] >= qty), None)
                or next((o for o in priced if o["available"] > 0), None)
                or (found[0] if found else None))

    def quote_list(self, rows: list[tuple[str, int]]) -> str:
        """Cotiza una lista (descripción, cantidad) con precio, subtotal, stock y total del servidor.
        Lo a pedido o sin precio va a una persona; lo que no está en el catálogo se dice."""
        lines, priced, total, human, missing = [], [], 0.0, False, 0
        for desc, qty in rows:
            o = self._quote_pick(desc, qty)
            head = f"• {qty} {'unidad' if qty == 1 else 'unidades'} de «{desc}»: "
            if o is None:
                lines.append(head + "no lo encontré en el catálogo.")
                missing += 1
                continue
            head += f"{o['name']}{_detail(o)}" + (f" — {o['brand']}" if o.get("brand") else "") + " · "
            if o["pricing_mode"] != "fixed":
                human = True
                lines.append(head + "a pedido: precio y plazo los confirma una persona.")
            elif o["price"] is None:
                human = True
                lines.append(head + "sin precio vigente: lo confirma una persona.")
            elif o["available"] == 0:
                lines.append(head + f"{_money(o['price'])} c/u, SIN STOCK: no entra en el total.")
            else:
                n = min(qty, o["available"])
                sub = o["price"] * n
                total += sub
                priced.append((o, sub))
                lines.append(head + (f"{_money(o['price'])} c/u × {n} = {_money(sub)} · {o['available']} disponibles."
                                     if n == qty else
                                     f"{_money(o['price'])} c/u, sólo hay {o['available']} disponible"
                                     f"{'s' if o['available'] > 1 else ''}: {n} salen {_money(sub)}; faltan {qty - n}."))
        lines.append(f"Total de lo que hay en stock: {_money(total)}." if priced else
                     "No hay renglones con precio y stock para sumar un total.")
        if human:
            self.requires_human = True
            lines.append("Lo que está a pedido o sin precio: le paso tu consulta a una persona del negocio "
                         "para que te confirme precio y plazo.")
        if missing:
            lines.append("Lo que no encontré: si me lo describís de otra forma (marca, medida, modelo), lo busco.")
        text = "Cotización de tu lista (precios y stock de hoy):\n" + "\n".join(lines)
        self.quote = {"rows": priced, "total": total, "text": text}
        self.tool("cotizar_lista", f"{len(rows)} renglón(es), {len(priced)} con precio y stock, total {_money(total)}")
        return text

    def add(self, text: str, tail: bool = True) -> Optional[str]:
        """Orden explícita de agregar ("quiero un flexible", "agregame 3 de la Aquaflux")."""
        n = _option(text)
        if n is not None and not 0 < n <= len(self._shown()):
            return self.no_option(n)
        found = self._candidates(text)
        if not found:
            if self._named(text) or not self.state.get("last_results"):
                return None     # nombra algo que no está en la lista: se busca
            return "¿Cuál querés que te agregue? Decime el número de la lista o el producto."
        if len(found) > 1:
            return self.ask_which(found, _units(text))
        return self.add_offer(found[0], _units(text) or self._offer_qty(found[0]) or 1, tail)

    def order(self, text: str) -> Optional[str]:
        """Pedido compuesto: agrega cada parte identificable y explora el resto, en orden."""
        parts = _parts(text)
        if len(parts) == 1:
            return self.add(text) if _adds(text) else None
        out = []
        for i, part in enumerate(parts):
            if _RE_NO_CART.search(part):
                continue
            last = i == len(parts) - 1
            done = self.add(part, tail=last) if _adds(part) else None
            out.append(done or self.search(part, _budget(part)))
        return "\n\n".join(out)

    def take(self, text: str) -> Optional[str]:
        """"Sí", "la 2", "sí, la Aquaflux" en respuesta a la propuesta vigente de agregar."""
        rest = _RE_YES.sub("", text, count=1).strip(" ,.!")
        n = _option(rest) if rest else None
        if n is not None and not 0 < n <= len(self._shown()):
            return self.no_option(n)
        found = self._picked(text)
        if not found:
            return self.select(n) if n is not None else None
        if len(found) > 1:
            if rest and self._named(rest):
                return self.ask_which(found)
            self.state["offer"] = self.offer           # sigue vigente hasta que elija
            return f"¿Cuál querés? Decime el número (1 a {len(found)})."
        return self.add_offer(found[0], _units(rest) or self._offer_qty(found[0]) or 1)

    def select(self, n: int) -> str:
        """Elección sin propuesta de agregar vigente: muestra el producto y pregunta."""
        shown = self._shown()
        if not 0 < n <= len(shown):
            return self.no_option(n)
        return self.stock_offer(shown[n - 1])

    def add_offer(self, o: dict[str, Any], qty: int, tail: bool = True) -> str:
        if o["id"] in self._added:          # una orden se ejecuta una vez por mensaje
            self.blocked = True
            return f"Ya agregué la {o['name']} en este mensaje."
        qty = max(1, int(qty))
        self.state["selected"] = o["id"]
        res = orders.add_item(self.tenant, self.conv, o["id"], qty,
                              policies=(self.profile.get("policies") or {}) if self.dry_run else None)
        self.tool("agregar_al_carrito", f"{o['sku']} x{qty}: {res.status}")
        self._added.add(o["id"])
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
            current = next((it["qty"] for it in (res.cart or {}).get("items", []) if it["item_id"] == o["id"]), 0)
            more = res.available - current
            if more <= 0:
                return f"De la {o['name']} ya tenés en el carrito las {current} disponibles."
            self.state["offer"] = {"ids": [o["id"]], "qty": more}
            return (f"De la {o['name']} sólo hay {res.available} disponible(s)"
                    + (f" y ya tenés {current} en el carrito" if current else "")
                    + f". ¿Querés que te agregue {more}?")
        if res.status == "not_found":
            return "Ese producto ya no está disponible en el catálogo."
        extra = self.complement(o, res.cart) if tail else None
        return (f"Listo, agregué {qty} × {o['name']} ({_money(res.offer['price'])} c/u).\n"
                + self.cart_text(res.cart)
                + ("\nEntrega: por ahora coordinamos retiro o envío con el equipo después del pago. "
                   + (extra or "¿Querés sumar algo más o lo comprás?") if tail else ""))

    def complement(self, o: dict[str, Any], cart: Optional[dict[str, Any]]) -> Optional[str]:
        """Venta cruzada: UN complemento que el negocio cargó para este producto (columna
        `complementos`), con stock y precio vigente y que no esté ya en el carrito. Queda como
        propuesta: «sí» lo agrega. Nunca sugiere algo que el negocio no cargó, y como mucho dos
        veces por conversación (sugerir de más espanta)."""
        if self.state.get("cross_sold", 0) >= 2:
            return None
        with tenant_tx(self.tenant) as cur:
            cur.execute("select c.id from catalog_items p cross join lateral unnest(p.complements) "
                        "with ordinality as s(sku, n) join catalog_items c on c.tenant_id = p.tenant_id "
                        "and c.sku = s.sku and c.active where p.tenant_id = %s and p.id = %s order by s.n",
                        (self.tenant, o["id"]))
            ids = [str(r["id"]) for r in cur.fetchall()]
        in_cart = {it["item_id"] for it in (cart or {}).get("items", [])}
        ids = [i for i in ids if i not in in_cart]
        if not ids:
            return None
        found = {x["id"]: x for x in inventory.offers(self.tenant, ids=ids, limit=len(ids))}
        pick = next((found[i] for i in ids if i in found and found[i].get("price") is not None
                     and found[i].get("available", 0) > 0 and found[i].get("pricing_mode") != "custom_quote"), None)
        if pick is None:
            return None
        self.tool("venta_cruzada", f"{o['sku']} → {pick['sku']}")
        self.state["offer"] = {"ids": [pick["id"]], "qty": 1}
        self.state["cross_sold"] = self.state.get("cross_sold", 0) + 1
        return f"Suele llevarse con eso: {pick['name']} a {_money(pick['price'])}. ¿Te lo agrego?"

    def edit(self, op: tuple[str, int]) -> Optional[str]:
        """"Dejame dos", "sacá una", "sacá todas": un único cambio de la línea, sin vaciar y volver
        a cargar. None si fija la cantidad de algo que no está en el carrito (entonces se agrega)."""
        cart = orders.get_cart(self.tenant, self.conv)
        line, why = self.edit_line(op, cart)
        if line is None:
            if why == "absent":
                return None if op[0] == "set" else "Eso no está en tu carrito.\n" + self.cart_text(cart)
            return "¿De cuál producto? Tenés:\n" + self.cart_text(cart)
        return self.set_qty(line["item_id"], line["name"], self.edit_plan()[line["item_id"]])

    def set_qty(self, item_id: str, name: str, qty: int) -> str:
        res = orders.set_item_qty(self.tenant, self.conv, item_id, qty,
                                 policies=(self.profile.get("policies") or {}) if self.dry_run else None)
        self.tool("cambiar_cantidad", f"{name} → {qty}: {res.status}")
        if res.status == "insufficient_stock":
            return (f"De la {name} sólo hay {res.available} disponible(s); no la puedo dejar en {qty}.\n"
                    + self.cart_text(res.cart))
        if res.status == "not_in_cart":
            return f"La {name} no estaba en tu carrito.\n" + self.cart_text(res.cart)
        if res.status == "requires_human":
            self.requires_human = True
            if not self.dry_run:
                self._lead_for_human(res.offer)
            return (f"La {name} necesita confirmación de una persona para aumentar la cantidad.\n"
                    + self.cart_text(res.cart))
        if res.status != "ok":
            self.requires_human = res.status == "no_price"
            return f"No pude cambiar la {name}: ya no tiene precio vigente cargado.\n" + self.cart_text(res.cart)
        self.state["edited"] = self.state["selected"] = item_id
        head = f"Saqué la {name}." if qty == 0 else f"Listo, quedan {qty} × {name}."
        return head + "\n" + self.cart_text(res.cart)

    def _lead_only(self, cart: Optional[dict[str, Any]]) -> str:
        """El negocio apagó la venta directa: se registra el interés y cierra una persona."""
        self.requires_human = True
        self.tool("preparar_compra", "venta directa deshabilitada por el negocio")
        if cart and cart["items"]:
            opportunities.upsert_opportunity(self.tenant, OpportunityInput(
                conversation_id=self.conv, stage="para_cotizar", origin="venta_chat",
                requirements={"productos": [f"{i['qty']} × {i['name']}" for i in cart["items"]]},
                requires_human_quote=True, estimated_amount=cart["total"]))
        return ("Para cerrar la compra te contacta una persona del equipo con el detalle de lo que "
                "elegiste. ¿Querés consultar algo más mientras tanto?")

    def _below_minimum(self, total: float) -> Optional[str]:
        minimum = float((self.profile.get("policies") or {}).get("min_order_total") or 0)
        if minimum and total < minimum:
            self.tool("politica", f"compra mínima {_money(minimum)}")
            return (f"La compra mínima es de {_money(minimum)} y tu carrito suma {_money(total)}. "
                    "¿Querés sumar algo más?")
        return None

    def shipping(self, zone: str) -> str:
        """¿Se envía a esta zona? Sale de las zonas que cargó el negocio, sin inventar costos."""
        self.tool("consultar_envio", zone or "sin zona")
        zones = (self.profile.get("policies") or {}).get("delivery_zones") or []
        info = self.profile.get("shipping") or ""
        if not zones:
            return info or "Eso lo confirma una persona del equipo."
        z = normalize(zone)
        hit = next((x for x in zones if z and (normalize(x) in z or z in normalize(x))), None)
        where = ""
        if not hit and z:
            # «Bernal» no dice «Quilmes»: Georef ubica la localidad y su partido (o zona del GBA).
            hit, found = georef.match_zone(zone, zones)
            if hit:
                place = next(p for p in found if normalize(hit) in georef.names_for(p))
                where = f" ({georef.describe(place)} entra en {hit})"
                self.tool("consultar_envio", f"georef: {georef.describe(place)} → {hit}")
            elif len({(p["departamento"], p["provincia"]) for p in found}) > 1:
                options = sorted({georef.describe(p) for p in found})[:4]
                return (f"Hay varias localidades que se llaman así: {'; '.join(options)}. "
                        "¿Cuál es la tuya?")
        if hit:
            cost = ((self.profile.get("policies") or {}).get("shipping_costs") or {}).get(hit)
            # El costo es el que cargó el negocio; sin costo cargado no se inventa.
            price = f" El envío a {hit} cuesta {_money(cost)}." if cost is not None else ""
            return f"Sí, enviamos a {hit}{where}.{price}" + (f" {info}" if info else "")
        return (f"A {zone or 'esa zona'} no figura que enviemos. Las zonas de envío son: "
                f"{', '.join(zones)}. Si querés, una persona del equipo lo revisa.")

    def prepare_checkout(self, text: str) -> str:
        cart = orders.get_cart(self.tenant, self.conv)
        if not agent_profile.tool_enabled(self.profile, "preparar_compra"):
            return self._lead_only(cart)
        if not cart or not cart["items"]:
            # Con un pedido ya esperando pago, "la compro" pide ese link; no arma otro carrito.
            pending = [o for o in orders.conversation_orders(self.tenant, self.conv)
                       if o["status"] in orders.AWAITING_PAYMENT and not o["attention_reason"]]
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
                       if o["status"] in orders.AWAITING_PAYMENT]
            if pending:
                return self.pay_link(pending[0], "Ya tenés un pedido esperando el pago.")
            return "Todavía no agregaste nada al carrito. ¿Qué producto querés llevar?"
        below = self._below_minimum(cart["subtotal"])     # el mínimo es de productos: el envío no cuenta
        if below:
            return below
        # Las evaluaciones no escriben la entrega ni consultan Georef (sin efectos).
        if delivery.enabled(self.profile) and not cart.get("delivery_method") and not self.dry_run:
            return self.ask_delivery()
        self.state["pending"] = {"action": "checkout", "total": cart["total"]}
        how = delivery.describe(cart)
        text_cart = self.cart_text(cart)
        if cart.get("shipping"):        # el envío va ANTES del total (que ya lo incluye)
            text_cart = text_cart.replace("\nTotal:", f"\nEnvío: {_money(cart['shipping'])}\nTotal:", 1)
        return ("Te confirmo el pedido:\n" + text_cart
                + (f"\nEntrega: {how}" if how else "")
                + "\nAl confirmar te aparto el stock y te paso el link de pago. ¿Confirmás? (sí / no)")

    # -- entrega (envío o retiro), antes del resumen --
    def ask_delivery(self) -> str:
        o = delivery.options(self.profile)
        self.state["delivery"] = {"step": "method"}
        self.tool("entrega", "pregunta envío o retiro")
        lines = []
        if o["zones"]:
            lines.append(f"1. Envío a domicilio (zonas: {', '.join(o['zones'])})")
        if o["pickup"]:
            hours = f" · {o['hours'].rstrip('. ')}" if o["hours"] else ""
            lines.append(f"{len(lines) + 1}. Retiro en el local: {o['pickup']}{hours}")
        if len(lines) == 1:
            only = "envío" if o["zones"] else "retiro"
            self.state["delivery"] = {"step": "method", "only": only}
            return f"Antes de confirmar: {lines[0][3:]}. ¿Te sirve así?"
        return "Antes de confirmar, ¿cómo lo querés recibir?\n" + "\n".join(lines)

    def _cart_id(self) -> Optional[str]:
        cart = orders.get_cart(self.tenant, self.conv)
        return cart["id"] if cart else None

    def delivery_step(self, text: str) -> Optional[str]:
        """Responde el paso de entrega pendiente. None si el mensaje no lo contesta (sigue el agente)."""
        st, o = self.delivery_state or {}, delivery.options(self.profile)
        step = st.get("step")
        if step == "method":
            wants_pickup = bool(_RE_PICKUP.search(text)) or (
                st.get("only") == "retiro" and _RE_YES.match(text)) or (o["zones"] and re.fullmatch(r"\s*2\s*", text))
            wants_ship = bool(re.search(r"\b(envi\w*|domicilio|mand\w*|llev\w*|traig\w*)\b", text)) or (
                st.get("only") == "envío" and _RE_YES.match(text)) or bool(re.fullmatch(r"\s*1\s*", text) and o["zones"])
            if wants_pickup and o["pickup"] and not (wants_ship and o["zones"]):   # si nombra el envío, gana el envío
                cid = self._cart_id()
                if cid:
                    with tenant_tx(self.tenant) as cur:
                        delivery.apply(cur, self.tenant, cid, "pickup")
                self.tool("entrega", "retiro en el local")
                return self.prepare_checkout(text)
            if wants_ship and o["zones"]:
                self.state["delivery"] = {"step": "address"}
                return "Pasame la dirección de entrega: calle, número y localidad (ej.: Av. Mitre 1234, Avellaneda)."
            return None
        if step == "address":
            if o["pickup"] and _RE_PICKUP.search(text):          # «mejor lo retiro»: cambia a retiro
                self.delivery_state = {"step": "method", "only": "retiro"}
                return self.delivery_step("si")
            tries = st.get("tries", 0) + 1
            addr = delivery.parse_address(self.raw or text)
            if addr is None:
                if tries >= 2:
                    self.requires_human = True
                    return ("No pude ubicar esa dirección. Le paso tu pedido a una persona del equipo para que "
                            "coordine la entrega con vos por acá." + (" También podés retirarlo en el local." if o["pickup"] else ""))
                self.state["delivery"] = {"step": "address", "tries": tries}
                return "No encontré esa dirección. ¿Me la pasás con calle, número y localidad? (ej.: Av. Mitre 1234, Avellaneda)"
            zone = delivery.zone_for(addr, o["zones"])
            self.tool("entrega", f"dirección {addr['texto'] or addr['localidad']} → {zone or 'fuera de zona'}")
            if zone is None:
                if o["pickup"]:
                    self.state["delivery"] = {"step": "method", "only": "retiro"}
                    return (f"A {addr['localidad'] or addr['departamento']} no hacemos envíos (zonas: {', '.join(o['zones'])}). "
                            f"¿Lo retirás en el local? {o['pickup']}")
                self.requires_human = True
                return (f"A {addr['localidad'] or addr['departamento']} no figura que enviemos. Le paso tu consulta a una "
                        "persona del equipo para ver cómo te lo hacemos llegar.")
            cost = o["costs"].get(zone)
            courier = zone in o["courier_zones"]
            self.state["delivery"] = {"step": "contact", "address": addr, "zone": zone, "cost": cost, "courier": courier}
            price = f"El envío a {zone} cuesta {_money(cost)}." if cost is not None else f"El costo del envío a {zone} te lo confirma el equipo."
            if courier:
                price += " Va por correo" + (f" ({o['courier_eta']})" if o["courier_eta"] else "") + " y te pasamos el número de seguimiento por acá."
            return f"Perfecto: {addr['texto']}. {price} ¿A nombre de quién y un teléfono para coordinar la entrega?"
        if step == "contact":
            contact = delivery.parse_contact(self.raw or text)     # el nombre tal como lo escribe
            if contact is None:
                self.state["delivery"] = st
                return "¿Me pasás un nombre y un teléfono para coordinar la entrega? (ej.: Ana, 11 5555 4444)"
            cid = self._cart_id()
            options: list[dict[str, Any]] = []
            if cid:
                with tenant_tx(self.tenant) as cur:
                    delivery.apply(cur, self.tenant, cid, "delivery", address=st["address"], contact=contact,
                                   cost=st.get("cost"), note=None if st.get("cost") is not None else "costo de envío a coordinar")
                    # Por correo no hay franja: la entrega la maneja el correo.
                    options = [] if st.get("courier") else reparto.suggest(cur, self.tenant, st["address"], exclude_order=cid)
            self.tool("entrega", f"envío a {st['zone']}")
            if options:
                return self.ask_slot(options)
            return self.prepare_checkout(text)
        if step == "slot":
            return self.slot_step(text, st.get("options") or [])
        return None

    # -- día y franja de la entrega (con cupo; primero donde ya pasamos cerca) --
    def ask_slot(self, options: list[dict[str, Any]]) -> str:
        self.state["delivery"] = {"step": "slot", "options": options}
        self.tool("entrega", "ofrece franjas: " + ", ".join(f"{o['date']} {o['window']}" for o in options))
        lines = [f"{i}. {o['label'][:1].upper() + o['label'][1:]}" + (" (ese día ya pasamos por tu zona)" if o["near_km"] is not None else "")
                 for i, o in enumerate(options, 1)]
        return ("¿Cuándo te queda mejor recibirlo?\n" + "\n".join(lines)
                + "\nSi no te sirve ninguno, decime «otro día» y lo coordina el equipo.")

    def slot_step(self, text: str, options: list[dict[str, Any]]) -> Optional[str]:
        """Entiende «1», «la segunda», «el jueves», «mañana a la tarde»… Si no queda claro, repregunta."""
        pick = None
        m = re.fullmatch(r"\s*(?:la |el |opcion )?(\d)\s*[.!]?\s*", text)
        if m and 1 <= int(m.group(1)) <= len(options):
            pick = options[int(m.group(1)) - 1]
        elif re.search(r"\bprimer[ao]?\b", text):
            pick = options[0]
        elif re.search(r"\bsegund[ao]\b", text) and len(options) > 1:
            pick = options[1]
        else:
            window = "pm" if re.search(r"\btarde\b", text) else "am" if re.search(r"\b(temprano|a la manana|de manana)\b", text) else None
            hits = [o for o in options if any(re.search(rf"\b{re.escape(t)}\b", text) for t in reparto.day_tokens(o["date"]))
                    and (window is None or o["window"] == window)]
            if len(hits) == 1:
                pick = hits[0]
        if pick is None and re.search(r"\b(otro dia|ninguno|ninguna|no puedo|otra fecha)\b", text):
            self.tool("entrega", "otro día: a coordinar")
            return self.prepare_checkout(text)
        if pick is None:
            self.state["delivery"] = {"step": "slot", "options": options}
            return "¿Cuál te sirve? Respondé 1" + (" o 2" if len(options) > 1 else "") + ", o «otro día»."
        cid = self._cart_id()
        if cid:
            with tenant_tx(self.tenant) as cur:
                reparto.hold(cur, self.tenant, cid, pick["date"], pick["window"])
        self.tool("entrega", f"franja {pick['date']} {pick['window']}")
        return self.prepare_checkout(text)

    def confirm_checkout(self) -> str:
        pending = self.state.pop("pending", None) or {}
        cart = orders.get_cart(self.tenant, self.conv)
        # El negocio pudo apagar la venta directa después del resumen: el "sí" no la reactiva.
        if not agent_profile.tool_enabled(self.profile, "preparar_compra"):
            return self._lead_only(cart)
        # Evaluaciones: se verifica todo hasta acá, pero nunca se aparta stock ni se crea un cobro.
        if self.dry_run:
            self.tool("comprar", "simulado (evaluación): sin pedido ni link")
            below = self._below_minimum(cart["total"]) if cart else None
            return below or "[Prueba] Acá se confirmaría el pedido y se enviaría el link de pago."
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
        if res.status == "below_minimum":
            return self._below_minimum(res.shortage["total"]) or "No alcanza la compra mínima del negocio."
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
        except PaymentAccountMissing:
            # El negocio no tiene su Mercado Pago conectado: no se promete un link que no va a llegar.
            # Lo resuelve una persona (aparece en derivadas), y el pedido sigue apartado.
            self.tool("comprar", "sin cuenta de Mercado Pago conectada")
            self.requires_human = True
            return (intro + " El pago con Mercado Pago no está disponible en este momento: ya le aviso a una "
                    "persona del equipo para que te pase cómo pagar (por ejemplo, transferencia). "
                    "El stock sigue apartado.")
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
        if not agent_profile.tool_enabled(self.profile, "estado_pedido"):
            self.requires_human = True
            self.tool("estado_pedido", "deshabilitada por el negocio")
            return "El estado de tu pedido te lo confirma una persona del equipo. Ya les aviso."
        found = orders.conversation_orders(self.tenant, self.conv)
        self.tool("estado_pedido", f"{len(found)} pedido(s)")
        if not found:
            cart = orders.get_cart(self.tenant, self.conv)
            if cart and cart["items"]:
                return "Todavía no confirmaste ningún pedido. Tenés en el carrito:\n" + self.cart_text(cart)
            return "No encuentro pedidos en esta conversación."
        if len(found) > 1:
            # Varios pedidos: el estado de cada uno, sin elegir uno ni esconder una revisión humana.
            self.requires_human = any(o["attention_reason"] for o in found)
            return "Tus pedidos:\n" + "\n".join(self._order_line(o) for o in found)
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
        if o["status"] == "DEPOSIT_PAID":
            head = (f"Tu pedido #{o['number']} está señado: falta pagar el saldo de "
                    f"{_money(o['amount_due'])}.")
            return self.pay_link(o, head) if not paid_claim else head + " Apenas se acredite, te aviso por acá."
        if o["status"] == "CANCELLED":
            why = (" porque venció la reserva sin pago" if o["cancel_reason"] == "reservation_expired"
                   else "")
            return f"El pedido #{o['number']} quedó cancelado{why}. ¿Querés que lo armemos de nuevo?"
        sent = shipping.describe(o)
        if sent:
            return f"Tu pedido #{o['number']} está {o['status_label']}. {sent}."
        slot = reparto.describe_slot(o)
        if slot and o["status"] in ("PAID", "PREPARING", "DISPATCHED"):
            return f"Tu pedido #{o['number']} está {o['status_label']}. Te lo llevamos {slot}."
        tracking = ("" if o["status"] in ("PAID", "PREPARING", "REFUNDED")
                    else " Todavía no tengo número de seguimiento cargado para este envío.")
        return f"Tu pedido #{o['number']} está {o['status_label']}.{tracking}"

    @staticmethod
    def _order_line(o: dict[str, Any]) -> str:
        if o["attention_reason"] == "paid_without_stock":
            return (f"• #{o['number']}: recibimos el pago, pero el producto se agotó; una persona del "
                    "equipo te contacta para devolverte el dinero o darte una alternativa.")
        if o["attention_reason"]:
            return (f"• #{o['number']}: una persona del equipo revisa el pago; no hace falta que "
                    "pagues de nuevo.")
        return f"• #{o['number']}: {o['status_label']}."

    def thanks(self) -> str:
        """Cierre social: agradece sin reabrir la venta; el estado del pedido sale de la base."""
        self.tool("cierre", "agradecimiento")
        recent = orders.conversation_orders(self.tenant, self.conv, limit=1)
        tail = ""
        if recent:
            o = recent[0]
            tail = (f" El pedido #{o['number']} lo revisa una persona del equipo." if o["attention_reason"]
                    else f" Tu pedido #{o['number']} está {o['status_label']}.")
        return f"¡Gracias a vos!{tail} Cualquier cosa, escribime por acá."

    def offer_slots(self, cfg: dict[str, Any], text: str) -> str:
        service = booking.pick_service(cfg, text)
        if service is None:
            self.state["booking_ask"] = True
            names = ", ".join(s["name"] for s in cfg["services"])
            return f"¿Para qué es el turno? Tengo: {names}."
        with tenant_tx(self.tenant) as cur:
            slots = booking.free_slots(cur, self.tenant, cfg, service)
        self.tool("turnos", f"{service['name']}: {len(slots)} horario(s) libre(s)")
        if not slots:
            return (f"No tengo turnos libres para {service['name']} en los próximos días. Si querés, "
                    "le paso tu consulta a una persona del equipo.")
        self.state["slots"] = {"service": service["name"], "options": [s.isoformat() for s in slots]}
        lines = "\n".join(f"{i}. {booking.label(s)}" for i, s in enumerate(slots, 1))
        return (f"Turnos libres para {service['name']} ({service['minutes']} min):\n{lines}\n"
                "¿Cuál te sirve? Decime el número.")

    def book_slot(self, cfg: dict[str, Any], n: int) -> str:
        options = self.slots["options"]
        service = next((s for s in cfg["services"] if s["name"] == self.slots["service"]), None)
        if service is None or not 0 < n <= len(options):
            self.state["slots"] = self.slots
            return f"Decime un número de la lista (1 a {len(options)})."
        if self.dry_run:
            return f"(Vista previa) Reservaría {service['name']} el {booking.label(datetime.fromisoformat(options[n - 1]))}."
        with tenant_tx(self.tenant) as cur:
            appt = booking.book(cur, self.tenant, self.conv, cfg, service, datetime.fromisoformat(options[n - 1]))
        if appt.get("error"):
            self.tool("turnos", f"no se pudo reservar: {appt['error']}")
            why = ("Ese horario ya quedó muy cerca para reservarlo." if appt["error"] == "too_soon"
                   else "Ese horario se acaba de ocupar.")
            return why + " " + self.offer_slots(cfg, normalize(service["name"]))
        self.tool("turnos", f"reservado {service['name']}")
        return (f"¡Listo! Te reservé {service['name']} el {booking.label(datetime.fromisoformat(appt['starts_at']))}. "
                "Si no podés venir, avisanos por acá.")

    def reorder(self) -> Optional[str]:
        """Arma el carrito con el último pedido pagado del cliente recordado, con el precio y el
        stock de HOY (nunca los de entonces); lo que ya no se puede vender se avisa, no se agrega."""
        customer = customer_memory.customer_of(self.tenant, self.conv)
        last = orders.last_paid_items(self.tenant, customer) if customer else []
        if not last:
            return None      # sin compra pagada: responde el historial (o el resto del agente)
        self.tool("recompra", f"{len(last)} ítem(s) del último pedido")
        added, missing, cart = [], [], None
        for it in last:
            res = orders.add_item(self.tenant, self.conv, it["item_id"], it["qty"],
                                  policies=(self.profile.get("policies") or {}) if self.dry_run else None)
            if res.status == "insufficient_stock" and res.available:
                res = orders.add_item(self.tenant, self.conv, it["item_id"], res.available,
                                      policies=(self.profile.get("policies") or {}) if self.dry_run else None)
                if res.status == "ok":
                    missing.append(f"{it['name']} (había {it['qty']}, hoy hay {res.available})")
            if res.status == "ok":
                added.append(it["name"])
                cart = res.cart
            elif not (res.status == "insufficient_stock" and res.available):
                why = {"insufficient_stock": "sin stock", "requires_human": "a pedido",
                       "no_price": "sin precio vigente", "not_found": "ya no está en el catálogo"}.get(res.status, res.status)
                missing.append(f"{it['name']} ({why})")
        if not added:
            return ("Tu último pedido era: " + ", ".join(f"{i['qty']} × {i['name']}" for i in last)
                    + ". Hoy no puedo armarlo: " + "; ".join(missing) + ". ¿Buscamos alternativas?")
        head = "Te armé el carrito con tu último pedido, con los precios de hoy."
        warn = ("\nNo pude sumar todo: " + "; ".join(missing) + ".") if missing else ""
        return f"{head}\n{self.cart_text(cart)}{warn}\n¿Lo comprás o querés cambiar algo?"

    def handoff(self, again: bool = False, topic: Optional[dict[str, Any]] = None) -> str:
        """Pide una persona: queda en la bandeja del panel («derivadas») y en oportunidades. El equipo
        puede responder en este mismo chat; no hay aviso por otro medio: no se promete canal ni plazo."""
        self.requires_human = True
        # Repetir la derivación no cambia su motivo (queda el original en la conversación).
        self.asked_for_person = topic is None and not again
        self.by_topic = topic is not None
        self.state["handoff"] = True
        hours = (f" Horario de atención: {self.profile['hours'].rstrip('. ')}." if self.profile.get("hours")
                 else "")
        if again:
            self.tool("derivar_persona", "ya registrada")
            return ("Tu pedido para hablar con una persona ya está en la bandeja del equipo del negocio: pueden "
                    "responderte en este mismo chat. No tengo forma de avisarte por otro medio ni de darte un plazo."
                    + hours + " Si querés, seguí contándome qué necesitás y te ayudo con productos, precios y stock.")
        if not self.dry_run:
            req = dict(opportunities.get_conversation_requirements(self.tenant, self.conv))
            req["atencion"] = f"tema: {topic['match']}" if topic else "pidió hablar con una persona"
            cart = orders.get_cart(self.tenant, self.conv)
            opp = opportunities.upsert_opportunity(self.tenant, OpportunityInput(
                conversation_id=self.conv, stage="para_cotizar", origin="venta_chat", requirements=req,
                requires_human_quote=True, estimated_amount=cart["total"] if cart and cart["items"] else None))
            opportunities.log_activity(self.tenant, opp.id, "derivacion",
                                       f"tema configurado: «{topic['match']}»" if topic else "el cliente pidió hablar con una persona")
        self.tool("derivar_persona", f"tema «{topic['match']}»" if topic else "registrada en oportunidades")
        if topic:
            # Mensaje del negocio para este tema (o uno neutro); nunca promete plazos ni canales.
            return ((topic.get("reply") or "Eso lo atiende una persona del equipo del negocio.")
                    + " Ya le dejé tu consulta en su bandeja: pueden responderte en este mismo chat." + hours)
        return ("Listo, le dejé al equipo del negocio tu pedido de hablar con una persona: lo ven en su bandeja y "
                "pueden responderte en este mismo chat." + hours + " No puedo avisarte por otro medio ni darte un "
                "plazo. Mientras tanto, si querés, te sigo ayudando con productos, precios y stock.")

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


# Retiro en el local (sin «paso» o «local» sueltos: «te paso la dirección» es un envío).
_RE_PICKUP = re.compile(r"\b(retir\w*|lo busco|paso a buscar\w*|voy a buscar\w*|en el local|por el local)\b")
_RE_BOOKING = re.compile(r"\b(turnos?|reserv\w*|agend\w*|cita|coordinar (una )?(visita|medicion|retiro|instalacion))\b")


def _booking_reply(turn: _Turn, text: str) -> Optional[str]:
    """Turnos: pedir uno (ofrece horarios libres) o elegir uno de los ofrecidos («el 2»).
    Determinista también con IA: los horarios salen de la agenda real."""
    cfg = booking.config(turn.profile)
    if not cfg:
        return None
    if turn.slots:
        n = _option(text)
        if n is not None:
            return turn.book_slot(cfg, n)
    if _RE_BOOKING.search(text) or (turn.booking_ask and booking.pick_service(cfg, text)):
        return turn.offer_slots(cfg, text)
    return None


# «No me manden más promos», «dame de baja»: la baja de campañas aplica al toque y se confirma.
_OPT_NOUN = r"(mensajes|promos?|promociones|ofertas|publicidad|novedades|campanas|recordatorios)"
_RE_OPT_OUT = re.compile(
    r"\bno (me )?(manden|mandes|envien|envies|escriban|escribas) mas " + _OPT_NOUN + r"\b|"
    r"\bno quiero (recibir )?(mas )?" + _OPT_NOUN + r"\b|\bbasta de " + _OPT_NOUN + r"\b|"
    r"\b(dame|darme|me doy) de baja( de (la lista|(las |los )?" + _OPT_NOUN + r"))?[\s.!]*$|"
    r"\bdesuscrib\w*|\bunsubscribe\b")


def _opt_out_reply(turn: _Turn, text: str) -> Optional[str]:
    if turn.dry_run or not _RE_OPT_OUT.search(text):
        return None
    campaigns.opt_out(turn.ctx.tenant_id, turn.ctx.conversation_id)
    return ("Listo, no te vamos a mandar más promociones ni recordatorios. "
            "Si necesitás algo, escribime acá cuando quieras.")


def _reorder_reply(turn: _Turn, text: str) -> Optional[str]:
    """«Repetí mi pedido»: determinista también con IA (toca el carrito con datos reales)."""
    if (not _RE_REORDER.search(text) or _RE_STATUS_Q.search(text)
            or not agent_profile.tool_enabled(turn.profile, "preparar_compra")):
        return None
    return turn.reorder()


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


def _topic(profile: dict[str, Any], text: str) -> Optional[dict[str, Any]]:
    """Tema que el negocio quiere que atienda siempre una persona (reclamos, cambios…): palabra o
    frase completa en el mensaje normalizado."""
    for t in (profile.get("policies") or {}).get("handoff_topics") or []:
        for k in t["keywords"]:
            # Bordes por «no es letra ni número» (no \b): una palabra con signos («¿garantía?») también vale.
            if re.search(rf"(?<!\w){re.escape(normalize(k).strip('¿?¡!.,;: '))}(?!\w)", text):
                return {**t, "match": k}
    return None


def _human_reply(turn: _Turn, text: str, handoff: bool) -> Optional[str]:
    """Pedido de una persona y su seguimiento ("dale, ¿cómo me avisan?"). Determinista también con
    LLM: lo que se afirma de la derivación (registro, canal, plazo) no lo redacta el modelo."""
    topic = _topic(turn.profile, text)
    if topic:
        # Ya derivado: no vuelve a registrar ni a repetir el mensaje entero.
        return turn.handoff(again=True) if handoff else turn.handoff(topic=topic)
    if _RE_HUMAN.search(text):
        return turn.handoff()
    if handoff and (_RE_NOTIFY.search(text) or (_RE_YES.match(text) and len(text.split()) <= 6)):
        return turn.handoff(again=True)
    return None


def _rules_reply(turn: _Turn, text: str) -> str:
    """Planner determinista (modo mock): intención por reglas."""
    state, tenant_id, conv = turn.state, turn.tenant, turn.conv
    budget = _budget(text)
    cart_now = orders.get_cart(tenant_id, conv)
    edit = _edit(text) if turn.consent == "order" else None
    if _RE_DONE.match(text) and cart_now and cart_now["items"]:
        reply = turn.prepare_checkout(text)
    elif _social(text):
        reply = turn.thanks()
    elif _RE_COMPARE.search(text) and state.get("last_results") and (cmp := turn.compare(text, budget=budget)):
        reply = cmp
    elif _RE_HISTORY.search(text) and agent_profile.tool_enabled(turn.profile, "historial_cliente"):
        reply = turn.customer_history()
    elif _RE_INFO.search(text) and not _RE_ORDER_WORD.search(text):
        reply = turn.info(text)
    elif _RE_PAID_CLAIM.search(text):
        reply = turn.status(paid_claim=True)
    elif _RE_STATUS.search(text) and (_RE_ORDER_WORD.search(text) or "salio" in text or "llego" in text):
        reply = turn.status(paid_claim=False)
    elif _RE_CART.search(text) and turn.consent != "order" and not turn.no_cart:
        turn.tool("ver_carrito", "vacío" if not cart_now else f"{len(cart_now['items'])} ítem(s)")
        reply = turn.cart_text(cart_now)
    elif (turn.consent == "read" and budget is None
          and (_RE_STOCK_Q.search(text) or _RE_PRICE_Q.search(text) or re.search(r"\bhay\b", text))
          and (o := turn.resolve(text))):
        reply = turn.stock_offer(o, _qty(text))         # consultar/cotizar: no toca el carrito
    elif _RE_BUY.search(text) and turn.consent == "order":
        reply = turn.prepare_checkout(text)
    elif edit and cart_now and cart_now["items"] and (done := turn.edit(edit)):
        reply = done
    elif _RE_REMOVE.search(text) and turn.consent == "order":
        reply = "¿Cuál querés que saque?\n" + turn.cart_text(cart_now)
    elif turn.consent == "order" and (done := turn.order(text)):
        reply = done
    elif turn.consent == "pick" and (done := turn.take(text)):
        reply = done
    elif state.get("last_results") and (n := _option(text)) is not None and len(text.split()) <= 3:
        reply = turn.select(n)
    elif budget is None and _RE_STOCK_Q.search(text) and turn.state.get("last_results"):
        reply = turn.stock(text)
    elif (_RE_DOCS.search(text) and not _RE_PRODUCT_ASK.search(text)
          and not (_RE_ADD.search(text) and state.get("last_results"))
          and agent_profile.tool_enabled(turn.profile, "buscar_info_negocio")
          and (doc := turn.knowledge(text))):
        reply = doc
    else:
        reply = turn.search(text, budget)
    return reply


def _human_hold(tenant_id: str, conversation_id: str) -> SalesReply:
    """Una persona del negocio tiene la conversación: el agente no responde (bandeja)."""
    return SalesReply(reply="", conversation_id=conversation_id, mode="human", requires_human=True,
                      cart=orders.get_cart(tenant_id, conversation_id),
                      orders=orders.conversation_orders(tenant_id, conversation_id), ui={"type": "human_hold"})


def handle_sales_message(tenant_id: str, message: str, conversation_id: Optional[str] = None,
                         planner: Optional[Any] = None, profile_override: Optional[dict[str, Any]] = None,
                         channel: str = "web_sandbox") -> SalesReply:
    """Un mensaje del cliente. Con LLM configurado (o un `planner` inyectado) el modelo elige las
    herramientas; si falla o su respuesta no pasa los controles, responde el planner por reglas."""
    message = privacy.mask_cards(message)     # una tarjeta nunca se guarda ni llega a la IA
    from . import llm_sales

    conv = opportunities.ensure_conversation(tenant_id, conversation_id, channel)
    opportunities.add_message(tenant_id, conv, "inbound", message)
    state, taken = _load_state(tenant_id, conv)
    if taken and channel != "eval":
        return _human_hold(tenant_id, conv)
    turn = _Turn(ToolContext(tenant_id=tenant_id, conversation_id=conv), state)
    if profile_override is not None:      # evaluaciones: borrador del perfil sin guardarlo
        turn._profile = profile_override
    turn.dry_run = channel == "eval"      # evaluaciones: sin pedidos, stock apartado ni cobros
    text = normalize(message)
    turn.text = text
    turn.raw = message
    mode = "mock"
    # Una propuesta de agregar vale sólo para el mensaje siguiente; la derivación, para su seguimiento.
    turn.offer = state.pop("offer", None)
    turn.slots = state.pop("slots", None)      # turnos ofrecidos en el mensaje anterior
    turn.delivery_state = state.pop("delivery", None)   # envío o retiro: un paso por mensaje
    turn.booking_ask = bool(state.pop("booking_ask", None))   # preguntó «¿para qué es el turno?»
    handoff = bool(state.pop("handoff", None))
    turn.no_cart = all(_RE_NO_CART.search(part) for part in _parts(text))
    turn.consent = _consent(message, text, turn.offer)

    reply = (_opt_out_reply(turn, text) or _confirmation_reply(turn, text) or _human_reply(turn, text, handoff)
             or (turn.delivery_step(text) if turn.delivery_state else None) or _reorder_reply(turn, text)
             or _booking_reply(turn, text))
    if reply is None:
        planner = planner or llm_sales.default_planner()
        if planner is not None and limits.ai_allowed(tenant_id):
            with ai_usage.for_tenant(tenant_id, "venta"):
                reply = llm_sales.run(turn, message, conv, planner)
            mode = "live" if reply is not None and turn.model_answered else "mock"
        if reply is None:
            reply = _rules_reply(turn, text)

    if turn.requires_human:
        state.pop("offer", None)          # "dale" después de derivar no es una compra
    ui = _ui(turn)
    # Aparece en «derivadas» de la bandeja: 'asked' si pidió una persona; si no, por cotización.
    why = (None if turn.dry_run or not turn.requires_human
           else "asked" if turn.asked_for_person else "topic" if turn.by_topic else "quote")
    if not _finish_turn(tenant_id, conv, state, reply, ui, turn.profile.get("version"), why):
        return _human_hold(tenant_id, conv)
    return SalesReply(
        reply=reply, conversation_id=conv, mode=mode, requires_human=turn.requires_human,
        cart=orders.get_cart(tenant_id, conv), orders=orders.conversation_orders(tenant_id, conv),
        payment=turn.payment, products=turn.products, trace=turn.trace, ui=ui,
    )
