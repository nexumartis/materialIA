"""Chat embebible: el dueño configura el botón; el script lo lee en vivo desde cualquier sitio (CORS
abierto, sólo datos públicos); se registra sólo el dominio donde se instaló, con tope; otro negocio no
ve ni cambia nada."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import widget
from app.main import app
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


def test_owner_configures_and_script_reads_it_live(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Widget Config")
    h = bearer(shop["uid"])
    panel = client.get("/app/widget", headers=h).json()
    assert panel["slug"] == shop["slug"] and f'data-tienda="{shop["slug"]}"' in panel["snippet"]
    assert panel["config"] == widget.DEFAULTS and panel["installs"] == []
    new = {"color": "#FF5500", "label": "Consultanos", "position": "left", "greeting": "¿Buscás algo?", "greeting_delay_s": 5}
    saved = client.put("/app/widget", headers=h, json=new).json()
    assert saved["config"]["color"] == "#ff5500" and saved["snippet"] == panel["snippet"]   # el código no cambia
    pub = client.get(f"/public/{shop['slug']}/widget", headers={"Origin": "https://otra-web.com"})
    assert pub.status_code == 200 and pub.headers["access-control-allow-origin"] == "*"
    body = pub.json()
    assert body["label"] == "Consultanos" and body["store_url"].endswith(f"#/tienda/{shop['slug']}")
    assert set(body) == {"color", "label", "position", "greeting", "greeting_delay_s", "store_url"}
    js = client.get("/widget.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"] and "data-tienda" in js.text


def test_validation(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Widget Validación")
    h = bearer(shop["uid"])
    for bad in ({"color": "red"}, {"label": ""}, {"label": "x" * 41}, {"position": "top"},
                {"greeting": "x" * 141}, {"greeting_delay_s": 999}, {"greeting_delay_s": "ya"}):
        assert client.put("/app/widget", headers=h, json=bad).status_code == 400, bad


def test_seen_records_only_the_host_with_cap(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Widget Instalado")
    url = f"/public/{shop['slug']}/widget/seen"
    assert client.post(url, content='{"page":"https://www.mitienda.com.ar"}', headers={"Content-Type": "text/plain"}).status_code == 204
    client.post(url, content='{"page":"https://www.mitienda.com.ar"}')       # repetido: no suma (cada 10 min)
    for bad in ('{"page":"javascript:alert(1)"}', '{"page":"https://<b>x</b>"}', "no-json", '{"page": 5}'):
        assert client.post(url, content=bad).status_code == 204
    installs = client.get("/app/widget", headers=bearer(shop["uid"])).json()["installs"]
    assert [(i["host"], i["hits"]) for i in installs] == [("mitienda.com.ar", 1)]
    for n in range(widget.MAX_HOSTS + 5):
        widget.seen(shop["tenant"], f"https://sitio{n}.com")
    with raw_conn.cursor() as cur:
        cur.execute("select count(*) as n from widget_installs where tenant_id = %s", (shop["tenant"],))
        assert cur.fetchone()["n"] == widget.MAX_HOSTS
    raw_conn.commit()


def test_unknown_store_and_other_business(client, accounts, raw_conn):
    a = _shop(client, accounts, raw_conn, "Widget A")
    b = _shop(client, accounts, raw_conn, "Widget B")
    assert client.get("/public/no-existe-tienda/widget").status_code == 404
    client.put("/app/widget", headers=bearer(a["uid"]), json={"label": "Sólo A"})
    assert client.get("/app/widget", headers=bearer(b["uid"])).json()["config"]["label"] == widget.DEFAULTS["label"]
    assert client.get(f"/public/{b['slug']}/widget").json()["label"] == widget.DEFAULTS["label"]
