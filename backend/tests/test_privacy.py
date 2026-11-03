"""Privacidad: una tarjeta nunca se guarda ni llega a la IA; el equipo oculta DNI/CUIT/CBU/tarjetas
de una conversación; bloquear un contacto pausa el agente (y al mismo cliente recordado)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.domain import privacy
from app.main import app
from jwt_helpers import KEY, bearer
from test_inbox import HDR, _say
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_patterns():
    assert privacy.mask_cards("4111 1111 1111 1111") == "•••• 1111"
    assert privacy.mask_cards("4111 1111 1111 1112") == "4111 1111 1111 1112"      # no pasa Luhn
    out = privacy.redact("DNI 30.123.456 cbu 0170099220000067797370 cuit 20-30123456-7 total 1.250.000")
    assert "30.123.456" not in out and "0170099220000067797370" not in out and "20-30123456-7" not in out
    assert "1.250.000" in out


def test_card_never_stored_and_redact(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Privacidad")
    _, conv, tok = _say(client, shop, "te paso mi tarjeta 4111111111111111 y mi DNI 30.123.456")
    with raw_conn.cursor() as cur:
        cur.execute("select string_agg(content, ' ') as t from messages where conversation_id = %s", (conv,))
        stored = cur.fetchone()["t"]
    raw_conn.commit()
    assert "4111111111111111" not in stored and "•••• 1111" in stored and "30.123.456" in stored
    h = bearer(shop["uid"])
    r = client.post(f"/app/inbox/{conv}/redact", headers=h)
    assert r.status_code == 200 and r.json()["changed"] >= 1 and r.json()["conversation"]["redacted_at"]
    assert "30.123.456" not in str(r.json()["conversation"]["messages"])
    other, _ = accounts("Otro Privacidad")
    assert client.post(f"/app/inbox/{conv}/redact", headers=bearer(other)).status_code == 404


def test_block_pauses_agent_and_unblock(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Bloqueo")
    _, conv, tok = _say(client, shop, "hola")
    h = bearer(shop["uid"])
    assert client.post(f"/app/inbox/{conv}/block", headers=h).json()["blocked"] is True
    r = client.post(f"/public/{shop['slug']}/chat", json={"message": "hola?", "conversation_id": conv},
                    headers={HDR: tok})
    assert r.status_code == 403 and "pausó" in r.json()["detail"]
    other, _ = accounts("Otro Bloqueo")
    assert client.post(f"/app/inbox/{conv}/block", headers=bearer(other)).status_code == 404
    assert client.post(f"/app/inbox/{conv}/block", headers=h, json={"blocked": False}).json()["blocked"] is False
    assert client.post(f"/public/{shop['slug']}/chat", json={"message": "hola", "conversation_id": conv},
                       headers={HDR: tok}).status_code == 200


def test_unblock_from_another_conversation_of_same_customer(accounts, raw_conn):
    client = TestClient(app)
    shop = _shop(client, accounts, raw_conn, "Tienda Bloqueo Cliente")
    key = {"X-Buyer-Key": "k" * 32}
    r1 = client.post(f"/public/{shop['slug']}/chat", json={"message": "hola"}, headers=key).json()
    r2 = client.post(f"/public/{shop['slug']}/chat", json={"message": "hola de nuevo"}, headers=key).json()
    h = bearer(shop["uid"])
    client.post(f"/app/inbox/{r1['conversation_id']}/block", headers=h)
    assert client.get(f"/app/inbox/{r2['conversation_id']}", headers=h).json()["blocked"] is True   # mismo cliente
    client.post(f"/app/inbox/{r2['conversation_id']}/block", headers=h, json={"blocked": False})
    r = client.post(f"/public/{shop['slug']}/chat", json={"message": "sigo?", "conversation_id": r1["conversation_id"]},
                    headers={HDR: r1["conversation_token"], **key})
    assert r.status_code == 200
