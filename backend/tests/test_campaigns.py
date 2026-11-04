"""Campañas: audiencias de un catálogo cerrado, mensaje con datos reales, envío simulado por el worker,
tope de frecuencia, baja pedida en la charla, resultados (quién compró) y aislamiento entre negocios."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth, buyer_session
from app.agent import sales_agent
from app.domain import campaigns, orders
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop

CART = {"kind": "abandoned_cart", "params": {"days": 3, "min_amount": 20000}}
MSG = "Hola {nombre}! Te quedó {producto} en el carrito ({monto}). {link}"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


def _cart(shop, raw_conn, days_ago=4):
    """Una charla con un carrito armado hace `days_ago` días."""
    conv, _ = buyer_session.start(shop["tenant"])
    assert orders.add_item(shop["tenant"], conv, shop["item"], 1).status == "ok"
    with raw_conn.cursor() as cur:
        cur.execute("update orders set updated_at = now() - make_interval(days => %s) "
                    "where tenant_id = %s and conversation_id = %s", (days_ago, shop["tenant"], conv))
    raw_conn.commit()
    return conv


def _launch(client, shop, audience=CART, message=MSG):
    h = bearer(shop["uid"])
    c = client.post("/app/campaigns", headers=h, json={"name": "Carritos", "audience": audience, "message": message})
    assert c.status_code == 200, c.text
    r = client.post(f"/app/campaigns/{c.json()['id']}/launch", headers=h, json={"scheduled_at": None})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "scheduled"
    return c.json()["id"]


def test_abandoned_cart_preview_uses_real_order_data(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Preview")
    _cart(shop, raw_conn)
    _cart(shop, raw_conn, days_ago=1)            # muy reciente: no entra
    h = bearer(shop["uid"])
    p = client.post("/app/campaigns/preview", headers=h, json={"audience": CART, "message": MSG}).json()
    assert p["count"] == 1
    msg = p["sample"][0]["message"]
    with raw_conn.cursor() as cur:
        cur.execute("select i.name, o.total from order_items i join orders o on o.id = i.order_id "
                    "where o.tenant_id = %s and o.updated_at < now() - interval '2 days'", (shop["tenant"],))
        item = cur.fetchone()
    raw_conn.commit()
    assert item["name"] in msg and campaigns.money(item["total"]) in msg
    assert msg.startswith("Hola! ")                 # sin nombre real no inventa uno
    assert f"#/tienda/{shop['slug']}" in msg
    high = {"kind": "abandoned_cart", "params": {"days": 3, "min_amount": 10_000_000}}
    assert client.post("/app/campaigns/preview", headers=h, json={"audience": high, "message": MSG}).json()["count"] == 0


def test_validation_rejects_unknown_audience_and_placeholders(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Validación")
    h = bearer(shop["uid"])
    bad = [({"kind": "drop table", "params": {}}, MSG), (CART, "Hola {apellido}"),
           ({"kind": "abandoned_cart", "params": {"days": -5}}, MSG), (CART, "x" * 701)]
    for audience, message in bad:
        r = client.post("/app/campaigns", headers=h, json={"audience": audience, "message": message})
        assert r.status_code == 400, (audience, message)


def test_worker_sends_simulated_and_frequency_cap(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Envío")
    _cart(shop, raw_conn)
    cid = _launch(client, shop)
    assert campaigns.dispatch_due() >= 1
    h = bearer(shop["uid"])
    view = client.get(f"/app/campaigns/{cid}", headers=h).json()
    assert view["status"] == "sent" and view["stats"]["sent"] == 1 and view["channel"] == "simulado"
    assert view["recipients"][0]["status"] == "sent" and "Te quedó" in view["recipients"][0]["message"]
    # Ya recibió una campaña esta semana: no se le vuelve a escribir.
    p = client.post("/app/campaigns/preview", headers=h, json={"audience": CART, "message": MSG}).json()
    assert p["count"] == 0 and p["excluded"]["recently_contacted"] == 1
    assert client.get("/app/campaigns", headers=h).json()["channel"]["real_sending"] is False


def test_customer_opt_out_in_chat_excludes_them(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Baja")
    conv = _cart(shop, raw_conn)
    reply = sales_agent.handle_sales_message(shop["tenant"], "no quiero recibir más promociones", conv)
    assert "no te vamos a mandar más" in reply.reply
    p = client.post("/app/campaigns/preview", headers=bearer(shop["uid"]), json={"audience": CART, "message": MSG}).json()
    assert p["count"] == 0 and p["excluded"]["opted_out"] == 1


def test_conversion_counts_paid_order_after_send(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Conversión")
    conv = _cart(shop, raw_conn)
    cid = _launch(client, shop)
    campaigns.dispatch_due()
    order = orders.checkout(shop["tenant"], conv).order
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    stats = client.get(f"/app/campaigns/{cid}", headers=bearer(shop["uid"])).json()["stats"]
    assert stats["converted"] == 1 and stats["revenue"] == pytest.approx(order["total"])


def test_payment_pending_audience_and_cancel(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Cobranza")
    conv, _ = buyer_session.start(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    orders.checkout(shop["tenant"], conv)
    h = bearer(shop["uid"])
    due = {"kind": "payment_pending", "params": {"days": 0, "min_amount": 0}}
    p = client.post("/app/campaigns/preview", headers=h,
                    json={"audience": due, "message": "Quedó pendiente {monto}"}).json()
    assert p["count"] == 1 and p["sample"][0]["detail"].startswith("Debe $")
    c = client.post("/app/campaigns", headers=h, json={"audience": due, "message": "Quedó pendiente {monto}"}).json()
    r = client.post(f"/app/campaigns/{c['id']}/launch", headers=h,
                    json={"scheduled_at": "2099-01-01T10:00:00-03:00"})
    assert r.status_code == 400                      # más de 60 días adelante
    assert client.post(f"/app/campaigns/{c['id']}/cancel", headers=h).json()["status"] == "cancelled"
    assert client.post(f"/app/campaigns/{c['id']}/launch", headers=h, json={}).status_code == 400


def test_other_business_cannot_see_or_target(client, accounts, raw_conn):
    a = _shop(client, accounts, raw_conn, "Campañas A")
    b = _shop(client, accounts, raw_conn, "Campañas B")
    _cart(a, raw_conn)
    cid = _launch(client, a)
    hb = bearer(b["uid"])
    assert client.get(f"/app/campaigns/{cid}", headers=hb).status_code == 404
    assert client.post(f"/app/campaigns/{cid}/cancel", headers=hb).status_code == 404
    assert client.get("/app/campaigns", headers=hb).json()["campaigns"] == []
    assert client.post("/app/campaigns/preview", headers=hb, json={"audience": CART, "message": MSG}).json()["count"] == 0


def test_opt_out_only_for_marketing_phrases():
    hit = ["no quiero recibir más promociones", "dame de baja", "no me manden más mensajes", "basta de ofertas!"]
    miss = ["no me mandes más de 3 cajas", "quiero dar de baja el pedido", "dame de baja el pedido de ayer",
            "no quiero más la canilla negra"]
    from app.domain.inventory import normalize
    assert all(sales_agent._RE_OPT_OUT.search(normalize(t)) for t in hit)
    assert not any(sales_agent._RE_OPT_OUT.search(normalize(t)) for t in miss)


def test_two_campaigns_built_together_write_once(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Doble")
    conv = _cart(shop, raw_conn)
    orders.checkout(shop["tenant"], conv)                      # también queda con pago pendiente
    a = _launch(client, shop)
    b = _launch(client, shop, {"kind": "payment_pending", "params": {"days": 0, "min_amount": 0}}, "Pendiente {monto}")
    # Ninguna estaba enviada al armar la otra: el tope se aplica al enviar.
    with raw_conn.cursor() as cur:
        cur.execute("update orders set status = 'CART_OPEN' where tenant_id = %s", (shop["tenant"],))
    raw_conn.commit()
    campaigns._materialize(shop["tenant"], a)
    with raw_conn.cursor() as cur:
        cur.execute("update orders set status = 'PENDING_PAYMENT' where tenant_id = %s", (shop["tenant"],))
    raw_conn.commit()
    campaigns._materialize(shop["tenant"], b)
    campaigns.dispatch_due()
    h = bearer(shop["uid"])
    sent = [client.get(f"/app/campaigns/{x}", headers=h).json()["stats"]["sent"] for x in (a, b)]
    assert sorted(sent) == [0, 1]


def test_cancelled_before_build_creates_no_recipients(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Carrera")
    _cart(shop, raw_conn)
    cid = _launch(client, shop)
    h = bearer(shop["uid"])
    client.post(f"/app/campaigns/{cid}/cancel", headers=h)
    campaigns._materialize(shop["tenant"], cid)
    view = client.get(f"/app/campaigns/{cid}", headers=h).json()
    assert view["status"] == "cancelled" and view["stats"]["recipients"] == 0


def test_cart_amount_is_todays_price_and_skips_unpriced(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Campañas Precio")
    _cart(shop, raw_conn)
    h = bearer(shop["uid"])
    with raw_conn.cursor() as cur:
        cur.execute("update price_entries set amount = 150000 where tenant_id = %s and item_id = %s", (shop["tenant"], shop["item"]))
    raw_conn.commit()
    p = client.post("/app/campaigns/preview", headers=h, json={"audience": CART, "message": "{monto}"}).json()
    assert p["sample"][0]["message"] == "$150.000"
    with raw_conn.cursor() as cur:
        cur.execute("update price_entries set valid_until = current_date - 1 where tenant_id = %s and item_id = %s",
                    (shop["tenant"], shop["item"]))
    raw_conn.commit()
    assert client.post("/app/campaigns/preview", headers=h, json={"audience": CART, "message": "{monto}"}).json()["count"] == 0
