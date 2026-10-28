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
from ..domain import agent_profile, customer_memory, inventory, knowledge, opportunities, orders
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
        self.dry_run = False
        self.text = ""          # mensaje normalizado del turno (el comparador ve qué dato se pidió)
        self.offer: Optional[dict[str, Any]] = None   # propuesta de agregar del turno anterior
        self.consent = "read"   # ver _consent
        self.no_cart = False    # "todavía no quiero carrito": no se propone agregar
        self.blocked = False    # la última herramienta del modelo fue rechazada por el servidor
        self.model_answered = False   # el modelo respondió al menos una vez (si no, el modo es mock)
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
                                     ambiente=f["ambiente"], limit=5)
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
        return f"{i}. {o['name']}{brand} · {tail}"

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
        text = self.show(items, f"Hay {len(items)} opciones que coinciden:")
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
        query = {"keywords": f["keywords"], "color": f["color"], "ambiente": f["ambiente"]}
        last = self.state.get("last_query")
        if last and not f["keywords"] and (budget is not None or f["color"] or f["ambiente"] or drop_budget):
            # Corrección parcial ("¿y en cromo?", "hasta 150 mil", "sin límite de precio") => sobre la
            # última búsqueda, con su tope salvo que lo cambie o lo quite. Otro tipo de producto
            # arranca de cero (sin tope).
            query = {k: query[k] or last.get(k) for k in query}
            if budget is None and not drop_budget:
                budget = last.get("budget")
        if not (query["keywords"] or query["color"] or query["ambiente"]):
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
                    f"({best.get('brand') or 'sin marca'}) a {_money(best['price'])}."
                    + ("" if self.no_cart else " ¿Te la agrego?"))
        listed = self.show(found, "Tengo estas opciones:")
        if self.no_cart:
            return listed
        places = sorted({o["specs"].get("ambiente") for o in found} - {None})
        if not query["ambiente"] and len(places) > 1:
            # Falta el dato que cambia la elección: una pregunta concreta, sin descartar opciones.
            return listed + f"\n¿Es para {' o para '.join(places)}? Si alguna ya te sirve, decime el número."
        return listed + "\n¿Querés que te agregue alguna?"

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
        return (f"Listo, agregué {qty} × {o['name']} ({_money(res.offer['price'])} c/u).\n"
                + self.cart_text(res.cart)
                + ("\nEntrega: por ahora coordinamos retiro o envío con el equipo después del pago. "
                   "¿Querés sumar algo más o lo comprás?" if tail else ""))

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
        if hit:
            return f"Sí, enviamos a {hit}." + (f" {info}" if info else "")
        return (f"A {zone or 'esa zona'} no figura que enviemos. Las zonas de envío son: "
                f"{', '.join(zones)}. Si querés, una persona del equipo lo revisa.")

    def prepare_checkout(self, text: str) -> str:
        cart = orders.get_cart(self.tenant, self.conv)
        if not agent_profile.tool_enabled(self.profile, "preparar_compra"):
            return self._lead_only(cart)
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
        below = self._below_minimum(cart["total"])
        if below:
            return below
        self.state["pending"] = {"action": "checkout", "total": cart["total"]}
        return ("Te confirmo el pedido:\n" + self.cart_text(cart)
                + "\nAl confirmar te aparto el stock y te paso el link de pago. ¿Confirmás? (sí / no)")

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
        if o["status"] == "CANCELLED":
            why = (" porque venció la reserva sin pago" if o["cancel_reason"] == "reservation_expired"
                   else "")
            return f"El pedido #{o['number']} quedó cancelado{why}. ¿Querés que lo armemos de nuevo?"
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

    def handoff(self, again: bool = False) -> str:
        """Pide una persona: queda registrado en oportunidades (lo que ve el equipo en el panel).
        No hay bandeja ni aviso automático todavía: no se promete canal ni plazo."""
        self.requires_human = True
        self.state["handoff"] = True
        hours = (f" Horario de atención: {self.profile['hours'].rstrip('. ')}." if self.profile.get("hours")
                 else "")
        if again:
            self.tool("derivar_persona", "ya registrada")
            return ("Tu pedido para hablar con una persona ya quedó registrado para el equipo del negocio. "
                    "Desde este chat no tengo forma de avisarte por otro medio ni de darte un plazo."
                    + hours + " Si querés, seguí contándome qué necesitás y te ayudo con productos, precios y stock.")
        if not self.dry_run:
            req = dict(opportunities.get_conversation_requirements(self.tenant, self.conv))
            req["atencion"] = "pidió hablar con una persona"
            cart = orders.get_cart(self.tenant, self.conv)
            opp = opportunities.upsert_opportunity(self.tenant, OpportunityInput(
                conversation_id=self.conv, stage="para_cotizar", origin="venta_chat", requirements=req,
                requires_human_quote=True, estimated_amount=cart["total"] if cart and cart["items"] else None))
            opportunities.log_activity(self.tenant, opp.id, "derivacion", "el cliente pidió hablar con una persona")
        self.tool("derivar_persona", "registrada en oportunidades")
        return ("Listo, dejé registrado para el equipo del negocio que querés hablar con una persona." + hours
                + " Desde este chat no puedo avisarte por otro medio ni darte un plazo. Mientras tanto, si "
                  "querés, te sigo ayudando con productos, precios y stock.")

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


