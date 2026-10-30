"""Google Sheets como catálogo vivo: link validado, URL de exportación armada por el servidor,
regla de stock (sólo un cambio en la planilla pisa lo vendido) y aislamiento por negocio.
Sin red: la descarga usa un transporte HTTP falso."""
from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import catalog_sheet
from app.main import app
from jwt_helpers import KEY, bearer

SHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-xy"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=123"
HEADER = "sku;nombre;categoria;marca;precio;stock\n"


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def client():
    return TestClient(app)


class FakeGoogle:
    """Transporte HTTP falso: registra lo pedido y responde lo configurado."""

    def __init__(self):
        self.csv = HEADER + "CAN-1;Canilla negra;griferia;Marca X;89.900;5\nFLEX-1;Flexible 40 cm;repuestos;;6.800;40\n"
        self.status, self.content_type, self.redirect_to, self.requests = 200, "text/csv", None, []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        if self.redirect_to and request.url.host == "docs.google.com":
            return httpx.Response(307, headers={"location": self.redirect_to})
        return httpx.Response(self.status, headers={"content-type": self.content_type}, content=self.csv.encode())


@pytest.fixture
def google(monkeypatch):
    fake = FakeGoogle()
    real = httpx.Client
    monkeypatch.setattr(catalog_sheet.httpx, "Client",
                        lambda **kw: real(transport=httpx.MockTransport(fake.handler), **kw))
    return fake


def _stock(raw_conn, tenant, sku):
    with raw_conn.cursor() as cur:
        cur.execute("select s.on_hand, s.reserved, i.sheet_stock from catalog_items i join stock_levels s "
                    "on s.tenant_id = i.tenant_id and s.item_id = i.id where i.tenant_id = %s and i.sku = %s",
                    (tenant, sku))
        row = dict(cur.fetchone())
    raw_conn.commit()
    return row


PUB_ID = "2PACX-1vT" + "a" * 70


