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
