"""Venta confiable: consentimiento, cantidades y referentes (spec 2026-10-27-venta-confiable).

Catálogo propio con las marcas del seed C (más un martillo de D), en una empresa nueva por test.
Las pruebas con planner guionado hacen que el "modelo" proponga a propósito la acción equivocada:
el servidor tiene que impedirla. No miden la naturalidad de un modelo real."""
from __future__ import annotations

import json
import re
import uuid

import pytest

from app.agent.sales_agent import handle_sales_message
from app.domain import orders

from conftest import stock_of
from test_llm_sales import Scripted, say, tool


# R1: casos de aceptación; la ejecución roja queda a cargo de root.
@pytest.mark.parametrize("planner", [None, "model"])
@pytest.mark.parametrize("negative", ["No quiero el flexible", "No quiero agregar el flexible"])
@pytest.mark.parametrize("compound", [False, True])
def test_r1_negation_preserves_only_the_positive_clause(store, planner, negative, compound):
    chat = Chat(store["tenant"])
    chat("quiero un martillo")
    chat("¿Hay flexible?")
    before = chat.lines()
    message = negative + (" y también quiero un sifón" if compound else "")
    llm = planner and Scripted(
        {"content": "", "tool_calls": [
            {"name": "agregar_al_carrito", "arguments": {"consulta": "flexible"}},
            {"name": "agregar_al_carrito", "arguments": {"consulta": "sifon"}}]},
        say("Entendido."), say("Entendido."))
    chat(message, planner=llm)
    expected = before | ({store["sifon"]: 1} if compound else {})
    assert chat.lines() == expected and _no_orders(chat)


@pytest.mark.parametrize("explicit_proposal", [False, True])
def test_r1_yes_uses_only_the_delivered_proposal_and_quantity(store, explicit_proposal):
    from app.domain.inventory import normalize

    chat = Chat(store["tenant"])
    name = next(item[2] for item in _ITEMS if item[0] == "flex")
    info = f"De la {name} hay 40 disponibles a $6.800 c/u; 3 salen $20.400."
    content = info + (" ¿Te agrego 3?" if explicit_proposal else "")
    r = chat("¿Cuánto salen tres flexibles?", planner=Scripted(
        tool("consultar_producto", consulta="flexible", cantidad=3), say(content), say(content)))
    assert chat.lines() == {} and _no_orders(chat)
    # Se admite que el servidor conserve la propuesta canónica en vez de la redacción del modelo.
    offered = "?" in r.reply and bool(re.search(r"\b(?:agreg\w*|sum\w*)\b", normalize(r.reply)))
    if offered:
        assert name in r.reply and re.search(r"\b(?:3|tres)\b", normalize(r.reply))
    if explicit_proposal:
        assert offered
    chat("sí", planner=Scripted(say("Entendido."), say("Entendido.")))
    assert chat.lines() == ({store["flex"]: 3} if offered else {})
    assert _no_orders(chat)


def test_r1_cart_tools_cannot_be_disabled_by_a_validated_profile():
    from app.domain import agent_profile

    for name in ("agregar_al_carrito", "cambiar_cantidad", "quitar_del_carrito"):
        assert name not in agent_profile.TOGGLEABLE_TOOLS
        with pytest.raises(ValueError):
            agent_profile.validate({"disabled_tools": [name]})
        assert agent_profile.tool_enabled(agent_profile.validate({"disabled_tools": []}), name)
    disabled = agent_profile.validate({"disabled_tools": ["comparar_productos"]})
    assert not agent_profile.tool_enabled(disabled, "comparar_productos")


def test_r1_disabled_comparison_cannot_be_forced_by_the_planner(store):
    from app.db import tenant_tx
    from app.domain import agent_profile

    chat = Chat(store["tenant"])
    chat("canillas monocomando negras para cocina")
    before = chat.lines()
    with tenant_tx(store["tenant"]) as cur:
        agent_profile._ensure(cur, store["tenant"], "Grifería Marcas Test")
        profile = agent_profile._update(cur, store["tenant"], agent_profile.validate(
            {"disabled_tools": ["comparar_productos"]}))
    assert not agent_profile.tool_enabled(profile, "comparar_productos")
    r = chat("¿Qué opciones hay?", planner=Scripted(
        tool("comparar_productos", opciones=[1, 2]),
        say("Lo confirma una persona del equipo.")))
    assert "$" not in r.reply and r.requires_human
    assert chat.lines() == before and _no_orders(chat)