def _human_reply(turn: _Turn, text: str, handoff: bool) -> Optional[str]:
    """Pedido de una persona y su seguimiento ("dale, ¿cómo me avisan?"). Determinista también con
    LLM: lo que se afirma de la derivación (registro, canal, plazo) no lo redacta el modelo."""
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


def handle_sales_message(tenant_id: str, message: str, conversation_id: Optional[str] = None,
                         planner: Optional[Any] = None, profile_override: Optional[dict[str, Any]] = None,
                         channel: str = "web_sandbox") -> SalesReply:
    """Un mensaje del cliente. Con LLM configurado (o un `planner` inyectado) el modelo elige las
    herramientas; si falla o su respuesta no pasa los controles, responde el planner por reglas."""
    from . import llm_sales

    conv = opportunities.ensure_conversation(tenant_id, conversation_id, channel)
    opportunities.add_message(tenant_id, conv, "inbound", message)
    state = _load_state(tenant_id, conv)
    turn = _Turn(ToolContext(tenant_id=tenant_id, conversation_id=conv), state)
    if profile_override is not None:      # evaluaciones: borrador del perfil sin guardarlo
        turn._profile = profile_override
    turn.dry_run = channel == "eval"      # evaluaciones: sin pedidos, stock apartado ni cobros
    text = normalize(message)
    turn.text = text
    mode = "mock"
    # Una propuesta de agregar vale sólo para el mensaje siguiente; la derivación, para su seguimiento.
    turn.offer = state.pop("offer", None)
    handoff = bool(state.pop("handoff", None))
    turn.no_cart = all(_RE_NO_CART.search(part) for part in _parts(text))
    turn.consent = _consent(message, text, turn.offer)

    reply = _confirmation_reply(turn, text) or _human_reply(turn, text, handoff)
    if reply is None:
        planner = planner or llm_sales.default_planner()
        if planner is not None:
            reply = llm_sales.run(turn, message, conv, planner)
            mode = "live" if reply is not None and turn.model_answered else "mock"
        if reply is None:
            reply = _rules_reply(turn, text)

    if turn.requires_human:
        state.pop("offer", None)          # "dale" después de derivar no es una compra
    _save_state(tenant_id, conv, state)
    ui = _ui(turn)
    opportunities.add_message(tenant_id, conv, "outbound", reply, ui or None,
                              profile_version=turn.profile.get("version"))
    return SalesReply(
        reply=reply, conversation_id=conv, mode=mode, requires_human=turn.requires_human,
        cart=orders.get_cart(tenant_id, conv), orders=orders.conversation_orders(tenant_id, conv),
        payment=turn.payment, products=turn.products, trace=turn.trace, ui=ui,
    )
