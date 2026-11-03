"""Webhooks salientes: sólo el dueño los configura; sólo https públicos (SSRF); el secreto se muestra
una vez; el evento se encola en la misma transacción del pago; la entrega va firmada (HMAC) a la IP
verificada, con reintentos; otro negocio no ve ni recibe nada."""
from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import orders, safe_http, webhooks
from app.main import app
from app.payments import service
from app.payments.providers import SimulatedProvider
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop

PUBLIC = [(0, 0, 0, "", ("93.184.216.34", 0))]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    monkeypatch.setattr(safe_http.socket, "getaddrinfo",
                        lambda host, *_: [(0, 0, 0, "", ("10.0.0.7", 0))] if "interno" in host else PUBLIC)


@pytest.fixture
def receiver(monkeypatch):
    """Servidor receptor simulado: guarda lo que llega; `status` define la respuesta."""
    got = {"calls": [], "status": 200}

    def handler(request):
        got["calls"].append(request)
        return httpx.Response(got["status"], text="ok")
    real = webhooks.httpx.Client
    monkeypatch.setattr(webhooks.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    return got


def _pay(shop):
    from conftest import new_conversation
    conv = new_conversation(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    order = orders.checkout(shop["tenant"], conv).order
    pref = service.start_payment(shop["tenant"], order["id"])["checkout_url"].rsplit("/", 1)[1]
    headers, body = SimulatedProvider().pay(pref, "approved")
    assert service.receive_notification("simulated", headers, {}, body)[1] == "pedido pagado"
    return order


def test_only_public_https_and_secret_shown_once(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Webhooks")
    h = bearer(shop["uid"])
    for bad in ("http://hooks.example/x", "https://interno.example/x", "https://user:pw@hooks.example/x",
                "ftp://hooks.example", "https://" + "a" * 500 + ".com"):
        assert client.post("/app/webhooks", headers=h, json={"url": bad}).status_code == 400, bad
    r = client.post("/app/webhooks", headers=h, json={"url": "https://hooks.example/pv", "events": ["order.paid"]})
    assert r.status_code == 200 and r.json()["secret"].startswith("whsec_")
    listed = client.get("/app/webhooks", headers=h).json()
    assert "secret" not in json.dumps(listed["endpoints"]) and listed["endpoints"][0]["events"] == ["order.paid"]
    assert client.post("/app/webhooks", headers=h, json={"url": "https://hooks.example/y", "events": ["nada"]}).status_code == 400
    other, _ = accounts("Otro Webhooks")
    assert client.get("/app/webhooks", headers=bearer(other)).json()["endpoints"] == []
    assert client.delete(f"/app/webhooks/{r.json()['id']}", headers=bearer(other)).status_code == 404


def test_paid_order_delivers_signed_event_with_retries(accounts, raw_conn, receiver):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Webhooks 2")
    ep = client.post("/app/webhooks", headers=bearer(shop["uid"]), json={"url": "https://hooks.example/pv"}).json()
    order = _pay(shop)

    receiver["status"] = 500                                          # primer intento falla
    assert webhooks.deliver_due() >= 1
    d = client.get("/app/webhooks", headers=bearer(shop["uid"])).json()["deliveries"][0]
    assert d["status"] == "pending" and d["attempts"] == 1 and d["last_status_code"] == 500
    with raw_conn.cursor() as cur:                                    # adelanta el reintento
        cur.execute("update webhook_deliveries set next_attempt_at = now() where tenant_id = %s", (shop["tenant"],))
    raw_conn.commit()
    receiver["status"] = 200
    webhooks.deliver_due()
    req = receiver["calls"][-1]
    assert str(req.url) == "https://93.184.216.34/pv" and req.headers["host"] == "hooks.example"   # IP fija
    body = req.content
    payload = json.loads(body)
    assert payload["event"] == "order.paid" and payload["data"]["number"] == order["number"]
    assert "token" not in body.decode() and "checkout" not in body.decode()                       # datos mínimos
    t, v1 = (p.split("=", 1)[1] for p in req.headers["x-pv-signature"].split(","))
    expected = hmac.new(ep["secret"].encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(v1, expected)
    d = client.get("/app/webhooks", headers=bearer(shop["uid"])).json()["deliveries"][0]
    assert d["status"] == "sent" and d["attempts"] == 2


def test_other_business_does_not_receive_and_ping(accounts, raw_conn, receiver):
    client = TestClient(app)
    a = _shop(client, accounts, raw_conn, "Tienda Webhooks A")
    b = _shop(client, accounts, raw_conn, "Tienda Webhooks B")
    ep = client.post("/app/webhooks", headers=bearer(a["uid"]), json={"url": "https://hooks.example/a"}).json()
    _pay(b)
    webhooks.deliver_due()
    assert not [c for c in receiver["calls"] if c.url.path == "/a"]
    r = client.post(f"/app/webhooks/{ep['id']}/test", headers=bearer(a["uid"]))
    assert r.status_code == 200 and r.json()["ok"] and receiver["calls"][-1].headers["x-pv-event"] == "ping"


def test_panel_role_can_enqueue_but_never_read_secret(accounts, raw_conn):
    import psycopg
    from app.db import user_tx
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Webhooks Secreto")
    client.post("/app/webhooks", headers=bearer(shop["uid"]), json={"url": "https://hooks.example/s"})
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with user_tx(shop["uid"]) as (cur, _):
            cur.execute("select secret from webhook_endpoints")
    with user_tx(shop["uid"]) as (cur, tenant):
        assert webhooks.enqueue(cur, tenant, "order.cancelled", {"order_id": "x"}) == 1


def test_empty_events_rejected_and_unexpected_error_counts_as_attempt(accounts, raw_conn, monkeypatch):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Webhooks Errores")
    h = bearer(shop["uid"])
    assert client.post("/app/webhooks", headers=h, json={"url": "https://hooks.example/e", "events": []}).status_code == 400
    client.post("/app/webhooks", headers=h, json={"url": "https://hooks.example/e"})
    _pay(shop)

    def boom(**kw):
        raise UnicodeError("host raro")
    monkeypatch.setattr(webhooks.httpx, "Client", boom)
    assert webhooks.deliver_due() >= 1                       # no se cae el worker
    d = client.get("/app/webhooks", headers=h).json()["deliveries"][0]
    assert d["attempts"] == 1 and d["status"] == "pending" and d["last_error"] == "UnicodeError"
