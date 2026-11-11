"""Mercado Pago por negocio: el dueño conecta SU cuenta con el OAuth oficial; los tokens quedan cifrados;
el state no se puede alterar ni reusar vencido; cada negocio cobra con su cuenta y un aviso de pago no
acredita pedidos de otro negocio; el worker renueva los tokens antes de que venzan."""
from __future__ import annotations

import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.domain import orders
from app.main import app
from app.payments import mp_oauth, providers, service
from app.payments.providers import MercadoPagoProvider, sign_notification
from conftest import new_conversation
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop
from test_team import signup  # noqa: F401  (fixture)

KEY_FERNET = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    monkeypatch.setattr(settings, "mp_client_id", "app-123")
    monkeypatch.setattr(settings, "mp_client_secret", "secreto-app")
    monkeypatch.setattr(settings, "mp_token_key", KEY_FERNET)
    monkeypatch.setattr(settings, "mp_access_token", None)


@pytest.fixture
def client():
    return TestClient(app)


def _mp(seen: dict, token="APP_USR-vendedor", refresh="TG-1", status=200):
    """Mercado Pago simulado: /oauth/token devuelve tokens; registra lo que recibió."""
    def handler(request: httpx.Request) -> httpx.Response:
        seen.setdefault("calls", []).append((request.method, request.url.path, json.loads(request.content or b"{}")))
        if request.url.path == "/oauth/token":
            return httpx.Response(status, json={"access_token": token, "refresh_token": refresh, "user_id": 555,
                                                "public_key": "APP_USR-pk", "live_mode": True, "expires_in": 15552000})
        return httpx.Response(404, json={})
    return httpx.Client(base_url="https://api.mp.test", transport=httpx.MockTransport(handler))


def _connect(client, shop, seen=None):
    url = client.post("/app/payments/mercadopago/connect", headers=bearer(shop["uid"])).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    return mp_oauth.complete("CODE-1", state, _mp(seen if seen is not None else {})), url


def test_owner_connects_and_tokens_are_encrypted(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "MP Alta")
    seen: dict = {}
    tenant, url = _connect(client, shop, seen)
    q = parse_qs(urlparse(url).query)
    assert url.startswith(mp_oauth.AUTH_URL) and q["client_id"] == ["app-123"] and q["response_type"] == ["code"]
    assert tenant == shop["tenant"]
    body = seen["calls"][0][2]
    assert body["grant_type"] == "authorization_code" and body["code"] == "CODE-1" and body["client_secret"] == "secreto-app"
    with raw_conn.cursor() as cur:
        cur.execute("select access_token_encrypted, refresh_token_encrypted from mp_connections where tenant_id = %s",
                    (shop["tenant"],))
        row = cur.fetchone()
    raw_conn.commit()
    assert "APP_USR-vendedor" not in row["access_token_encrypted"] and "TG-1" not in row["refresh_token_encrypted"]
    assert mp_oauth.token_for(shop["tenant"]) == "APP_USR-vendedor"
    st = client.get("/app/payments/mercadopago", headers=bearer(shop["uid"])).json()
    assert st["connected"] and st["mp_user_id"] == "555" and st["live_mode"] is True
    assert "token" not in json.dumps({k: v for k, v in st.items() if k != "expires_at"}).replace("connected", "")
    assert client.delete("/app/payments/mercadopago", headers=bearer(shop["uid"])).json()["disconnected"]
    assert mp_oauth.token_for(shop["tenant"]) is None


def test_state_cannot_be_forged_or_reused_late(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "MP State")
    with pytest.raises(mp_oauth.OAuthError):
        mp_oauth.complete("CODE", "inventado", _mp({}))
    old = Fernet(KEY_FERNET.encode()).encrypt_at_time(
        json.dumps({"t": shop["tenant"], "u": shop["uid"], "n": "x"}).encode(), int(time.time()) - 700).decode()
    with pytest.raises(mp_oauth.OAuthError):
        mp_oauth.complete("CODE", old, _mp({}))
    # Un state válido pero de alguien que no es dueño de ese negocio no conecta nada.
    other = _shop(client, accounts, raw_conn, "MP Otro")
    forged = Fernet(KEY_FERNET.encode()).encrypt(json.dumps({"t": shop["tenant"], "u": other["uid"], "n": "y"}).encode()).decode()
    with pytest.raises(mp_oauth.OAuthError):
        mp_oauth.complete("CODE", forged, _mp({}))
    assert mp_oauth.token_for(shop["tenant"]) is None


