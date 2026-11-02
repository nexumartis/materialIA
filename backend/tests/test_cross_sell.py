"""Venta cruzada genérica (acá, una tienda de ropa): al agregar un producto el agente ofrece UN
complemento cargado por el negocio, con stock y precio; «sí» lo agrega. No sugiere lo que no hay,
lo que ya está en el carrito ni lo que el negocio no cargó; como mucho dos veces por conversación."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import _say

CSV = """sku;nombre;categoria;precio;stock;complementos
REM-1;Remera lisa algodón;remeras;15000;10;MED-1, PAN-1
PAN-1;Pantalón cargo;pantalones;42000;3;CIN-1
MED-1;Medias deportivas;medias;3000;0;
CIN-1;Cinturón de cuero;accesorios;12000;5;
BUZ-1;Buzo frisa;buzos;38000;4;NOEXISTE
"""


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


@pytest.fixture
def shop(accounts):
    client = TestClient(app)
    uid, tenant = accounts("Ropa Cruzada")
    r = client.post("/app/catalog/import", headers=bearer(uid), json={"csv": CSV})
    assert r.status_code == 200 and not r.json()["errors"], r.text
    slug = client.get("/app/agent-profile", headers=bearer(uid)).json()["public_slug"]
    return client, {"uid": uid, "tenant": tenant, "slug": slug}


def _cart(j):
    return sorted(f"{i['qty']} {i['name']}" for i in (j.get("cart") or {}).get("items", []))


def test_offers_complement_with_stock_and_yes_adds_it(shop):
    client, s = shop
    j, conv, tok = _say(client, s, "agregame la remera lisa")
    assert _cart(j) == ["1 Remera lisa algodón"]
    # Medias sin stock se saltean; ofrece el pantalón (con su precio, cargado por el negocio).
    assert "Pantalón cargo a $42.000" in j["reply"] and "Medias" not in j["reply"]
    j, _, _ = _say(client, s, "sí", conv, tok)
    assert _cart(j) == ["1 Pantalón cargo", "1 Remera lisa algodón"]
    # Segunda (y última) sugerencia: el complemento del pantalón.
    assert "Cinturón de cuero" in j["reply"]


def test_no_suggestion_without_valid_complement(shop):
    client, s = shop
    j, conv, tok = _say(client, s, "agregame el buzo frisa")
    assert _cart(j) == ["1 Buzo frisa"] and "Suele llevarse" not in j["reply"]


def test_column_absent_keeps_complements(shop):
    client, s = shop
    r = client.post("/app/catalog/import", headers=bearer(s["uid"]),
                    json={"csv": "sku;nombre;categoria;precio;stock\nREM-1;Remera lisa algodón;remeras;16000;10\n"})
    assert r.status_code == 200
    j, _, _ = _say(client, s, "agregame la remera lisa")
    assert "Pantalón cargo" in j["reply"]