@pytest.mark.parametrize("evaluation", [False, True])
@pytest.mark.parametrize("planner", [None, "model"])
def test_r1_human_policy_blocks_increase_but_allows_reducing_and_removing(
        store, raw_conn, evaluation, planner):
    from app.db import tenant_tx
    from app.domain import agent_profile

    chat = Chat(store["tenant"])
    chat("quiero dos flexibles")
    chat("quiero un sifón")
    before = {store["flex"]: 2, store["sifon"]: 1}
    assert chat.lines() == before
    restricted = {"human_only_categories": ["repuestos"]}
    with tenant_tx(store["tenant"]) as cur:
        agent_profile._ensure(cur, store["tenant"], "Grifería Marcas Test")
        saved = agent_profile._update(cur, store["tenant"], agent_profile.validate(
            {"policies": {} if evaluation else restricted}))
    override = saved | {"policies": restricted} if evaluation else None
    channel = "eval" if evaluation else "web_sandbox"
    llm = planner and Scripted(
        tool("cambiar_cantidad", consulta="flexible", cantidad=3),
        say("Lo confirma una persona del equipo."))
    r = handle_sales_message(
        chat.tenant, "dejame tres flexibles", chat.conv, planner=llm,
        profile_override=override, channel=channel)
    assert chat.lines() == before and r.requires_human
    assert _no_orders(chat) and stock_of(raw_conn, chat.tenant, store["flex"]) == (40, 0)
    # Un tenant ajeno no puede editar esta línea, aunque conozca conversación y producto.
    foreign = orders.set_item_qty(str(uuid.uuid4()), chat.conv, store["flex"], 4)
    assert foreign.status == "not_in_cart" and chat.lines() == before
    for message, qty in (("dejame un flexible", 1), ("sacá todos los flexibles", 0)):
        llm = planner and Scripted(
            tool("cambiar_cantidad", consulta="flexible", cantidad=qty),
            say("Entendido."), say("Entendido."))
        handle_sales_message(
            chat.tenant, message, chat.conv, planner=llm,
            profile_override=override, channel=channel)
        expected = {store["sifon"]: 1} | ({store["flex"]: qty} if qty else {})
        assert chat.lines() == expected and _no_orders(chat)
    assert agent_profile.for_agent(chat.tenant)["policies"] == saved["policies"]
    assert stock_of(raw_conn, chat.tenant, store["flex"]) == (40, 0)


def test_r1_evaluation_quantity_increase_uses_draft_instead_of_saved_policy(store, raw_conn):
    from app.db import tenant_tx
    from app.domain import agent_profile

    chat = Chat(store["tenant"])
    chat("quiero un flexible")
    with tenant_tx(store["tenant"]) as cur:
        agent_profile._ensure(cur, store["tenant"], "Grifería Marcas Test")
        saved = agent_profile._update(cur, store["tenant"], agent_profile.validate(
            {"policies": {"human_only_categories": ["repuestos"]}}))
    r = handle_sales_message(
        chat.tenant, "dejame dos flexibles", chat.conv,
        profile_override=saved | {"policies": {}}, channel="eval")
    assert chat.lines() == {store["flex"]: 2} and not r.requires_human
    assert _no_orders(chat) and stock_of(raw_conn, chat.tenant, store["flex"]) == (40, 0)
    assert agent_profile.for_agent(chat.tenant)["policies"] == saved["policies"]


@pytest.mark.parametrize("feature", ["dos llaves", "2 llaves"])
@pytest.mark.parametrize("stock, qty", [(1, 1), (5, 1), (5, 2)])
@pytest.mark.parametrize("planner", [None, "model"])
def test_r1_two_handles_is_a_feature_and_explicit_units_are_preserved(
        store, raw_conn, feature, stock, qty, planner):
    with raw_conn.cursor() as cur:
        cur.execute("update stock_levels set on_hand = %s where tenant_id = %s and item_id = %s",
                    (stock, store["tenant"], store["dos_ll"]))
    raw_conn.commit()
    chat = Chat(store["tenant"])
    chat("busco canilla de cocina dos llaves negra")
    units = "dos unidades de " if qty == 2 else ""
    llm = planner and Scripted(
        tool("agregar_al_carrito", consulta="canilla de cocina dos llaves negra", cantidad=9),
        say("Entendido."), say("Entendido."))
    chat(f"dame {units}la canilla de {feature}", planner=llm)
    assert chat.lines() == {store["dos_ll"]: qty} and _no_orders(chat)
    assert stock_of(raw_conn, store["tenant"], store["dos_ll"]) == (stock, 0)


