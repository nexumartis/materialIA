"""Temas de derivación configurables: «reclamo» o «cambio» van siempre a una persona, con el mensaje
del negocio; quedan en la bandeja como derivadas. Validación de los temas."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain.agent_profile import validate_policies
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_parse_and_limits():
    out = validate_policies({"handoff_topics": "reclamo, no funciona => Lamento lo que pasó.\n\ncambio, devolución"})
    assert out["handoff_topics"] == [{"keywords": ["reclamo", "no funciona"], "reply": "Lamento lo que pasó."},
                                     {"keywords": ["cambio", "devolución"], "reply": None}]
    assert validate_policies(out) == out
    with pytest.raises(ValueError):
        validate_policies({"handoff_topics": "x => " + "y" * 301})
    with pytest.raises(ValueError):
        validate_policies({"handoff_topics": "\n".join(f"tema{i}" for i in range(11))})


def test_topic_goes_to_person_with_business_message(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Temas")
    h = bearer(shop["uid"])
    profile = client.get("/app/agent-profile", headers=h).json()
    profile["policies"] = {"handoff_topics": "reclamo, no funciona => Lamento lo que pasó, lo vemos enseguida."}
    assert client.put("/app/agent-profile", headers=h, json=profile).status_code == 200
    j, conv, _ = _say(client, shop, "hola, la canilla que compré NO FUNCIONA")
    assert j["reply"].startswith("Lamento lo que pasó") and j["requires_human"]
    d = client.get(f"/app/inbox/{conv}", headers=h).json()
    assert d["needs_human"]
    j, _, _ = _say(client, shop, "quiero una canilla")                  # sin tema: sigue el agente
    assert not j["requires_human"]


def test_repeat_punctuation_and_reason(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Temas 2")
    h = bearer(shop["uid"])
    profile = client.get("/app/agent-profile", headers=h).json()
    profile["policies"] = {"handoff_topics": "¿garantía? => Lo ve el equipo de garantías."}
    client.put("/app/agent-profile", headers=h, json=profile)
    j, conv, tok = _say(client, shop, "esto tiene garantía?")
    assert j["reply"].startswith("Lo ve el equipo de garantías")
    j, _, _ = _say(client, shop, "y la garantía cuánto dura", conv, tok)
    assert "ya está en la bandeja" in j["reply"]                  # no re-deriva ni repite
    items = client.get("/app/inbox?filter=derivadas", headers=h).json()
    assert next(i for i in items if i["id"] == conv)["needs_human_reason"] == "topic"
