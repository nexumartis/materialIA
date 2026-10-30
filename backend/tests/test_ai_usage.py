"""Uso de IA por negocio: se cuenta por negocio y tarea, se aísla por negocio y el costo sólo
aparece con precio configurado."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.domain import ai_usage
from app.main import app
from jwt_helpers import KEY, bearer


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def test_usage_is_recorded_per_business_and_cost_needs_a_price(accounts, monkeypatch):
    client = TestClient(app)
    uid_a, tenant_a = accounts("Tienda IA A")
    uid_b, _ = accounts("Tienda IA B")
    ai_usage.record("m", {"prompt_eval_count": 100, "eval_count": 10})          # sin contexto: no cuenta
    with ai_usage.for_tenant(tenant_a, "venta"):
        ai_usage.record("m", {"prompt_eval_count": 1000, "eval_count": 200})
        ai_usage.record("m", {"prompt_eval_count": 500, "eval_count": 100})
    with ai_usage.for_tenant(tenant_a, "memoria"):
        ai_usage.record("m", {"prompt_eval_count": 300})
    a = client.get("/app/ai-usage", headers=bearer(uid_a)).json()
    assert a["calls"] == 3 and a["prompt_tokens"] == 1800 and a["completion_tokens"] == 300
    assert {r["kind"]: r["calls"] for r in a["by_kind"]} == {"memoria": 1, "venta": 2}
    assert a["cost"] is None                                                      # sin precio: no inventa
    assert client.get("/app/ai-usage", headers=bearer(uid_b)).json()["calls"] == 0
    monkeypatch.setattr(settings, "llm_price_in_per_mtok", 1.0)
    monkeypatch.setattr(settings, "llm_price_out_per_mtok", 4.0)
    assert client.get("/app/ai-usage", headers=bearer(uid_a)).json()["cost"] == round((1800 * 1 + 300 * 4) / 1e6, 4)
