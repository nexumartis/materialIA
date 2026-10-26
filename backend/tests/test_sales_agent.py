"""Agente de ventas por chat: escenarios de aceptación A, B y D del diseño (modo mock).

Las respuestas sólo pueden contener datos que devolvieron las herramientas: precios del catálogo,
disponible real, número y estado del pedido, link del proveedor."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.agent.sales_agent import handle_sales_message
from app.domain import orders
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider

from conftest import stock_of


class Chat:
    def __init__(self, tenant):
        self.tenant, self.conv, self.last = tenant, None, None

    def say(self, text):
        self.last = handle_sales_message(self.tenant, text, self.conv)
        self.conv = self.last.conversation_id
        return self.last.reply


def test_scenario_a_successful_sale_end_to_end(shop, raw_conn):
    chat = Chat(shop["tenant"])
    r = chat.say("Hola, ¿tenés canillas negras para cocina?")
    assert "$89.900" in r and "$129.000" in r and "$74.500" in r
    assert "lavatorio" not in r                      # sólo cocina

    r = chat.say("¿Cuál me recomendás por menos de 100 mil?")
    assert "$129.000" not in r and "$89.900" in r

    r = chat.say("Dale, quiero la segunda")
    assert "agregué 1 × Canilla de cocina monocomando negra mate" in r
    assert chat.last.cart["total"] == 89900
    assert stock_of(raw_conn, shop["tenant"], shop["mono_aq"]) == (6, 0)   # agregar no aparta

    r = chat.say("La compro")
    assert "¿Confirmás?" in r and "$89.900" in r
    assert orders.conversation_orders(shop["tenant"], chat.conv) == []     # sin "sí" no hay pedido

    r = chat.say("sí")
    assert "Pedido #" in r and "SIMULADO" in r and chat.last.payment["checkout_url"] in r
    assert stock_of(raw_conn, shop["tenant"], shop["mono_aq"]) == (6, 1)

    # "Ya pagué" sin aviso del proveedor no cambia nada.
    r = chat.say("ya pagué")
    assert "no veo acreditado" in r
    assert orders.conversation_orders(shop["tenant"], chat.conv)[0]["status"] == "PENDING_PAYMENT"

    pref = chat.last.orders[0]["payment"]["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    assert stock_of(raw_conn, shop["tenant"], shop["mono_aq"]) == (5, 0)

    # Escenario B: seguimiento con el estado real.
    r = chat.say("¿Ya salió mi pedido?")
    assert "pagado, todavía no despachado" in r
    order_id = chat.last.orders[0]["id"]
    orders.advance_status(shop["tenant"], order_id, "DISPATCHED")
    r = chat.say("¿dónde está mi pedido?")
    assert "despachado" in r and "seguimiento" in r            # no inventa tracking


def test_scenario_d_out_of_stock_offers_real_alternatives(shop):
    chat = Chat(shop["tenant"])
    r = chat.say("¿tenés canilla de lavatorio negra?")
    assert "sin stock" in r and "no te la puedo prometer" in r
    assert "Canilla de lavatorio monocomando cromo" in r and "$52.000" in r
    r = chat.say("agregame la primera")
    assert "cromo" in r and chat.last.cart["total"] == 52000


def test_cancel_confirmation_creates_nothing(shop):
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 2")
    assert "¿Confirmás?" in chat.say("quiero pagar")
    assert "no generé nada" in chat.say("no")
    assert chat.say("sí") and orders.conversation_orders(shop["tenant"], chat.conv) == []


def test_quantity_above_stock_is_not_promised(shop):
    chat = Chat(shop["tenant"])
    chat.say("canilla con pico extraíble")
    r = chat.say("agregame 5 de la primera")
    assert "sólo hay 3" in r and chat.last.cart is None


def test_custom_item_goes_to_a_person(shop):
    chat = Chat(shop["tenant"])
    chat.say("necesito un inodoro largo")
    r = chat.say("quiero ese")
    assert "persona" in r and chat.last.requires_human is True
    assert chat.last.cart is None


def test_remove_and_view_cart(shop):
    chat = Chat(shop["tenant"])
    chat.say("flexible de 40")
    chat.say("agregame 2")
    assert "Total: $13.600" in chat.say("¿cuánto es el total?")
    assert "vacío" in chat.say("sacalo")


def test_sales_endpoint_and_tenant_allowlist(shop):
    client = TestClient(app)
    resp = client.post("/sandbox/sales/chat?company=C", json={"message": "tenés canillas negras para cocina?"})
    assert resp.status_code == 200 and resp.json()["products"]
    assert client.post("/sandbox/sales/chat?company=Z", json={"message": "hola"}).status_code == 400


def test_agent_does_not_misstate_orders_that_need_a_person(shop, raw_conn):
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 1")
    chat.say("la compro")
    chat.say("sí")
    order = chat.last.orders[0]
    with raw_conn.cursor() as cur:
        cur.execute("update orders set attention_reason = 'amount_mismatch' where id = %s", (order["id"],))
    raw_conn.commit()
    r = chat.say("¿cómo va mi pedido?")
    assert "una persona" in r.lower() and "no hace falta que pagues" in r and "http" not in r


def test_paid_without_stock_is_explained_honestly(shop, raw_conn):
    chat = Chat(shop["tenant"])
    chat.say("canilla dos llaves negra")
    chat.say("agregame la primera")
    chat.say("la compro")
    chat.say("sí")
    order = chat.last.orders[0]
    with raw_conn.cursor() as cur:
        cur.execute("update orders set status = 'CANCELLED', attention_reason = 'paid_without_stock' "
                    "where id = %s", (order["id"],))
    raw_conn.commit()
    r = chat.say("¿ya salió mi pedido?")
    assert "Recibimos el pago" in r and "venció" not in r


def test_confirmation_is_for_the_summarized_total(shop):
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 1")
    chat.say("la compro")
    # Otra pestaña/mensaje cambia el carrito antes del "sí".
    orders.add_item(shop["tenant"], chat.conv, shop["flex"], 1)
    r = chat.say("sí")
    assert "cambió" in r and "$13.600" in r
    assert orders.conversation_orders(shop["tenant"], chat.conv) == []
    assert "Pedido #" in chat.say("sí")


def test_double_yes_reports_existing_order(shop):
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 1")
    chat.say("la compro")
    chat.say("sí")
    r = chat.say("la compro")
    assert "esperando el pago" in r and "http" in r


def test_bare_number_picks_the_listed_option(shop):
    chat = Chat(shop["tenant"])
    chat.say("Hola, ¿tenés canillas negras para cocina?")
    r = chat.say("2")
    assert "agregué 1 × Canilla de cocina monocomando negra mate" in r
    assert "No tengo una opción 9" in chat.say("9")
    assert "agregué 1 × Canilla de cocina dos llaves negra" in chat.say("la primera")


def test_typos_are_corrected_against_the_catalog(shop):
    chat = Chat(shop["tenant"])
    r = chat.say("Canulla negra")
    assert "Canilla de cocina monocomando negra mate" in r


def test_in_stock_options_are_listed_first(shop):
    chat = Chat(shop["tenant"])
    r = chat.say("canilla negra")
    lines = [l for l in r.splitlines() if l[:2] in ("1.", "2.", "3.", "4.")]
    assert "SIN STOCK" in lines[-1] and "lavatorio" in lines[-1]


def test_unknown_message_after_a_list_asks_for_the_number(shop):
    chat = Chat(shop["tenant"])
    chat.say("canilla negra")
    assert "decime el número" in chat.say("mmm")


def test_saying_no_more_items_goes_to_checkout(shop):
    for closing in ("no", "no quiero sumar nada mas", "nada más, gracias", "eso es todo"):
        chat = Chat(shop["tenant"])
        chat.say("Hola, ¿tenés canillas negras para cocina?")
        chat.say("1")
        assert "sumar canilla" not in chat.say("si quiero sumar canilla de cocina con pico extarible")
        r = chat.say(closing)
        assert "Te confirmo el pedido" in r and "$203.500" in r, (closing, r)


def test_no_with_a_change_is_not_just_a_cancel(shop):
    chat = Chat(shop["tenant"])
    chat.say("busco flexible 40 cm")
    chat.say("agregame 2")
    assert "¿Confirmás?" in chat.say("la compro")
    r = chat.say("no espera, sacalo")
    assert "no generé nada" not in r and "vacío" in r


def test_interactive_cards_and_quick_replies(shop):
    chat = Chat(shop["tenant"])
    chat.say("canillas negras para cocina")
    cards = chat.last.ui["products"]
    assert [c["n"] for c in cards] == [1, 2, 3]
    assert cards[1]["action"] == {"label": "Agregar", "message": "agregame la 2"}
    # El botón envía un mensaje que el agente entiende.
    chat.say(cards[1]["action"]["message"])
    assert chat.last.cart["total"] == 89900
    assert {q["label"] for q in chat.last.ui["quick_replies"]} == {"Comprar", "Ver carrito"}
    chat.say("comprar")
    assert chat.last.ui["quick_replies"][0] == {"label": "Sí, confirmo", "message": "sí"}
    chat.say("sí")
    assert chat.last.ui["payment"]["url"] == chat.last.payment["checkout_url"]


def test_out_of_stock_card_has_no_add_button_and_history_keeps_ui(shop):
    from app.domain import opportunities
    chat = Chat(shop["tenant"])
    chat.say("canilla negra")
    out = [c for c in chat.last.ui["products"] if c["available"] == 0]
    assert out and out[0]["action"] is None
    history = opportunities.conversation_messages(shop["tenant"], chat.conv)
    assert history[-1]["ui"]["products"]