def test_callback_redirects_back_to_panel(client, accounts, raw_conn, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "MP Callback")
    url = client.post("/app/payments/mercadopago/connect", headers=bearer(shop["uid"])).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    real = mp_oauth._token_request
    monkeypatch.setattr(mp_oauth, "_token_request", lambda body, client=None: real(body, _mp({})))
    r = client.get(f"/mp/oauth/callback?code=CODE&state={state}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("#/integraciones?mp=ok")
    r = client.get("/mp/oauth/callback?code=CODE&state=malo", follow_redirects=False)
    assert r.headers["location"].endswith("?mp=error")


def test_each_business_charges_with_its_own_account(client, accounts, raw_conn, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "MP Cobro")
    _connect(client, shop)
    monkeypatch.setattr(settings, "payment_provider", "mercadopago")
    assert providers.get_provider(tenant_id=shop["tenant"])._token == "APP_USR-vendedor"
    other = _shop(client, accounts, raw_conn, "MP Sin Cuenta")
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "mp_access_token", "TEST-plataforma")
    with pytest.raises(providers.PaymentProviderError):        # en producción, nunca la cuenta de la plataforma
        providers.get_provider(tenant_id=other["tenant"])._auth


def test_notification_for_another_business_is_ignored(client, accounts, raw_conn, monkeypatch):
    a = _shop(client, accounts, raw_conn, "MP Aviso A")
    b = _shop(client, accounts, raw_conn, "MP Aviso B")
    conv = new_conversation(a["tenant"])
    orders.add_item(a["tenant"], conv, a["item"], 1)
    order = orders.checkout(a["tenant"], conv).order

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": 987, "status": "approved", "external_reference": order["id"],
                                         "transaction_amount": order["total"], "currency_id": "ARS"})
    fake = httpx.Client(base_url="https://api.mp.test", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(settings, "payment_provider", "mercadopago")
    monkeypatch.setattr(settings, "mp_webhook_secret", "mp-secret")
    monkeypatch.setattr(service, "get_provider", lambda name=None, tenant_id=None: MercadoPagoProvider(
        client=fake, access_token="tok", tenant_id=tenant_id))
    headers = sign_notification("mp-secret", "987", "req-1")
    status, outcome = service.receive_notification("mercadopago", headers, {"type": "payment", "data.id": "987", "t": b["tenant"]},
                                                   {"type": "payment", "data": {"id": "987"}})
    assert (status, outcome) == (200, "pago de otro negocio: ignorado")
    assert orders.get_order(a["tenant"], order["id"])["status"] == "PENDING_PAYMENT"
    status, outcome = service.receive_notification("mercadopago", headers, {"type": "payment", "data.id": "987", "t": a["tenant"]},
                                                   {"type": "payment", "data": {"id": "987"}})
    assert (status, outcome) == (200, "pedido pagado")


def test_worker_refreshes_tokens_before_they_expire(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "MP Renovar")
    _connect(client, shop)
    with raw_conn.cursor() as cur:
        cur.execute("update mp_connections set expires_at = now() + interval '5 days' where tenant_id = %s", (shop["tenant"],))
    raw_conn.commit()
    seen: dict = {}
    assert mp_oauth.refresh_due(client=_mp(seen, token="APP_USR-nuevo", refresh="TG-2")) >= 1
    assert any(c[2].get("grant_type") == "refresh_token" and c[2].get("refresh_token") == "TG-1" for c in seen["calls"])
    assert mp_oauth.token_for(shop["tenant"]) == "APP_USR-nuevo"
    with raw_conn.cursor() as cur:
        cur.execute("update mp_connections set expires_at = now() + interval '5 days' where tenant_id = %s", (shop["tenant"],))
    raw_conn.commit()
    mp_oauth.refresh_due(client=_mp({}, status=400))
    st = client.get("/app/payments/mercadopago", headers=bearer(shop["uid"])).json()
    assert st["last_error"] and mp_oauth.token_for(shop["tenant"]) == "APP_USR-nuevo"     # sigue el vigente


def test_only_the_owner_manages_the_connection(client, accounts, raw_conn, signup):
    from test_team import _email
    shop = _shop(client, accounts, raw_conn, "MP Permisos")
    email = _email()
    client.post("/app/team/invites", headers=bearer(shop["uid"]), json={"email": email})
    staff = signup(email)
    for method, path in (("get", "/app/payments/mercadopago"), ("post", "/app/payments/mercadopago/connect"),
                         ("delete", "/app/payments/mercadopago")):
        assert getattr(client, method)(path, headers=bearer(staff)).status_code == 403


def test_state_is_single_use(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "MP Un Uso")
    url = client.post("/app/payments/mercadopago/connect", headers=bearer(shop["uid"])).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    mp_oauth.complete("CODE-1", state, _mp({}))
    with pytest.raises(mp_oauth.OAuthError):
        mp_oauth.complete("CODE-2", state, _mp({}))


def test_notification_without_hint_uses_the_mp_account_owner(client, accounts, raw_conn, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "MP Sin Pista")
    _connect(client, shop)                         # cuenta MP 555
    conv = new_conversation(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    order = orders.checkout(shop["tenant"], conv).order
    used = {}

    def handler(request: httpx.Request) -> httpx.Response:
        used["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"id": 77, "status": "approved", "external_reference": order["id"],
                                         "transaction_amount": order["total"], "currency_id": "ARS"})
    fake = httpx.Client(base_url="https://api.mp.test", transport=httpx.MockTransport(handler))
    real_init = MercadoPagoProvider.__init__
    monkeypatch.setattr(MercadoPagoProvider, "__init__", lambda self, client=None, **kw: real_init(self, client=fake, **kw))
    monkeypatch.setattr(settings, "payment_provider", "mercadopago")
    monkeypatch.setattr(settings, "mp_webhook_secret", "mp-secret")
    headers = sign_notification("mp-secret", "77", "req-2")
    status, outcome = service.receive_notification("mercadopago", headers, {"type": "payment", "data.id": "77"},
                                                   {"type": "payment", "user_id": 555, "data": {"id": "77"}})
    assert (status, outcome) == (200, "pedido pagado") and used["auth"] == "Bearer APP_USR-vendedor"


def test_reconnecting_another_account_drops_old_links(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "MP Reconectar")
    _connect(client, shop)
    conv = new_conversation(shop["tenant"])
    orders.add_item(shop["tenant"], conv, shop["item"], 1)
    order = orders.checkout(shop["tenant"], conv).order
    with raw_conn.cursor() as cur:
        cur.execute("insert into payments (tenant_id, order_id, provider, preference_id, checkout_url, amount, currency, "
                    "mp_user_id, status) values (%s, %s, 'mercadopago', 'pref-x', 'https://mp/x', %s, 'ARS', '555', 'pending')",
                    (shop["tenant"], order["id"], order["total"]))
    raw_conn.commit()
    url = client.post("/app/payments/mercadopago/connect", headers=bearer(shop["uid"])).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]

    def other(request):
        return httpx.Response(200, json={"access_token": "APP_USR-otra", "refresh_token": "TG-9", "user_id": 999})
    mp_oauth.complete("CODE", state, httpx.Client(base_url="https://api.mp.test", transport=httpx.MockTransport(other)))
    with raw_conn.cursor() as cur:
        cur.execute("select checkout_url from payments where preference_id = 'pref-x'")
        assert cur.fetchone()["checkout_url"] is None
    raw_conn.commit()


