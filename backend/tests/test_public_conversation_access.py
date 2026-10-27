"""Chat público: cada conversación pertenece al comprador que la empezó. El servidor emite un
token al crearla y lo exige en cada lectura y escritura; conocer la UUID no alcanza. Las rutas
del sandbox no sirven de acceso alternativo a esas conversaciones."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from conftest import TENANT_C
from jwt_helpers import KEY, bearer
from test_business_setup import CSV

HDR = "X-Conversation-Token"
DEMO_SLUG = "sanitarios-demo-c"   # seed: tienda pública de la empresa demo C (la del sandbox)


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


def _store(client, accounts, name: str) -> str:
    uid, _ = accounts(name)
    client.post("/app/catalog/import", headers=bearer(uid), json={"csv": CSV})
    return client.get("/app/agent-profile", headers=bearer(uid)).json()["public_slug"]


def _start(client, slug: str, message: str = "canilla negra de cocina") -> tuple[str, str]:
    r = client.post(f"/public/{slug}/chat", json={"message": message})
    assert r.status_code == 200
    j = r.json()
    assert j["conversation_token"]
    return j["conversation_id"], j["conversation_token"]


def _say(client, slug: str, conv: str, token: str | None, message: str):
    return client.post(f"/public/{slug}/chat", json={"message": message, "conversation_id": conv},
                       headers={HDR: token} if token is not None else {})


def _read(client, slug: str, conv: str, token: str | None):
    return client.get(f"/public/{slug}/conversations/{conv}",
                      headers={HDR: token} if token is not None else {})


def test_other_buyer_of_the_same_store_cannot_read_or_write_with_the_uuid(client, accounts):
    slug = _store(client, accounts, "Tienda Compartida")
    a_conv, a_tok = _start(client, slug)
    assert _say(client, slug, a_conv, a_tok, "agregame la 1").status_code == 200
    _b_conv, b_tok = _start(client, slug)

    for token in (b_tok, None, "", "x" * 43):
        assert _read(client, slug, a_conv, token).status_code == 404
        assert _say(client, slug, a_conv, token, "comprar").status_code == 404

    a = _read(client, slug, a_conv, a_tok).json()
    assert len(a["messages"]) == 4                      # sólo los dos turnos de A
    assert len(a["cart"]["items"]) == 1 and a["orders"] == []   # B no compró sobre el carrito de A


def test_token_of_one_store_does_not_open_a_conversation_in_another(client, accounts):
    slug_x = _store(client, accounts, "Tienda X")
    slug_y = _store(client, accounts, "Tienda Y")
    conv, tok = _start(client, slug_x)
    assert _read(client, slug_y, conv, tok).status_code == 404
    assert _say(client, slug_y, conv, tok, "hola").status_code == 404
    assert _read(client, slug_x, conv, tok).status_code == 200


def test_sandbox_routes_do_not_reach_public_conversations(client):
    conv, tok = _start(client, DEMO_SLUG)
    assert client.get(f"/sandbox/sales/{conv}?company=C").status_code == 404
    r = client.post("/sandbox/sales/chat?company=C", json={"message": "agregame la 1", "conversation_id": conv})
    assert r.status_code == 404
    assert len(_read(client, DEMO_SLUG, conv, tok).json()["messages"]) == 2

    # Y al revés: una conversación del sandbox no se abre desde la tienda pública.
    sandbox_conv = client.post("/sandbox/sales/chat?company=C", json={"message": "hola"}).json()["conversation_id"]
    assert _read(client, DEMO_SLUG, sandbox_conv, tok).status_code == 404
    assert _say(client, DEMO_SLUG, sandbox_conv, tok, "hola").status_code == 404


def test_buyer_resumes_the_conversation_and_sees_the_paid_order_after_checkout(client, accounts):
    slug = _store(client, accounts, "Tienda Checkout")
    first = client.post(f"/public/{slug}/chat", json={"message": "canilla negra de cocina"}).json()
    conv, tok = first["conversation_id"], first["conversation_token"]
    later = []
    for m in ("agregame la 1", "comprar", "sí"):
        r = _say(client, slug, conv, tok, m)
        assert r.status_code == 200 and r.json()["conversation_id"] == conv
        later.append(r.json())
    pref = later[-1]["payment"]["checkout_url"].rsplit("/", 1)[1]
    assert client.post(f"/sandbox/checkout/{pref}/pay?outcome=approved").status_code == 200

    # "Recarga": sólo con la referencia guardada (UUID + token) se recupera todo.
    state = _read(client, slug, conv, tok)
    assert state.status_code == 200
    s = state.json()
    assert [o["status"] for o in s["orders"]] == ["PAID"]
    assert len(s["messages"]) >= 8

    # El token se entrega una sola vez y no aparece en trazas, respuestas ni historial.
    assert all("conversation_token" not in r or r["conversation_token"] is None for r in later)
    leaked = json.dumps([first["trace"], first["reply"], first["ui"], later, s])
    assert tok not in leaked


# --- Pedidos y oportunidades del hilo: tampoco por las rutas del sandbox ----------------------
@pytest.fixture
def linked(raw_conn):
    """Pedido PAGADO + oportunidad sintéticos de la empresa C colgados de una conversación dada
    (sin pasar por la compra, para no consumir el stock del seed). Limpia al final."""
    made: list[tuple[str, str]] = []

    def make(conversation_id: str) -> tuple[str, str]:
        with raw_conn.cursor() as cur:
            cur.execute("insert into orders (tenant_id, conversation_id, status, total) "
                        "values (%s, %s, 'PAID', 1000) returning id", (TENANT_C, conversation_id))
            oid = str(cur.fetchone()["id"])
            cur.execute("insert into opportunities (tenant_id, conversation_id, stage) "
                        "values (%s, %s, 'nueva') returning id", (TENANT_C, conversation_id))
            opp = str(cur.fetchone()["id"])
        raw_conn.commit()
        made.append((oid, opp))
        return oid, opp

    yield make
    raw_conn.rollback()
    with raw_conn.cursor() as cur:
        for oid, opp in made:
            cur.execute("delete from opportunities where id = %s", (opp,))
            cur.execute("delete from orders where id = %s", (oid,))
    raw_conn.commit()


def _row(conn, sql: str, arg: str):
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute(sql, (arg,))
        r = cur.fetchone()
    conn.commit()
    return r


def _sandbox_routes(client, oid: str, opp: str) -> dict[str, object]:
    return {
        "order": client.get(f"/sandbox/orders/{oid}?company=C").status_code,
        "advance": client.post(f"/sandbox/orders/{oid}/status?status=PREPARING&company=C").status_code,
        "listed": opp in [o["id"] for o in client.get("/sandbox/opportunities?company=C").json()],
        "activity": client.get(f"/sandbox/opportunities/{opp}/activity?company=C").status_code,
        "patch": client.patch(f"/sandbox/opportunities/{opp}?company=C", json={"stage": "seguimiento"}).status_code,
    }


@pytest.fixture
def sandbox_admin(monkeypatch):
    """Opt-in explícito de las mutaciones administrativas del sandbox (SANDBOX_ADMIN=1) en local."""
    from app.config import settings
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "sandbox_admin", True)


def _admin_routes(client, oid: str, opp: str) -> dict[str, int]:
    return {
        "advance": client.post(f"/sandbox/orders/{oid}/status?status=PREPARING&company=C").status_code,
        "patch": client.patch(f"/sandbox/opportunities/{opp}?company=C", json={"stage": "cerrada"}).status_code,
        "import": client.post("/sandbox/catalog/import?company=D", json={"items": []}).status_code,
        "expire": client.post("/sandbox/maintenance/expire-reservations").status_code,
    }


def test_sandbox_does_not_read_or_operate_orders_and_opportunities_of_public_threads(
        client, linked, raw_conn, sandbox_admin):
    conv, _tok = _start(client, DEMO_SLUG, "hola")
    oid, opp = linked(conv)
    assert _sandbox_routes(client, oid, opp) == {
        "order": 404, "advance": 404, "listed": False, "activity": 404, "patch": 404}
    assert _row(raw_conn, "select status from orders where id = %s", oid)["status"] == "PAID"
    assert _row(raw_conn, "select stage from opportunities where id = %s", opp)["stage"] == "nueva"


def test_sandbox_threads_keep_the_demo_routes_with_the_local_opt_in(client, linked, sandbox_admin):
    conv = client.post("/sandbox/sales/chat?company=C", json={"message": "hola"}).json()["conversation_id"]
    oid, opp = linked(conv)
    assert _sandbox_routes(client, oid, opp) == {
        "order": 200, "advance": 200, "listed": True, "activity": 200, "patch": 200}


def test_sandbox_admin_is_off_by_default(monkeypatch):
    from app.config import Settings
    monkeypatch.delenv("SANDBOX_ADMIN", raising=False)
    monkeypatch.setenv("APP_ENV", "local")
    assert Settings(_env_file=None).sandbox_admin_enabled is False
    assert Settings(_env_file=None, sandbox_admin=True).sandbox_admin_enabled is True
    assert Settings(_env_file=None, sandbox_admin=True, app_env="production").sandbox_admin_enabled is False


def test_sandbox_admin_mutations_are_closed_in_local_without_opt_in(client, linked, raw_conn, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "sandbox_admin", False)
    conv = client.post("/sandbox/sales/chat?company=C", json={"message": "hola"})
    assert conv.status_code == 200                                       # la demo del chat sigue
    oid, opp = linked(conv.json()["conversation_id"])
    assert _admin_routes(client, oid, opp) == {"advance": 404, "patch": 404, "import": 404, "expire": 404}
    assert _row(raw_conn, "select status from orders where id = %s", oid)["status"] == "PAID"
    assert client.get(f"/sandbox/orders/{oid}?company=C").status_code == 200   # lectura demo
    assert client.get("/sandbox/products?company=C").status_code == 200


def test_sandbox_admin_opt_in_does_not_open_mutations_outside_local(client, linked, raw_conn, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "sandbox_admin", True)
    conv = client.post("/sandbox/sales/chat?company=C", json={"message": "hola"})
    assert conv.status_code == 200
    oid, opp = linked(conv.json()["conversation_id"])
    assert _admin_routes(client, oid, opp) == {"advance": 404, "patch": 404, "import": 404, "expire": 404}
    assert _row(raw_conn, "select status from orders where id = %s", oid)["status"] == "PAID"
    assert client.get(f"/sandbox/orders/{oid}?company=C").status_code == 200
