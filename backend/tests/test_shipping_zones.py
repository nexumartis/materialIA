"""Envío por zona con costo cargado por el negocio: el agente informa ese costo, nunca uno inventado."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain.agent_profile import validate_policies
from app.main import app
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_zone_costs_are_parsed():
    out = validate_policies({"delivery_zones": "CABA: 5000, GBA = $8.000, Rosario, Quilmes: 4.500,50"})
    assert out == {"delivery_zones": ["CABA", "GBA", "Rosario", "Quilmes"],
                   "shipping_costs": {"CABA": 5000.0, "GBA": 8000.0, "Quilmes": 4500.5}}
    for bad in ("CABA: gratis", "CABA: -5000", "CABA: 50 pesos"):
        with pytest.raises(ValueError, match="CABA"):
            validate_policies({"delivery_zones": bad})
    assert validate_policies({"delivery_zones": "CABA,9 de Julio: 3000"})["delivery_zones"] == ["CABA", "9 de Julio"]
    # Guardado como lista + costos (lo que devuelve el servidor) se conserva igual.
    assert validate_policies(out) == out


def test_agent_tells_the_loaded_cost_and_nothing_else(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Envíos")
    owner = bearer(shop["uid"])
    draft = {"policies": {"delivery_zones": "CABA: 5000, Rosario"}}

    def ask(text):
        r = client.post("/app/agent-preview", headers=owner, json={"message": text, "profile": draft})
        assert r.status_code == 200, r.text
        return r.json()["reply"]
    assert "CABA" in ask("¿envían a CABA?") and "$5.000" in ask("¿envían a CABA?")
    rosario = ask("¿llegan a Rosario?")
    assert "Rosario" in rosario and "$" not in rosario            # sin costo cargado: no inventa
    mendoza = ask("¿envían a Mendoza?")                           # zona no cargada: no promete ni cotiza
    assert "$" not in mendoza and not mendoza.startswith("Sí")