def test_r1_omitted_option_keeps_text_cards_and_next_selection_synchronized(store):
    chat = Chat(store["tenant"])
    first = chat("canillas negras para cocina")
    expected_ids = [o["id"] for o in first.products]
    assert len(expected_ids) == 3
    # Reutiliza las líneas que produjo el renderer real, omitiendo sólo la tercera.
    lines = [line for line in first.reply.splitlines() if re.match(r"^\d+\.\s", line)]
    assert len(lines) == 3
    subset = say("\n".join(lines[:2]))
    r = chat("canillas negras para cocina", planner=Scripted(
        tool("buscar_productos", consulta="canillas negras para cocina"), subset, subset))
    cards = r.ui.get("products") or []
    listed = re.findall(r"(?m)^(\d+)\.\s+([^\n]+)", r.reply)
    assert [o["id"] for o in r.products] == expected_ids
    assert [card["name"] for card in cards] == [o["name"] for o in r.products]
    assert [int(n) for n, _ in listed] == [card["n"] for card in cards]
    assert all(text.startswith(card["name"]) for (_, text), card in zip(listed, cards))
    assert chat.lines() == {} and _no_orders(chat)
    chat("la 3", planner=Scripted(say("Entendido."), say("Entendido.")))
    assert chat.lines() == {expected_ids[2]: 1} and _no_orders(chat)


_ITEMS = [
    # clave, sku, nombre, categoría, modo, specs, marca, precio, stock
    ("mono_aq", "G-COC-MONO-NEG-AQ", "Canilla de cocina monocomando negra mate", "griferia", "fixed",
     {"ambiente": "cocina", "tipo": "monocomando", "color": "negro", "acabado": "negro mate"}, "Aquaflux (DEMO)", 89900, 6),
    ("mono_hl", "G-COC-MONO-NEG-HL", "Canilla de cocina monocomando negra con pico extraíble", "griferia", "fixed",
     {"ambiente": "cocina", "tipo": "monocomando", "color": "negro", "acabado": "negro mate"}, "Hidrolar (DEMO)", 129000, 3),
    ("dos_ll", "G-COC-2LL-NEG-AQ", "Canilla de cocina dos llaves negra", "griferia", "fixed",
     {"ambiente": "cocina", "tipo": "dos llaves", "color": "negro", "acabado": "negro mate"}, "Aquaflux (DEMO)", 74500, 1),
    ("mono_cro", "G-COC-MONO-CRO-HL", "Canilla de cocina monocomando cromo", "griferia", "fixed",
     {"ambiente": "cocina", "tipo": "monocomando", "color": "cromo"}, "Hidrolar (DEMO)", 68000, 10),
    ("lav_neg", "G-BAN-LAV-NEG-AQ", "Canilla de lavatorio monocomando negra", "griferia", "fixed",
     {"ambiente": "baño", "tipo": "monocomando", "color": "negro", "acabado": "negro mate"}, "Aquaflux (DEMO)", 59900, 0),
    ("lav_cro", "G-BAN-LAV-CRO-HL", "Canilla de lavatorio monocomando cromo", "griferia", "fixed",
     {"ambiente": "baño", "tipo": "monocomando", "color": "cromo"}, "Hidrolar (DEMO)", 52000, 8),
    ("ducha", "D-TEL-NEG-AQ", "Ducha teléfono negra con flexible 1,5 m", "duchas", "fixed",
     {"ambiente": "baño", "color": "negro"}, "Aquaflux (DEMO)", 34500, 5),
    ("flex", "FLEX-AGUA-40", "Flexible de conexión de agua 40 cm (par)", "repuestos", "fixed",
     {"medida": "40 cm", "rosca": "1/2"}, "Hidrolar (DEMO)", 6800, 40),
    ("sifon", "SIF-PVC-BACHA", "Sifón de PVC para bacha", "repuestos", "fixed",
     {"material": "PVC"}, "Hidrolar (DEMO)", 9200, 15),
    ("inod", "INOD-LARGO-BLA", "Inodoro largo blanco (a pedido)", "sanitarios", "custom_quote",
     {"color": "blanco", "ambiente": "baño"}, "Aquaflux (DEMO)", None, None),
    ("martillo", "FER-MART-500", "Martillo carpintero 500 g", "herramientas", "fixed",
     {"peso": "500 g"}, "Forjax (DEMO)", 18500, 12),
]


