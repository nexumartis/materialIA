"""Conversación coherente con el estado real (planner guionado; DB local requerida).

El "modelo" guionado contradice a propósito pedidos, catálogo o capacidades: el servidor tiene que
corregirlo con un respaldo pertinente, sin repetir herramientas ni mutaciones. Estas pruebas no
miden la naturalidad de un modelo real; verifican estado, datos y efectos."""
from __future__ import annotations

import json

import pytest

from app.agent.sales_agent import handle_sales_message
from app.domain import orders
from app.payments import service
from app.payments.providers import SimulatedProvider

from conftest import stock_of
from test_llm_sales import Scripted, say, tool


def _buy(tenant, product="flexible 40 cm", conv=None):
    """Compra por reglas hasta el link de pago. Devuelve (conversación, pedido)."""
    conv = handle_sales_message(tenant, f"busco {product}", conv).conversation_id
    handle_sales_message(tenant, "agregame la primera", conv)
    handle_sales_message(tenant, "la compro", conv)
    r = handle_sales_message(tenant, "sí", conv)
    assert r.payment, r.reply
    return conv, r.orders[0]


def _pay(order):
    pref = order["payment"]["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"


def _profile(conn, tenant, **fields):
    with conn.cursor() as cur:
        cur.execute("insert into agent_profiles (tenant_id, public_slug, faq, rules, shipping, hours, "
                    "payment_methods) values (%s, %s, '[]'::jsonb, %s::jsonb, %s, '', %s)",
                    (tenant, f"test-{tenant[:8]}", json.dumps(fields.get("rules", [])),
                     fields.get("shipping", ""), fields.get("payment_methods", "")))
    conn.commit()


def _searched(tenant):
    r = handle_sales_message(tenant, "canillas negras para cocina",
                             planner=Scripted(tool("buscar_productos", consulta="canilla negra cocina"),
                                              say("Mirá estas opciones.")))
    return r.conversation_id


# --- Caso del video: pedido PAGADO + "gracias" -------------------------------------------
def test_paid_order_thanks_does_not_ask_to_pay_again_nor_promise_channels(shop):
    conv, order = _buy(shop["tenant"])
    _pay(order)
    bad = say(f"¡Gracias a vos! Para completar tu compra tenés que pagar el pedido #{order['number']}. "
              "¿Querés que te mande el link por email o por WhatsApp?")
    llm = Scripted(bad, bad)                      # insiste también al reescribir
    r = handle_sales_message(shop["tenant"], "gracias!", conv, planner=llm)
    low = r.reply.lower()
    assert "pagar" not in low and "whatsapp" not in low and "email" not in low and "http" not in low
    assert "gracias" in low and "?" not in r.reply           # cierre social, sin reabrir la venta
    assert f"#{order['number']}" in r.reply and "pagado" in low
    assert r.products == [] and r.payment is None and len(llm.calls) == 2
    assert orders.conversation_orders(shop["tenant"], conv)[0]["status"] == "PAID"


def test_paid_order_reply_with_legit_negation_is_kept(shop):
    conv, order = _buy(shop["tenant"])
    _pay(order)
    good = (f"¡Gracias a vos por la compra! El pedido #{order['number']} ya está pagado, "
            "no tenés que pagar nada más.")
    r = handle_sales_message(shop["tenant"], "gracias", conv, planner=Scripted(say(good)))
    assert r.mode == "live" and r.reply == good


def test_model_down_on_thanks_closes_socially_without_searching(shop):
    conv, order = _buy(shop["tenant"])
    _pay(order)
    r = handle_sales_message(shop["tenant"], "muchas gracias!", conv, planner=Scripted(RuntimeError("caído")))
    assert r.mode == "mock" and "gracias" in r.reply.lower() and "?" not in r.reply
    assert r.products == [] and "pagado" in r.reply
    assert not any(t["name"] == "buscar_productos" for t in r.trace)


# --- Pago pendiente: "ya pagué" no lo convierte en pagado ---------------------------------
@pytest.mark.parametrize("text,kept", [
    ("¡Listo! Tu pago está acreditado y el pedido #{n} ya está pagado.", False),
    ("No te preocupes, el pedido #{n} ya está pagado.", False),          # negación de otra frase
    ("Todavía no veo acreditado el pago del pedido #{n}; apenas entre, te aviso por acá.", True),
])
def test_pending_order_paid_claim_follows_provider_state(shop, text, kept):
    conv, order = _buy(shop["tenant"])
    reply = text.format(n=order["number"])
    llm = Scripted(tool("estado_pedido", cliente_dice_que_pago=True), say(reply), say(reply))
    r = handle_sales_message(shop["tenant"], "ya pagué", conv, planner=llm)
    assert (r.reply == reply) is kept
    if not kept:
        assert "no veo acreditado" in r.reply and len(llm.calls) == 3
    assert orders.conversation_orders(shop["tenant"], conv)[0]["status"] == "PENDING_PAYMENT"


def test_pending_order_may_be_asked_to_pay(shop):
    conv, order = _buy(shop["tenant"])
    good = f"Tu pedido #{order['number']} está esperando el pago: podés pagar con el link de arriba."
    r = handle_sales_message(shop["tenant"], "¿y ahora qué hago?", conv, planner=Scripted(say(good)))
    assert r.reply == good


# --- Varios pedidos y revisión humana ------------------------------------------------------
def test_several_orders_status_does_not_hide_human_review(shop, raw_conn):
    conv, first = _buy(shop["tenant"])
    with raw_conn.cursor() as cur:
        cur.execute("update orders set attention_reason = 'amount_mismatch' where id = %s", (first["id"],))
    raw_conn.commit()
    conv, second = _buy(shop["tenant"], "canilla de lavatorio cromo", conv)
    _pay(second)
    bad = say(f"Tu pedido #{first['number']} ya está pagado y te paso el link para pagar el #{second['number']}.")
    llm = Scripted(tool("estado_pedido"), bad, bad)
    r = handle_sales_message(shop["tenant"], "¿cómo van mis pedidos?", conv, planner=llm)
    assert r.requires_human
    assert f"#{first['number']}" in r.reply and f"#{second['number']}" in r.reply
    assert "una persona" in r.reply and "http" not in r.reply


def test_order_status_must_match_the_order_it_names(shop, raw_conn):
    conv, first = _buy(shop["tenant"])
    _pay(first)
    conv, second = _buy(shop["tenant"], "canilla de lavatorio cromo", conv)
    swapped = say(f"El pedido #{second['number']} está pagado y el #{first['number']} espera el pago.")
    right = say(f"El pedido #{first['number']} está pagado y el #{second['number']} está esperando el pago.")
    r = handle_sales_message(shop["tenant"], "¿cómo van?", conv, planner=Scripted(swapped, right))
    assert r.reply == right["content"]


# --- Capacidades: canales, descuentos, plazos ----------------------------------------------
def test_channel_promise_without_tool_is_rejected_unless_business_informs_it(shop, raw_conn):
    bad = say("Dale, te mando un WhatsApp cuando vuelva a entrar.")
    r = handle_sales_message(shop["tenant"], "¿me avisás cuando entre la canilla de lavatorio negra?",
                             planner=Scripted(bad, bad))
    assert "whatsapp" not in r.reply.lower() and r.requires_human     # respaldo: lo ve una persona

    _profile(raw_conn, shop["tenant"], payment_methods="Transferencia. Consultas por WhatsApp al local.")
    ok = "Podés consultarlo por WhatsApp al local, como figura en los datos del negocio."
    r = handle_sales_message(shop["tenant"], "¿tienen whatsapp?", planner=Scripted(say(ok)))
    assert r.reply == ok


def test_discount_needs_an_approved_business_rule(shop, raw_conn):
    conv = _searched(shop["tenant"])
    bad = say("Te hago un 15% de descuento si la llevás hoy.")
    r = handle_sales_message(shop["tenant"], "¿me hacés precio?", conv, planner=Scripted(bad, bad))
    assert "%" not in r.reply and "descuento" not in r.reply.lower()

    _profile(raw_conn, shop["tenant"], rules=["10% de descuento pagando por transferencia"])
    ok = "Pagando por transferencia tenés 10% de descuento."
    r = handle_sales_message(shop["tenant"], "¿me hacés precio?", conv, planner=Scripted(say(ok)))
    assert r.reply == ok
    neg = "No puedo hacer descuentos por mi cuenta, pero te paso las opciones con su precio real."
    r = handle_sales_message(shop["tenant"], "¿y un 20%?", conv, planner=Scripted(say(neg)))
    assert r.reply == neg


def test_smoke_findings_free_shipping_and_notify_offer_are_rejected(shop, raw_conn):
    # Respuestas reales de qwen3:8b en el smoke: «gratis» y «¿te aviso?» no constan en el perfil.
    _profile(raw_conn, shop["tenant"], shipping="Envíos en CABA y GBA; costo y plazo los confirma el equipo.")
    bad = say("El envío a Córdoba no está incluido en los envíos gratis de CABA y GBA. El costo y plazo "
              "lo confirma el equipo. ¿Querés que te avise cuando tengan la info?")
    r = handle_sales_message(shop["tenant"], "y me llega mañana a Córdoba?", planner=Scripted(bad, bad))
    assert "gratis" not in r.reply and "avise" not in r.reply
    assert "costo y plazo los confirma el equipo" in r.reply      # respaldo: lo que informa el negocio
    ok = "A Córdoba no figura en los envíos; el costo y plazo lo confirma el equipo."
    r = handle_sales_message(shop["tenant"], "y a Córdoba?", planner=Scripted(say(ok)))
    assert r.reply == ok and r.requires_human                     # derivó a una persona: queda marcado
    run2 = "Después de confirmar el pago, el equipo te avisa el plazo y costo exactos."
    r = handle_sales_message(shop["tenant"], "¿y el plazo?", planner=Scripted(say(run2)))
    assert r.reply == run2 and r.requires_human


def test_unknown_delivery_time_is_not_promised(shop):
    bad = say("Sí, te llega mañana sin cargo.")
    r = handle_sales_message(shop["tenant"], "¿me llega mañana?", planner=Scripted(bad, bad))
    assert "mañana" not in r.reply and r.requires_human        # lo confirma una persona


# --- Catálogo: precio y stock asociados al producto correcto --------------------------------
def test_price_and_stock_must_belong_to_the_named_product(shop):
    conv = _searched(shop["tenant"])
    swapped = say("La negra mate sale $129.000 y la de pico extraíble $89.900.")
    stock = say("De la de pico extraíble hay 6 disponibles.")
    right = say("La negra mate sale $89.900 y la de pico extraíble $129.000: la segunda trae pico "
                "extraíble, por eso cuesta más.")
    r = handle_sales_message(shop["tenant"], "¿cuánto salen la negra mate y la de pico?", conv,
                             planner=Scripted(tool("consultar_producto", opcion=3), swapped, right))
    assert r.reply == right["content"]
    r = handle_sales_message(shop["tenant"], "¿y de la de pico cuántas quedan?", conv,
                             planner=Scripted(tool("consultar_producto", opcion=3), stock, stock))
    assert "6 disponibles" not in r.reply and "3 disponibles" in r.reply


def test_model_sees_product_specs_and_current_preferences(shop):
    conv = _searched(shop["tenant"])
    llm = Scripted(say("¿Para qué uso la querés?"))
    handle_sales_message(shop["tenant"], "¿cuál me conviene?", conv, planner=llm)
    system = llm.calls[0][0]["content"]
    assert "dos llaves" in system and "monocomando" in system   # ficha para comparar
    assert "negro" in system and "cocina" in system              # preferencias vigentes


# --- Carrito natural, reintento sin repetir mutaciones -------------------------------------
def test_cart_reply_may_be_natural_when_it_shows_the_real_total(shop):
    conv = _searched(shop["tenant"])
    natural = say("¡Buenísimo! Te sumé la negra mate; vas $89.900 en total. ¿Algo más o cerramos?")
    r = handle_sales_message(shop["tenant"], "dale la negra mate", conv,     # opción 2 (orden por precio)
                             planner=Scripted(tool("agregar_al_carrito", opcion=2), natural))
    assert r.reply == natural["content"] and r.cart["total"] == 89900


def test_rewrite_never_reexecutes_tools(shop, raw_conn):
    conv = _searched(shop["tenant"])
    retry_with_tools = {"content": "Listo.", "tool_calls": [{"name": "agregar_al_carrito",
                                                             "arguments": {"opcion": 2}}]}
    llm = Scripted(tool("agregar_al_carrito", opcion=2), say("Listo, agregado."), retry_with_tools)
    r = handle_sales_message(shop["tenant"], "la negra mate", conv, planner=llm)
    cart = orders.get_cart(shop["tenant"], conv)
    assert len(llm.calls) == 3 and [it["qty"] for it in cart["items"]] == [1]
    assert "Total: $89.900" in r.reply                         # respaldo: texto real del carrito
    assert stock_of(raw_conn, shop["tenant"], shop["mono_aq"]) == (6, 0)
    assert orders.conversation_orders(shop["tenant"], conv) == []


def test_quantity_correction_updates_the_cart(shop):
    conv = handle_sales_message(shop["tenant"], "busco flexible 40 cm").conversation_id
    handle_sales_message(shop["tenant"], "agregame la primera", conv)
    llm = Scripted({"content": "", "tool_calls": [
                       {"name": "quitar_del_carrito", "arguments": {"consulta": "flexible"}},
                       {"name": "agregar_al_carrito", "arguments": {"consulta": "flexible", "cantidad": 3}}]},
                   say("Hecho, ahora son 3 flexibles: $20.400 en total."))
    r = handle_sales_message(shop["tenant"], "mejor que sean 3", conv, planner=llm)
    assert [it["qty"] for it in r.cart["items"]] == [3] and "$20.400" in r.reply


# --- Preferencias por reglas (sin modelo) ---------------------------------------------------
def test_partial_correction_keeps_the_rest_of_the_search(shop):
    conv = handle_sales_message(shop["tenant"], "canillas negras para cocina").conversation_id
    r = handle_sales_message(shop["tenant"], "¿y en cromo?", conv)
    assert "lavatorio" not in r.reply.lower()                  # sigue siendo para cocina


def test_new_product_type_clears_previous_filters(shop):
    conv = handle_sales_message(shop["tenant"], "canillas negras para cocina").conversation_id
    r = handle_sales_message(shop["tenant"], "¿y flexibles?", conv)
    assert "Flexible de conexión" in r.reply


# --- N1b: comparación respaldada por la ficha -----------------------------------------------
_SMOKE_COMPARISONS = [   # respuestas reales de qwen3:8b (corridas 1 y 2), reproducidas sin red
    "La **negra mate** es un monocomando tradicional, más sencillo y versátil para uso diario. La con "
    "**pico extraíble** tiene un diseño más moderno, con el pico desmontable para facilitar el llenado de "
    "recipientes grandes (como ollas). Si querés, te agrego una de las dos: ¿cuál te gustaría? 🧽",
    "La **negra mate** es un monocomando estándar con acabado mate, ideal para uso diario. La de **pico "
    "extraíble** tiene un diseño con un pico que se puede sacar para limpiar o ajustar el chorro. Es más "
    "versátil, pero más cara ($129k vs $89k). ¿Querés que te agregue alguna? 😊",
]


def _assert_factual_comparison(reply):
    low = reply.lower()
    assert "negra mate" in low and "pico extraíble" in low and "dos llaves" not in low
    assert "$89.900" in reply and "$129.000" in reply
    assert not any(w in low for w in ("desmont", "ollas", "chorro", "moderno", "versátil"))


@pytest.mark.parametrize("model_text", _SMOKE_COMPARISONS)
def test_free_text_comparison_is_answered_from_the_ficha(shop, model_text):
    conv = _searched(shop["tenant"])
    llm = Scripted(say(model_text), say(model_text))
    r = handle_sales_message(shop["tenant"], "qué diferencia hay entre la negra mate y la de pico extraíble?",
                             conv, planner=llm)
    _assert_factual_comparison(r.reply)
    assert len(llm.calls) == 1 and r.products == []


def test_comparison_tool_reaches_the_customer_as_built_by_the_server(shop):
    conv = _searched(shop["tenant"])
    llm = Scripted(tool("comparar_productos", opciones=[2, 3]), say("La de pico sirve para ollas."))
    r = handle_sales_message(shop["tenant"], "¿cuál me conviene, la 2 o la 3?", conv, planner=llm)
    _assert_factual_comparison(r.reply)
    assert len(llm.calls) == 1                                   # no pide redacción que se descartaría


def test_rules_compare_listed_products_and_state_the_limits(shop):
    conv = handle_sales_message(shop["tenant"], "canillas negras para cocina").conversation_id
    r = handle_sales_message(shop["tenant"], "qué diferencia hay entre la 2 y la 3?", conv)
    _assert_factual_comparison(r.reply)
    assert "monocomando" in r.reply and "ficha" in r.reply       # sólo hechos cargados, y lo dice


def test_clarifying_question_on_comparison_is_kept(shop):
    conv = _searched(shop["tenant"])
    ask = "¿Para qué la vas a usar? Así te digo cuál te conviene."
    r = handle_sales_message(shop["tenant"], "¿cuál me conviene?", conv, planner=Scripted(say(ask)))
    assert r.reply == ask


# --- N1b: el perfil informa, pero no habilita acciones que el agente no ejecuta --------------
def test_profile_contact_does_not_enable_sending_or_applying_discounts(shop, raw_conn):
    _profile(raw_conn, shop["tenant"], payment_methods="Transferencia. Consultas por WhatsApp al 11-5555-0000.",
             rules=["10% de descuento pagando por transferencia"])
    for bad in ("Listo, ya te lo envié por WhatsApp.", "Te voy a mandar el resumen por WhatsApp.",
                "Listo, te apliqué el 10% de descuento.", "Te hago el 10% de descuento si cerramos hoy."):
        r = handle_sales_message(shop["tenant"], "¿me lo pasás por whatsapp con descuento?",
                                 planner=Scripted(say(bad), say(bad)))
        assert r.reply != bad, bad
    for ok in ("Podés escribirnos por WhatsApp al 11-5555-0000.",
               "Pagando por transferencia tenés 10% de descuento."):
        r = handle_sales_message(shop["tenant"], "¿tienen whatsapp? ¿hay descuento?", planner=Scripted(say(ok)))
        assert r.reply == ok


# --- N1b: una condición futura no es una confirmación de pago -------------------------------
def test_conditional_payment_sentence_is_not_a_paid_claim(shop):
    conv, order = _buy(shop["tenant"])
    cond = f"Una vez acreditado el pago del pedido #{order['number']}, lo vas a ver en el estado del pedido."
    r = handle_sales_message(shop["tenant"], "¿y después qué pasa?", conv, planner=Scripted(say(cond)))
    assert r.reply == cond
    claim = f"Tu pedido #{order['number']} ya está pagado."
    r = handle_sales_message(shop["tenant"], "¿y?", conv, planner=Scripted(say(claim), say(claim)))
    assert r.reply != claim


# --- N1c: revisión cruzada de Codex ----------------------------------------------------------
def test_total_word_does_not_unlink_price_from_product(shop):
    conv = _searched(shop["tenant"])
    bad = say("La negra mate sale $129.000 en total.")            # importe real, producto equivocado
    r = handle_sales_message(shop["tenant"], "¿cuánto sale la negra mate?", conv,
                             planner=Scripted(tool("consultar_producto", opcion=2), bad, bad))
    assert "$129.000" not in r.reply and "$89.900" in r.reply
    handle_sales_message(shop["tenant"], "agregame la 2", conv)
    handle_sales_message(shop["tenant"], "agregame la 2", conv)
    ok = "Llevás 2 negra mate por $179.800 en total."             # total identificado del carrito
    r = handle_sales_message(shop["tenant"], "¿cuánto es?", conv, planner=Scripted(say(ok)))
    assert r.reply == ok


def test_unnumbered_paid_claim_is_ambiguous_with_paid_and_pending_orders(shop):
    conv, first = _buy(shop["tenant"])
    _pay(first)
    conv, second = _buy(shop["tenant"], "canilla de lavatorio cromo", conv)
    bad = say("Tu pedido está pagado.")
    r = handle_sales_message(shop["tenant"], "¿cómo va mi pedido?", conv, planner=Scripted(bad, bad))
    assert r.reply != bad["content"]
    assert f"#{first['number']}" in r.reply and f"#{second['number']}" in r.reply   # resumen por pedido


def test_partial_correction_keeps_budget_until_replaced_or_cleared(shop):
    conv = handle_sales_message(shop["tenant"], "canilla para cocina hasta 100 mil").conversation_id
    r = handle_sales_message(shop["tenant"], "¿y en negro?", conv)
    assert "$89.900" in r.reply and "$129.000" not in r.reply     # conserva el tope
    r = handle_sales_message(shop["tenant"], "¿y hasta 150 mil?", conv)
    assert "$129.000" in r.reply                                  # lo reemplaza
    handle_sales_message(shop["tenant"], "canilla para cocina hasta 100 mil", conv)
    r = handle_sales_message(shop["tenant"], "¿y sin límite de precio?", conv)
    assert "$129.000" in r.reply                                  # lo quita a pedido
    handle_sales_message(shop["tenant"], "canilla para cocina hasta 55 mil", conv)
    r = handle_sales_message(shop["tenant"], "¿y canillas de lavatorio?", conv)
    assert "$59.900" in r.reply                                   # otro tipo: arranca sin tope


def test_use_recommendation_is_answered_from_the_ficha_and_flags_missing_data(shop):
    conv = _searched(shop["tenant"])
    bad = say("Te recomiendo la de pico extraíble: el pico sale y llena ollas grandes fácil.")
    llm = Scripted(bad, bad)
    r = handle_sales_message(shop["tenant"], "¿Cuál me recomendás para llenar ollas?", conv, planner=llm)
    low = r.reply.lower()
    assert "pico sale" not in low and "ficha" in low and "llenar ollas" in low
    assert r.requires_human and len(llm.calls) == 1


def test_rewrite_that_recommends_freely_is_also_replaced_by_the_ficha(shop):
    conv = _searched(shop["tenant"])
    llm = Scripted(say("Te conviene la de $50.000."),               # dato falso -> reescritura
                   say("Te recomiendo la de pico extraíble, que llena ollas grandes."))
    r = handle_sales_message(shop["tenant"], "¿cuál me recomendás para llenar ollas?", conv, planner=llm)
    assert "llena ollas grandes" not in r.reply and "ficha" in r.reply and r.requires_human


def test_literal_comparison_flags_human_only_when_asked_data_is_missing(shop):
    conv = _searched(shop["tenant"])
    r = handle_sales_message(shop["tenant"], "¿cuál tiene más caudal, la 2 o la 3?", conv,
                             planner=Scripted(tool("comparar_productos", opciones=[2, 3])))
    assert "caudal" in r.reply.lower() and r.requires_human
    r = handle_sales_message(shop["tenant"], "¿qué diferencia hay entre la 2 y la 3?", conv,
                             planner=Scripted(tool("comparar_productos", opciones=[2, 3])))
    assert not r.requires_human                                   # precio/stock completos: sin revisión


# --- N1d: contraejemplos pendientes de la revisión ------------------------------------------
def test_cart_total_only_excuses_a_clause_about_the_cart_products(shop):
    conv = _searched(shop["tenant"])
    handle_sales_message(shop["tenant"], "agregame la 3", conv)    # carrito: pico extraíble $129.000
    bad = say("La negra mate sale $129.000 en total.")            # = total del carrito, otro producto
    r = handle_sales_message(shop["tenant"], "¿cuánto sale la negra mate?", conv, planner=Scripted(bad, bad))
    assert r.reply != bad["content"] and "$89.900" in r.reply
    for ok in ("La de pico extraíble te queda en $129.000 en total.", "Tu carrito suma $129.000 en total."):
        r = handle_sales_message(shop["tenant"], "¿cuánto es?", conv, planner=Scripted(say(ok)))
        assert r.reply == ok


@pytest.mark.parametrize("budget,over", [("150", None), ("100", "$129.000")])
def test_use_recommendation_with_budget_still_answers_from_the_ficha(shop, budget, over):
    conv = _searched(shop["tenant"])
    bad = say("Te recomiendo la de pico extraíble: el pico sale y llena ollas grandes fácil.")  # smoke-like
    llm = Scripted(bad, bad)
    r = handle_sales_message(shop["tenant"], f"¿Cuál me recomendás para llenar ollas hasta {budget} mil?",
                             conv, planner=llm)
    low = r.reply.lower()
    assert "pico sale" not in low and "ficha" in low and "llenar ollas" in low and r.requires_human
    assert len(llm.calls) == 1 and (over is None or over not in r.reply)


def test_budget_recommendation_rewrite_is_also_replaced_by_the_ficha(shop):
    conv = _searched(shop["tenant"])
    llm = Scripted(say("Te conviene la de $50.000."),
                   say("Te recomiendo la de pico extraíble, que llena ollas grandes."))
    r = handle_sales_message(shop["tenant"], "¿cuál me recomendás para llenar ollas hasta 150 mil?", conv,
                             planner=llm)
    assert "llena ollas grandes" not in r.reply and "ficha" in r.reply and r.requires_human


def test_cart_total_cannot_be_attributed_to_one_of_its_products(shop):
    conv = _searched(shop["tenant"])
    handle_sales_message(shop["tenant"], "agregame la 2", conv)    # negra mate $89.900
    handle_sales_message(shop["tenant"], "agregame la 3", conv)    # pico extraíble $129.000
    bad = say("La negra mate sale $218.900 en total.")            # total del carrito, no de la negra mate
    r = handle_sales_message(shop["tenant"], "¿cuánto sale la negra mate?", conv, planner=Scripted(bad, bad))
    assert r.reply != bad["content"]
    ok = "Tu carrito suma $218.900 en total."
    r = handle_sales_message(shop["tenant"], "¿cuánto es?", conv, planner=Scripted(say(ok)))
    assert r.reply == ok
