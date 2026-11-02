"""Variantes: cada una es un producto (precio y stock propios) agrupado por modelo; la tarjeta
del chat ofrece las otras variantes del modelo."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from jwt_helpers import KEY, bearer

CSV = ("sku;nombre;categoria;precio;stock;modelo;variante\n"
       "AQ-NEG;Canilla Aquaflux negra mate;griferia;89.900;3;Canilla Aquaflux;Negro mate\n"
       "AQ-CRO;Canilla Aquaflux cromo;griferia;68.000;10;Canilla Aquaflux;Cromo\n"
       "AQ-BLA;Canilla Aquaflux blanca;griferia;70.000;0;Canilla Aquaflux;Blanco\n")


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_cards_offer_the_other_variants_of_the_model(accounts):
    client = TestClient(app)
    uid, _ = accounts("Tienda Variantes")
    owner = bearer(uid)
    assert client.post("/app/catalog/import", headers=owner, json={"csv": CSV}).json()["errors"] == []
    items = {i["sku"]: i for i in client.get("/app/catalog", headers=owner).json()}
    assert items["AQ-NEG"]["variant_group"] == "Canilla Aquaflux" and items["AQ-NEG"]["variant_label"] == "Negro mate"
    slug = client.get("/app/agent-profile", headers=owner).json()["public_slug"]
    r = client.post(f"/public/{slug}/chat", json={"message": "canilla"}).json()
    assert "products" in r["ui"], r["reply"]
    cards = r["ui"]["products"]
    neg = next(c for c in cards if c["name"] == "Canilla Aquaflux negra mate")
    shown = {c["name"] for c in cards}
    others = {v["label"] for v in neg["variants"]}
    assert neg["variant_label"] == "Negro mate" and "Negro mate" not in others
    assert others == {lbl for name, lbl in [("Canilla Aquaflux cromo", "Cromo"), ("Canilla Aquaflux blanca", "Blanco")]
                      if name not in shown}
    # Quitar la columna «modelo» de la celda la borra; sin la columna, se conserva.
    client.post("/app/catalog/import", headers=owner, json={"csv": "sku;nombre;precio;modelo\nAQ-NEG;Canilla Aquaflux negra mate;89.900;\n"})
    client.post("/app/catalog/import", headers=owner, json={"csv": "sku;nombre;precio\nAQ-CRO;Canilla Aquaflux cromo;68.000\n"})
    items = {i["sku"]: i for i in client.get("/app/catalog", headers=owner).json()}
    assert items["AQ-NEG"]["variant_group"] is None and items["AQ-CRO"]["variant_group"] == "Canilla Aquaflux"


def test_search_by_model_and_color_and_variant_substitutes(accounts):
    client = TestClient(app)
    uid, _ = accounts("Tienda Búsqueda")
    owner = bearer(uid)
    client.post("/app/catalog/import", headers=owner, json={"csv": CSV + "OTRA-1;Canilla genérica cromo;griferia;50.000;8;;\n"})
    slug = client.get("/app/agent-profile", headers=owner).json()["public_slug"]
    r = client.post(f"/public/{slug}/chat", json={"message": "canilla aquaflux negra"}).json()
    names = [c["name"] for c in r["ui"].get("products", [])]
    assert names == ["Canilla Aquaflux negra mate"], r["reply"]                    # color sin ficha: por nombre
    r = client.post(f"/public/{slug}/chat", json={"message": "canilla aquaflux blanca"}).json()
    alts = [c["name"] for c in r["ui"].get("products", [])]
    assert "sin stock" in r["reply"] and alts and alts[0].startswith("Canilla Aquaflux"), r["reply"]   # variante primero


def test_color_fallback_matches_whole_words_only(accounts, raw_conn):
    from app.domain import inventory
    client = TestClient(app)
    uid, tenant = accounts("Tienda Colores")
    client.post("/app/catalog/import", headers=bearer(uid),
                json={"csv": "sku;nombre;categoria;precio;stock\nINO-1;Inodoro largo;sanitarios;1.000;5\n"
                              "GRI-1;Grifería dorada;griferia;2.000;5\n"})
    names = lambda color: [o["name"] for o in inventory.offers(tenant, color=color)]
    assert names("oro") == []                       # «oro» no es parte de «inodoro»
    assert names("dorado") == ["Grifería dorada"]
    assert names("%") == [] and names("_") == []
