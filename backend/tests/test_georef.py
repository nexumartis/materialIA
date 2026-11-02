"""Georef: «Bernal» entra en una zona cargada como «Quilmes» o «Zona Sur». Sin red: la API se simula.
Nunca inventa zonas: si no coincide, si es ambiguo o si Georef no responde, no promete envío."""
from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.domain import georef
from app.main import app
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop

PLACES = {
    "bernal": [("Bernal", "Quilmes", "Quilmes", "Buenos Aires"), ("Bernal Oeste", "Quilmes", "Quilmes", "Buenos Aires"),
               ("Berna", "Berna", "General Obligado", "Santa Fe")],
    "ramos mejia": [("Ramos Mejía", "La Matanza", "La Matanza", "Buenos Aires")],
    "san martin": [("San Martín", "General San Martín", "General San Martín", "Buenos Aires"),
                   ("San Martín", "San Martín", "General San Martín", "Mendoza")],
    "villa crespo": [("Villa Crespo", "", "Comuna 15", "Ciudad Autónoma de Buenos Aires")],
}


@pytest.fixture(autouse=True)
def _fake_georef(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    monkeypatch.setattr(settings, "georef_url", "https://georef.test")
    georef._cache.clear()
    calls = []

    def fake(name):
        calls.append(name)
        if name == "caida":
            raise httpx.ConnectTimeout("sin red")
        return [{"localidad": a, "municipio": b, "departamento": c, "provincia": d} for a, b, c, d in PLACES.get(name, [])]
    monkeypatch.setattr(georef, "_fetch", fake)
    return calls


def test_match_zone_by_partido_gba_zone_and_caba(_fake_georef):
    assert georef.match_zone("Bernal", ["CABA", "Quilmes"])[0] == "Quilmes"
    assert georef.match_zone("bernal", ["Zona Sur"])[0] == "Zona Sur"          # Berna (Santa Fe) se filtra
    assert georef.match_zone("Ramos Mejía", ["Zona Oeste", "Zona Sur"])[0] == "Zona Oeste"
    assert georef.match_zone("Villa Crespo", ["Capital Federal"])[0] == "Capital Federal"
    assert georef.match_zone("Ramos Mejía", ["Zona Norte"])[0] is None
    assert georef.match_zone("San Martín", ["Mendoza"])[0] is None              # homónimos en zonas distintas
    assert georef.match_zone("caida", ["Quilmes"]) == (None, [])                # sin respuesta: no promete
    georef.match_zone("Bernal", ["Quilmes"])
    assert _fake_georef.count("bernal") == 1                                    # cacheado


def test_agent_answers_with_georef(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Georef")
    draft = {"policies": {"delivery_zones": "Quilmes: 4000, Zona Oeste"}}

    def ask(text):
        r = client.post("/app/agent-preview", headers=bearer(shop["uid"]), json={"message": text, "profile": draft})
        assert r.status_code == 200, r.text
        return r.json()["reply"]
    bernal = ask("¿envían a Bernal?")
    assert bernal.startswith("Sí") and "Quilmes" in bernal and "$4.000" in bernal
    assert ask("¿llegan a Ramos Mejía?").startswith("Sí")
    sm = ask("¿envían a San Martín?")
    assert "¿Cuál es la tuya?" in sm and "Mendoza" in sm
    assert not ask("¿envían a Villa Crespo?").startswith("Sí")