@pytest.fixture
def store(raw_conn):
    tid = str(uuid.uuid4())
    ids: dict[str, str] = {"tenant": tid}
    with raw_conn.cursor() as cur:
        cur.execute("insert into tenants (id, name) values (%s, 'Grifería Marcas Test (SINTÉTICA)')", (tid,))
        for key, sku, name, cat, mode, specs, brand, price, stock in _ITEMS:
            cur.execute(
                "insert into catalog_items (tenant_id, sku, name, category, pricing_mode, specs_json, brand) "
                "values (%s, %s, %s, %s, %s, %s::jsonb, %s) returning id",
                (tid, sku, name, cat, mode, json.dumps(specs), brand))
            ids[key] = str(cur.fetchone()["id"])
            if price is not None:
                cur.execute("insert into price_entries (tenant_id, item_id, amount, valid_from) "
                            "values (%s, %s, %s, date '2026-01-01')", (tid, ids[key], price))
            if stock is not None:
                cur.execute("insert into stock_levels (tenant_id, item_id, on_hand) values (%s, %s, %s)",
                            (tid, ids[key], stock))
    raw_conn.commit()
    yield ids
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        cur.execute("delete from tenants where id = %s", (tid,))
    raw_conn.commit()


class Chat:
    def __init__(self, tenant):
        self.tenant, self.conv, self.last = tenant, None, None

    def __call__(self, message, planner=None):
        self.last = handle_sales_message(self.tenant, message, self.conv, planner=planner)
        self.conv = self.last.conversation_id
        return self.last

    def lines(self):
        cart = orders.get_cart(self.tenant, self.conv)
        return {it["item_id"]: it["qty"] for it in cart["items"]} if cart else {}


def _no_orders(chat):
    return orders.conversation_orders(chat.tenant, chat.conv) == []


# --- Consultar no cambia el carrito ----------------------------------------------------------
def test_dale_after_asking_for_a_person_does_not_touch_the_cart(store, raw_conn):
    chat = Chat(store["tenant"])
    chat("canillas negras para cocina")
    r = chat("Por favor, pasame con una persona")
    assert r.requires_human and r.products == [] and chat.lines() == {}
    with raw_conn.cursor() as cur:
        cur.execute("select stage, requires_human_quote from opportunities where tenant_id = %s "
                    "and conversation_id = %s", (store["tenant"], chat.conv))
        opp = cur.fetchone()
    raw_conn.commit()
    assert opp and opp["requires_human_quote"]                      # registro existente del CRM
    r = chat("dale, ¿cómo me avisan?")
    low = r.reply.lower()
    assert chat.lines() == {} and _no_orders(chat) and r.products == []
    assert "persona" in low and "whatsapp" not in low and "te avisamos" not in low and "$" not in r.reply


def test_dale_after_handoff_with_a_model_that_wants_to_add(store):
    chat = Chat(store["tenant"])
    chat("canillas negras para cocina")
    chat("Por favor, pasame con una persona")
    llm = Scripted(tool("agregar_al_carrito", opcion=1), say("Listo, te agregué la canilla."),
                   say("Listo, te agregué la canilla."))
    for text in ("dale", "dale, ¿cómo me avisan?"):
        chat(text, planner=llm)
        assert chat.lines() == {} and _no_orders(chat)


