"""Agente multirubro sin IA (modo reglas): ropa con colores y talles, comida con sabores. Los
atributos salen del catálogo del negocio, no de una lista de ferretería."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import agent_profile
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import _say

ROPA = """sku;nombre;categoria;precio;stock;color;talle
REM-R-M;Remera básica;remeras;15000;5;Roja;M
REM-R-L;Remera básica;remeras;15000;2;Roja;L
REM-A-M;Remera básica;remeras;15000;4;Azul;M
JEA-1;Jean recto;pantalones;45000;3;Azul;42
"""
COMIDA = """sku;nombre;categoria;precio;stock;sabor
ALF-DDL;Alfajor de maicena;alfajores;1200;40;dulce de leche
ALF-CHO;Alfajor triple;alfajores;1800;0;chocolate
TOR-1;Torta brownie;tortas;22000;2;chocolate
"""


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def _shop(accounts, csv, name):
    client = TestClient(app)
    uid, tenant = accounts(name)
    r = client.post("/app/catalog/import", headers=bearer(uid), json={"csv": csv})
    assert r.status_code == 200 and not r.json()["errors"], r.text
    slug = client.get("/app/agent-profile", headers=bearer(uid)).json()["public_slug"]
    return client, {"uid": uid, "tenant": tenant, "slug": slug}


def _lines(j):
    return [ln for ln in j["reply"].splitlines() if ln[:1].isdigit()]


def test_clothing_color_forms_and_size(accounts):
    client, s = _shop(accounts, ROPA, "Ropa Multirubro")
    j, conv, tok = _say(client, s, "tenés remeras rojas?")
    lines = _lines(j)                                                     # «rojas» encuentra «Roja»
    assert len(lines) == 2 and all("Remera básica (Roja, talle" in ln for ln in lines)
    assert "¿Qué talle buscás? Hay L, M." in j["reply"]
    j, _, _ = _say(client, s, "talle m", conv, tok)                      # corrige sólo el talle
    assert [ln.split(" · ")[0] for ln in _lines(j)] == ["1. Remera básica (Roja, talle M)"]
    j, _, _ = _say(client, s, "jean azul talle 42")
    assert [ln.split(" · ")[0] for ln in _lines(j)] == ["1. Jean recto (Azul, talle 42)"]


def test_food_flavor_and_stock(accounts):
    client, s = _shop(accounts, COMIDA, "Comida Multirubro")
    j, _, _ = _say(client, s, "tenés algo de chocolate?")
    assert "Torta brownie" in j["reply"] and "maicena" not in j["reply"]


def test_templates_for_other_rubros():
    assert {"ropa", "gastronomia"} <= set(agent_profile.TEMPLATES)