@pytest.mark.parametrize("url, expected", [
    (URL, (SHEET_ID, "123", False)),
    (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid=7#gid=7", (SHEET_ID, "7", False)),
    (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}", (SHEET_ID, "0", False)),
    (f"https://docs.google.com/spreadsheets/u/1/d/{SHEET_ID}/edit#gid=5", (SHEET_ID, "5", False)),   # multi-cuenta
    (f"docs.google.com/spreadsheets/d/{SHEET_ID}/edit", (SHEET_ID, "0", False)),                     # sin https://
    (f"https://docs.google.com/spreadsheets/d/e/{PUB_ID}/pub?output=csv&gid=9", (PUB_ID, "9", True)),  # publicada
])
def test_valid_links(url, expected):
    assert catalog_sheet.parse_url(url) == expected


def test_published_sheet_uses_the_publish_export():
    assert catalog_sheet.export_url(PUB_ID, "9", True) == (
        f"https://docs.google.com/spreadsheets/d/e/{PUB_ID}/pub?output=csv&gid=9&single=true")


@pytest.mark.parametrize("url", [
    "http://docs.google.com/spreadsheets/d/" + SHEET_ID,                 # sin https
    "https://evil.com/spreadsheets/d/" + SHEET_ID,                       # otro dominio
    "https://docs.google.com.evil.com/spreadsheets/d/" + SHEET_ID,
    "https://docs.google.com/document/d/" + SHEET_ID,                    # un documento, no una planilla
    "https://docs.google.com/spreadsheets/d/corto",
    URL.replace("gid=123", "gid=abc"),
    "",
])
def test_invalid_links(url):
    with pytest.raises(catalog_sheet.SheetError):
        catalog_sheet.parse_url(url)


def test_connect_imports_and_exports_only_from_google(client, accounts, raw_conn, google):
    uid, tenant = accounts("Tienda Planilla")
    owner = bearer(uid)
    r = client.put("/app/catalog/sheet", headers=owner, json={"url": URL})
    sheet = r.json()["sheet"]
    assert r.status_code == 200 and sheet["last_status"] == "ok"
    assert sheet["last_result"]["created"] == 2 and sheet["last_result"]["errors"] == []
    assert google.requests == [f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=123"]
    names = {i["sku"]: i for i in client.get("/app/catalog", headers=owner).json()}
    assert names["CAN-1"]["price"] == 89900 and names["CAN-1"]["on_hand"] == 5
    assert client.get("/app/catalog/sheet", headers=owner).json()["sheet"]["url"].endswith("#gid=123")
    assert client.put("/app/catalog/sheet", headers=owner, json={"url": "https://evil.com/x"}).status_code == 400


def test_stock_rule_keeps_sales_and_applies_owner_counts(client, accounts, raw_conn, google):
    uid, tenant = accounts("Tienda Stock")
    owner = bearer(uid)
    client.put("/app/catalog/sheet", headers=owner, json={"url": URL})
    assert _stock(raw_conn, tenant, "CAN-1") == {"on_hand": 5, "reserved": 0, "sheet_stock": 5}
    with raw_conn.cursor() as cur:   # el agente vendió 2 (descuento de stock por venta)
        cur.execute("update stock_levels s set on_hand = 3 from catalog_items i where i.id = s.item_id "
                    "and i.tenant_id = %s and i.sku = 'CAN-1'", (tenant,))
    raw_conn.commit()
    google.csv = google.csv.replace("89.900;5", "95.000;5")              # cambia el precio, no el stock
    sheet = client.post("/app/catalog/sheet/sync", headers=owner).json()["sheet"]
    assert sheet["last_status"] == "ok"
    assert _stock(raw_conn, tenant, "CAN-1")["on_hand"] == 3              # se respetó lo vendido
    assert {i["sku"]: i["price"] for i in client.get("/app/catalog", headers=owner).json()}["CAN-1"] == 95000
    google.csv = google.csv.replace("95.000;5", "95.000;12")             # el dueño contó de nuevo
    client.post("/app/catalog/sheet/sync", headers=owner)
    assert _stock(raw_conn, tenant, "CAN-1") == {"on_hand": 12, "reserved": 0, "sheet_stock": 12}
    with raw_conn.cursor() as cur:   # 4 apartadas por pedidos en curso
        cur.execute("update stock_levels s set reserved = 4 from catalog_items i where i.id = s.item_id "
                    "and i.tenant_id = %s and i.sku = 'CAN-1'", (tenant,))
    raw_conn.commit()
    google.csv = google.csv.replace("95.000;12", "99.000;2")               # stock bajo lo apartado + precio nuevo
    sheet = client.post("/app/catalog/sheet/sync", headers=owner).json()["sheet"]
    [err] = sheet["last_result"]["errors"]
    assert err["sku"] == "CAN-1" and "stock no aplicado" in err["error"] and "apartadas" in err["error"]
    assert _stock(raw_conn, tenant, "CAN-1") == {"on_hand": 12, "reserved": 4, "sheet_stock": 12}
    # El resto de la fila sí se aplicó: el precio nuevo no espera a que se liberen las reservas.
    assert {i["sku"]: i["price"] for i in client.get("/app/catalog", headers=owner).json()}["CAN-1"] == 99000


def test_products_missing_from_the_sheet_are_reported_not_paused(client, accounts, google):
    uid, _ = accounts("Tienda Faltantes")
    owner = bearer(uid)
    client.put("/app/catalog/sheet", headers=owner, json={"url": URL})
    google.csv = HEADER + "CAN-1;Canilla negra;griferia;Marca X;89.900;5\n"
    sheet = client.post("/app/catalog/sheet/sync", headers=owner).json()["sheet"]
    assert sheet["last_result"]["missing"] == {"count": 1, "skus": ["FLEX-1"]}
    assert {i["sku"]: i["active"] for i in client.get("/app/catalog", headers=owner).json()}["FLEX-1"] is True


@pytest.mark.parametrize("setup, message", [
    # Lo que hace Google con una planilla privada: redirige al login.
    (lambda g: setattr(g, "redirect_to", "https://accounts.google.com/ServiceLogin?continue=x"), "privada"),
    (lambda g: setattr(g, "content_type", "text/html; charset=utf-8"), "privada"),
    (lambda g: setattr(g, "status", 403), "compartila"),
    (lambda g: setattr(g, "redirect_to", "https://evil.example/robar"), "no permitido"),
    (lambda g: setattr(g, "csv", HEADER + "X;" * 1_100_000), "demasiado grande"),
    (lambda g: setattr(g, "csv", "columna;otra\n1;2\n"), "obligatorias"),
], ids=["privada-login", "privada-html", "403", "redireccion", "grande", "sin-columnas"])
def test_unreadable_sheets_are_reported_and_change_nothing(client, accounts, google, setup, message):
    uid, _ = accounts("Tienda Error")
    owner = bearer(uid)
    setup(google)
    sheet = client.put("/app/catalog/sheet", headers=owner, json={"url": URL}).json()["sheet"]
    assert sheet["last_status"] == "error" and message in sheet["last_error"]
    assert client.get("/app/catalog", headers=owner).json() == []


def test_redirect_to_googleusercontent_is_allowed(client, accounts, google):
    uid, _ = accounts("Tienda Redirect")
    google.redirect_to = "https://doc-0s-1c-sheets.googleusercontent.com/export/abc"
    sheet = client.put("/app/catalog/sheet", headers=bearer(uid), json={"url": URL}).json()["sheet"]
    assert sheet["last_status"] == "ok" and sheet["last_result"]["created"] == 2


def test_isolation_and_disconnect(client, accounts, raw_conn, google):
    uid_a, _ = accounts("Tienda A")
    uid_b, _ = accounts("Tienda B")
    client.put("/app/catalog/sheet", headers=bearer(uid_a), json={"url": URL})
    assert client.get("/app/catalog/sheet", headers=bearer(uid_b)).json() == {"sheet": None}
    assert client.post("/app/catalog/sheet/sync", headers=bearer(uid_b)).status_code == 404
    assert client.delete("/app/catalog/sheet", headers=bearer(uid_b)).json() == {"disconnected": False}
    assert client.delete("/app/catalog/sheet", headers=bearer(uid_a)).json() == {"disconnected": True}
    assert client.get("/app/catalog/sheet", headers=bearer(uid_a)).json() == {"sheet": None}
    with raw_conn.cursor() as cur:
        cur.execute("delete from memberships where user_id = %s", (uid_a,))
    raw_conn.commit()
    assert client.get("/app/catalog/sheet", headers=bearer(uid_a)).status_code == 403


def test_worker_syncs_due_sheets_and_one_failure_does_not_stop_others(client, accounts, raw_conn, google, monkeypatch):
    uid_a, tenant_a = accounts("Tienda Worker A")
    uid_b, tenant_b = accounts("Tienda Worker B")
    for uid in (uid_a, uid_b):
        client.put("/app/catalog/sheet", headers=bearer(uid), json={"url": URL})
    with raw_conn.cursor() as cur:   # pasaron más de 15 minutos
        cur.execute("update catalog_sources set last_synced_at = now() - interval '1 hour' "
                    "where tenant_id = any(%s)", ([tenant_a, tenant_b],))
    raw_conn.commit()
    real_sync = catalog_sheet.sync

    def flaky(tenant_id):
        if tenant_id == tenant_a:
            raise RuntimeError("se cayó")
        return real_sync(tenant_id)
    monkeypatch.setattr(catalog_sheet, "sync", flaky)
    google.csv = google.csv.replace("89.900;5", "70.000;5")
    assert catalog_sheet.sync_due() >= 2
    prices = {i["sku"]: i["price"] for i in client.get("/app/catalog", headers=bearer(uid_b)).json()}
    assert prices["CAN-1"] == 70000
    with raw_conn.cursor() as cur:   # las dos quedaron marcadas como leídas recién: no vencen de nuevo
        cur.execute("select count(*) n from catalog_sources where tenant_id = any(%s) "
                    "and last_synced_at > now() - interval '1 minute'", ([tenant_a, tenant_b],))
        assert cur.fetchone()["n"] == 2
    raw_conn.commit()


@pytest.mark.parametrize("cell", ["1e999", "99999999999", "nan"])
def test_a_bad_cell_is_an_error_of_its_row_only(client, accounts, google, cell):
    uid, _ = accounts("Tienda Celda")
    google.csv = HEADER + f"CAN-1;Canilla negra;griferia;;89.900;{cell}\nFLEX-1;Flexible;repuestos;;6.800;40\n"
    sheet = client.put("/app/catalog/sheet", headers=bearer(uid), json={"url": URL}).json()["sheet"]
    assert sheet["last_status"] == "ok"
    assert [e["sku"] for e in sheet["last_result"]["errors"]] == ["CAN-1"]
    assert [i["sku"] for i in client.get("/app/catalog", headers=bearer(uid)).json()] == ["FLEX-1"]


def test_unexpected_failure_is_recorded_not_left_pending(client, accounts, google, monkeypatch):
    uid, _ = accounts("Tienda Rota")

    def boom(*_, **__):
        raise RuntimeError("bug")
    monkeypatch.setattr(catalog_sheet.backoffice, "import_csv", boom)
    sheet = client.put("/app/catalog/sheet", headers=bearer(uid), json={"url": URL}).json()["sheet"]
    assert sheet["last_status"] == "error" and "formato" in sheet["last_error"]


def test_reconnecting_makes_the_sheet_the_stock_source_again(client, accounts, raw_conn, google):
    uid, tenant = accounts("Tienda Reconecta")
    owner = bearer(uid)
    client.put("/app/catalog/sheet", headers=owner, json={"url": URL})            # planilla dice 5
    client.patch(f"/app/catalog/{_item_id(raw_conn, tenant, 'CAN-1')}", headers=owner, json={"stock": 50})
    client.post("/app/catalog/sheet/sync", headers=owner)
    assert _stock(raw_conn, tenant, "CAN-1")["on_hand"] == 50                      # la planilla no cambió: manda el panel
    client.put("/app/catalog/sheet", headers=owner, json={"url": URL})            # reconectar = fuente otra vez
    assert _stock(raw_conn, tenant, "CAN-1") == {"on_hand": 5, "reserved": 0, "sheet_stock": 5}


def test_sync_with_changes_is_audited(client, accounts, raw_conn, google):
    uid, tenant = accounts("Tienda Auditada")
    client.put("/app/catalog/sheet", headers=bearer(uid), json={"url": URL})
    client.post("/app/catalog/sheet/sync", headers=bearer(uid))                   # sin cambios: no audita
    with raw_conn.cursor() as cur:
        cur.execute("select metadata_redacted m from audit_events where tenant_id = %s and event_type = "
                    "'catalog_sheet_synced'", (tenant,))
        rows = [r["m"] for r in cur.fetchall()]
    raw_conn.commit()
    assert rows == [{"created": 2, "prices": 2, "stock": 2, "errors": 0}]


def test_worker_stops_claiming_after_its_budget(client, accounts, raw_conn, google):
    tenants = []
    for name in ("Tienda Presupuesto A", "Tienda Presupuesto B"):
        uid, tenant = accounts(name)
        client.put("/app/catalog/sheet", headers=bearer(uid), json={"url": URL})
        tenants.append(tenant)
    with raw_conn.cursor() as cur:
        cur.execute("update catalog_sources set last_synced_at = now() - interval '1 hour' where tenant_id = any(%s)",
                    (tenants,))
    raw_conn.commit()
    assert catalog_sheet.sync_due(budget_s=0) == 1                                 # al menos una, no más
    assert catalog_sheet.sync_due() >= 1


def _item_id(raw_conn, tenant, sku):
    with raw_conn.cursor() as cur:
        cur.execute("select id from catalog_items where tenant_id = %s and sku = %s", (tenant, sku))
        item = str(cur.fetchone()["id"])
    raw_conn.commit()
    return item