@pytest.mark.parametrize("planner", [None, "model"])
def test_negated_availability_question_neither_adds_nor_prepares_a_purchase(store, planner):
    chat = Chat(store["tenant"])
    chat("busco martillo")
    llm = planner and Scripted(tool("agregar_al_carrito", consulta="martillo", cantidad=2),
                               tool("preparar_compra"), say("Te agregué dos. ¿Confirmás?"),
                               say("Te agregué dos. ¿Confirmás?"))
    r = chat("No quiero armar carrito todavía. ¿Hay dos disponibles para comprar hoy?", planner=llm)
    assert chat.lines() == {} and _no_orders(chat)
    assert "Confirmás" not in r.reply and not (r.ui.get("quick_replies") or [])
    if planner is None:
        assert "12 disponibles" in r.reply and "$37.000" in r.reply
        chat("canillas negras para cocina")
        r = chat("Todavía no quiero agregar nada. ¿Hay dos de la 2 para hoy?")
        assert chat.lines() == {} and "disponibles" in r.reply and "$179.800" in r.reply


# --- Cantidades ---------------------------------------------------------------------------
def test_set_subtract_and_remove_units_without_touching_other_lines(store, raw_conn):
    chat = Chat(store["tenant"])
    chat("busco canilla monocomando negra mate")
    chat("agregame 3 de la aquaflux")
    chat("sumame un flexible")
    assert chat.lines() == {store["mono_aq"]: 3, store["flex"]: 1}
    r = chat("dejame dos nomás, ¿cuánto queda?")
    assert chat.lines() == {store["mono_aq"]: 2, store["flex"]: 1}
    assert "vacío" not in r.reply and "Total: $186.600" in r.reply
    chat("sacá una")
    assert chat.lines() == {store["mono_aq"]: 1, store["flex"]: 1}
    chat("sacá todas las canillas")
    assert chat.lines() == {store["flex"]: 1}
    assert stock_of(raw_conn, store["tenant"], store["mono_aq"]) == (6, 0)


def test_ambiguous_quantity_change_asks_without_mutating(store):
    chat = Chat(store["tenant"])
    chat("busco flexible de 40 cm")
    chat("agregame 2")
    chat("busco sifón")
    chat("agregame 2")
    before = chat.lines()
    r = chat("sacá una")
    assert chat.lines() == before and "?" in r.reply


def test_quantity_change_with_a_model_that_removes_and_readds(store):
    chat = Chat(store["tenant"])
    chat("busco flexible de 40 cm")
    chat("agregame 3")
    llm = Scripted({"content": "", "tool_calls": [
                       {"name": "quitar_del_carrito", "arguments": {"consulta": "flexible"}},
                       {"name": "agregar_al_carrito", "arguments": {"consulta": "flexible", "cantidad": 3}}]},
                   say("Listo."))
    r = chat("dejame dos", planner=llm)
    assert chat.lines() == {store["flex"]: 2} and "vacío" not in r.reply
    twice = Scripted({"content": "", "tool_calls": [
                         {"name": "cambiar_cantidad", "arguments": {"consulta": "flexible", "cantidad": 1}},
                         {"name": "quitar_del_carrito", "arguments": {"consulta": "flexible"}},
                         {"name": "agregar_al_carrito", "arguments": {"consulta": "sifon"}}]},
                     say("Listo."))
    chat("sacá una", planner=twice)               # resta una sola vez y no agrega otra cosa
    assert chat.lines() == {store["flex"]: 1}


def test_measures_and_prices_are_not_quantities(store):
    chat = Chat(store["tenant"])
    chat("quiero un martillo carpintero de 500 g, uno solo, por $18.500")
    assert chat.lines() == {store["martillo"]: 1}
    chat2 = Chat(store["tenant"])
    chat2("busco flexible")
    chat2("agregame el de 40 cm")
    assert chat2.lines() == {store["flex"]: 1}


@pytest.mark.parametrize("planner", [None, "model"])
def test_quoting_quantities_is_a_read_and_an_explicit_add_then_sums(store, planner):
    chat = Chat(store["tenant"])
    llm = planner and Scripted(tool("agregar_al_carrito", consulta="martillo", cantidad=2),
                               tool("consultar_producto", consulta="martillo", cantidad=2),
                               say("Dos martillos salen $37.000."))
    r = chat("¿cuánto saldrían dos martillos carpinteros?", planner=llm)
    assert "$37.000" in r.reply and chat.lines() == {} and _no_orders(chat)
    chat("agregame dos")
    assert chat.lines() == {store["martillo"]: 2}
    r = chat("sumame uno más y decime el total")
    assert chat.lines() == {store["martillo"]: 3} and "Total: $55.500" in r.reply