def test_refresh_keeps_account_identity_and_bad_key_is_off(client, accounts, raw_conn, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "MP Identidad")
    _connect(client, shop)
    with raw_conn.cursor() as cur:
        cur.execute("update mp_connections set expires_at = now() + interval '5 days' where tenant_id = %s", (shop["tenant"],))
    raw_conn.commit()

    def bare(request):          # una renovación que no repite usuario ni modo
        return httpx.Response(200, json={"access_token": "APP_USR-r", "refresh_token": "TG-r"})
    mp_oauth.refresh_due(client=httpx.Client(base_url="https://api.mp.test", transport=httpx.MockTransport(bare)))
    st = client.get("/app/payments/mercadopago", headers=bearer(shop["uid"])).json()
    assert st["mp_user_id"] == "555" and st["live_mode"] is True and mp_oauth.token_for(shop["tenant"]) == "APP_USR-r"
    monkeypatch.setattr(settings, "mp_token_key", "no-es-fernet")
    assert mp_oauth.enabled() is False and mp_oauth.refresh_due() == 0      # apagado, sin romper el worker


def test_expired_token_is_not_used(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "MP Vencido")
    _connect(client, shop)
    with raw_conn.cursor() as cur:
        cur.execute("update mp_connections set expires_at = now() - interval '1 day' where tenant_id = %s", (shop["tenant"],))
    raw_conn.commit()
    assert mp_oauth.token_for(shop["tenant"]) is None
    st = client.get("/app/payments/mercadopago", headers=bearer(shop["uid"])).json()
    assert st["connected"] is False and "venció" in st["last_error"]
