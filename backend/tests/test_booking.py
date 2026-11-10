"""Turnos: configuración (servicios, días y horarios, cupo), horarios libres que respetan el cupo,
reserva desde el chat eligiendo el número, el último lugar no se da dos veces, cancelación en el panel
y aislamiento entre negocios."""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import booking
from app.domain.agent_profile import validate_policies
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop

CFG = {"services": "Medición a domicilio: 60, Retiro: 30", "hours": "lun-vie 9-12; sab 9-10", "capacity": 1}


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_config_parsing_and_errors():
    out = validate_policies({"booking": CFG})["booking"]
    assert out["services"] == [{"name": "Medición a domicilio", "minutes": 60}, {"name": "Retiro", "minutes": 30}]
    assert out["hours"]["0"] == [["09:00", "12:00"]] and out["hours"]["5"] == [["09:00", "10:00"]] and "6" not in out["hours"]
    assert validate_policies(validate_policies({"booking": CFG})) == validate_policies({"booking": CFG})
    for bad in ({**CFG, "hours": "lunes a viernes"}, {**CFG, "hours": "lun 18-9"}, {**CFG, "services": "X: 5"},
                {**CFG, "capacity": 0}, {**CFG, "services": ["Medición"]}, {**CFG, "services": [None]}):
        with pytest.raises(ValueError):
            validate_policies({"booking": bad})


def test_free_slots_respect_capacity_and_lead(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Turnos 1")
    cfg = booking.validate(CFG)
    monday = datetime(2026, 11, 9, 8, 0, tzinfo=booking.TZ)           # lunes 8:00
    with booking.opportunities.tenant_tx(shop["tenant"]) as cur:
        slots = booking.free_slots(cur, shop["tenant"], cfg, cfg["services"][0], now=monday)
        assert [s.strftime("%a %H:%M") for s in slots[:2]] == ["Mon 10:00", "Mon 11:00"]   # 9:00 queda < 2 h
    with booking.opportunities.tenant_tx(shop["tenant"]) as cur:
        assert "id" in booking.book(cur, shop["tenant"], None, cfg, cfg["services"][0], slots[0], now=monday)
    with booking.opportunities.tenant_tx(shop["tenant"]) as cur:
        assert booking.book(cur, shop["tenant"], None, cfg, cfg["services"][0], slots[0], now=monday) == {"error": "full"}   # cupo 1
        again = booking.free_slots(cur, shop["tenant"], cfg, cfg["services"][0], now=monday)
        assert slots[0] not in again


def test_chat_books_and_panel_cancels(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Turnos 2")
    h = bearer(shop["uid"])
    profile = client.get("/app/agent-profile", headers=h).json()
    profile["policies"] = {"booking": {**CFG, "hours": "lun-dom 0-23"}}
    assert client.put("/app/agent-profile", headers=h, json=profile).status_code == 200
    j, conv, tok = _say(client, shop, "quiero sacar un turno")
    assert "¿Para qué es el turno?" in j["reply"]
    j, _, _ = _say(client, shop, "para la medicion", conv, tok)
    assert "Turnos libres para Medición a domicilio" in j["reply"] and "1. " in j["reply"]
    j, _, _ = _say(client, shop, "el 2", conv, tok)
    assert j["reply"].startswith("¡Listo! Te reservé Medición a domicilio")
    appts = client.get("/app/appointments", headers=h).json()
    assert len(appts) == 1 and appts[0]["conversation_id"] == conv
    other, _ = accounts("Otra Turnos")
    assert client.get("/app/appointments", headers=bearer(other)).json() == []
    assert client.post(f"/app/appointments/{appts[0]['id']}/cancel", headers=bearer(other)).status_code == 404
    assert client.post(f"/app/appointments/{appts[0]['id']}/cancel", headers=h).status_code == 200
    assert client.get("/app/appointments", headers=h).json() == []