# --- Referentes y recorrido del usuario -------------------------------------------------------
def test_user_journey_rules(store):
    chat = Chat(store["tenant"])
    r = chat("¿Qué productos tenés?")
    assert "repuestos" in r.reply.lower() and "griferia" in r.reply.lower().replace("í", "i")
    chat("repuestos")
    r = chat("bien quiero un flexible y tambien quiero alguna canilla nueva negra o moderna")
    assert chat.lines() == {store["flex"]: 1}
    assert r.products and all("Canilla" in p["name"] for p in r.products)
    r = chat("quiero una monocomando negra mate")
    assert chat.lines() == {store["flex"]: 1}                          # dos coinciden: pregunta
    assert [p["n"] for p in r.ui["products"]] == [1, 2]
    for card in r.ui["products"]:                                       # texto y tarjetas, misma numeración
        assert f"{card['n']}. {card['name']}" in r.reply
    chat("si la aquaflux")
    assert chat.lines() == {store["flex"]: 1, store["mono_aq"]: 1}
    r = chat("la nro3")
    assert chat.lines() == {store["flex"]: 1, store["mono_aq"]: 1} and "3" in r.reply
    assert orders.get_cart(store["tenant"], chat.conv)["total"] == 96700 and _no_orders(chat)


@pytest.mark.parametrize("pick", ["la nro3", "la nro 3", "nro. 3", "la numero 3", "la 3"])
def test_option_three_of_a_real_list_selects_exactly_that_item(store, pick):
    chat = Chat(store["tenant"])
    r = chat("canillas negras")
    third = r.products[2]
    chat(pick)
    cart = orders.get_cart(store["tenant"], chat.conv)
    assert [(it["name"], it["qty"]) for it in cart["items"]] == [(third["name"], 1)]


def test_quantity_survives_the_which_one_question(store):
    chat = Chat(store["tenant"])
    chat("busco canilla monocomando negra mate")
    r = chat("quiero tres de esa canilla")
    assert chat.lines() == {} and "¿Cuál" in r.reply
    chat("la 1")
    assert chat.lines() == {store["mono_aq"]: 3}


def test_brand_that_leaves_several_options_asks(store):
    chat = Chat(store["tenant"])
    chat("canillas negras")                        # varias Aquaflux en la lista
    r = chat("sí, la aquaflux")
    assert chat.lines() == {} and "?" in r.reply


def test_short_selection_without_an_add_proposal_focuses_and_asks(store):
    chat = Chat(store["tenant"])
    chat("canillas negras para cocina")
    chat("agregame la primera")
    before = chat.lines()
    r = chat("la 2")                               # el último turno no proponía agregar
    assert chat.lines() == before and "?" in r.reply
    chat("sí")
    assert len(chat.lines()) == 2


def test_model_cannot_add_an_explored_product_in_a_compound_request(store):
    chat = Chat(store["tenant"])
    chat("repuestos")
    llm = Scripted({"content": "", "tool_calls": [
                       {"name": "agregar_al_carrito", "arguments": {"consulta": "flexible"}},
                       {"name": "agregar_al_carrito", "arguments": {"consulta": "canilla de cocina dos llaves negra"}},
                       {"name": "buscar_productos", "arguments": {"consulta": "canilla negra"}}]},
                   say("Listo."))
    chat("bien quiero un flexible y tambien quiero alguna canilla nueva negra o moderna", planner=llm)
    assert chat.lines() == {store["flex"]: 1}


def test_explicit_order_is_kept_even_if_the_model_only_searches(store):
    # Corrida live v1: el modelo buscó canillas primero y el flexible pedido se perdió.
    chat = Chat(store["tenant"])
    chat("repuestos")
    llm = Scripted(tool("buscar_productos", consulta="canilla negra"), tool("agregar_al_carrito", opcion=1),
                   say("Te sumé el flexible (total $6.800). Para la canilla mirá estas opciones."))
    r = chat("bien quiero un flexible y tambien quiero alguna canilla nueva negra o moderna", planner=llm)
    assert chat.lines() == {store["flex"]: 1} and r.mode == "live"
    assert all("Canilla" in p["name"] for p in r.products)


def test_model_cannot_cite_an_option_outside_the_last_list(store):
    # Corrida live v1: «la nro3» respondido con la lista de 4 de dos turnos antes.
    chat = Chat(store["tenant"])
    chat("canillas negras")
    chat("quiero una monocomando negra mate")                       # lista vigente: 2 opciones
    stale = say("La canilla número 3 (la de lavatorio) está sin stock.")
    r = chat("la nro3", planner=Scripted(stale, stale))
    assert "lavatorio" not in r.reply and "3" in r.reply and chat.lines() == {}


def test_unclear_choice_is_registered_even_if_the_model_asks_in_prose(store):
    # Corrida live v2: «¿la 1 o la 2?» en prosa sin herramienta; el «si la aquaflux» siguiente no entró.
    chat = Chat(store["tenant"])
    chat("canillas negras")
    prose = say("Decime con cuál quedás: la 1 (Aquaflux) o la 2 (Hidrolar).")
    r = chat("quiero una monocomando negra mate", planner=Scripted(prose, prose))
    assert [c["n"] for c in r.ui["products"]] == [1, 2] and chat.lines() == {}
    chat("si la aquaflux", planner=Scripted(say("Listo, va la Aquaflux: total $89.900.")))
    assert chat.lines() == {store["mono_aq"]: 1}


def test_mode_is_mock_when_the_model_never_answered(store):
    chat = Chat(store["tenant"])
    chat("busco flexible de 40 cm")
    r = chat("agregame 2", planner=Scripted(RuntimeError("modelo caído")))
    assert r.mode == "mock" and chat.lines() == {store["flex"]: 2}


def test_model_insisting_on_refused_actions_stops_early(store):
    chat = Chat(store["tenant"])
    chat("canillas negras para cocina")
    insist = tool("agregar_al_carrito", opcion=1)
    llm = Scripted(insist, insist, insist, insist, insist, say("x"), say("x"))
    chat("¿la 1 tiene garantía?", planner=llm)
    assert chat.lines() == {} and len(llm.calls) == 2


def test_model_cannot_pick_another_brand_than_the_one_chosen(store):
    chat = Chat(store["tenant"])
    chat("quiero una monocomando negra mate")
    llm = Scripted(tool("agregar_al_carrito", opcion=2), say("Listo, agregada."), say("Listo, agregada."))
    chat("si la aquaflux", planner=llm)
    assert store["mono_hl"] not in chat.lines()


def test_model_text_cannot_renumber_options(store):
    chat = Chat(store["tenant"])
    chat("canillas negras para cocina")
    renumbered = say("Te quedan dos: 1. Canilla de cocina monocomando negra mate — $89.900 "
                     "2. Canilla de cocina monocomando negra con pico extraíble — $129.000")
    r = chat("quiero una monocomando negra mate", planner=Scripted(renumbered, renumbered))
    numbers = re.findall(r"(\d)\. ([^\n—·]+)", r.reply)
    listed = {o["n"]: o["name"] for o in r.ui.get("products") or []}
    shown = {int(n): name.strip() for n, name in numbers}
    assert all(listed.get(n) == name for n, name in shown.items())


# --- Persona y cierre ------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["gracias igual", "chau", "bueno gracias, después veo"])
def test_goodbye_does_not_search_nor_hand_off(store, text):
    chat = Chat(store["tenant"])
    chat("busco flexible")
    r = chat(text)
    assert not r.requires_human and r.products == []
    assert all(t["name"] != "buscar_productos" for t in r.trace)


# --- Guías comerciales en el planner -------------------------------------------------------------
def test_sales_guides_reach_the_live_planner_without_disabled_tools(store):
    from app.agent import sales_skills
    from app.db import tenant_tx
    from app.domain import agent_profile
    with tenant_tx(store["tenant"]) as cur:
        agent_profile._ensure(cur, store["tenant"], "Grifería Marcas Test")
        agent_profile._update(cur, store["tenant"], agent_profile.validate({"disabled_tools": ["comparar_productos"]}))
    llm = Scripted(say("¿Qué estás buscando?"))
    handle_sales_message(store["tenant"], "hola", planner=llm)
    system = llm.calls[0][0]["content"]
    for name in ("asesorar_catalogo", "gestionar_carrito", "cerrar_o_derivar"):
        assert name in system
    assert "comparar_productos" not in system
    from app.agent.llm_sales import _TOOLS
    assert len(sales_skills.render(t["name"] for t in _TOOLS).split()) <= 600
