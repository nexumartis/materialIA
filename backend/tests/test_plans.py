"""Cupo mensual de IA por plan: cada negocio gasta lo suyo; pasado el cupo el agente sigue SIN IA (la
venta no se corta) hasta el mes siguiente; otro negocio no se ve afectado; el dueño ve su uso."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.db import tenant_tx
from app.domain import limits, plans
from app.main import app
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    limits._allowed_cache.clear()
    yield
    limits._allowed_cache.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _use(raw_conn, tenant, calls):
    with raw_conn.cursor() as cur:
        cur.execute("insert into llm_usage (tenant_id, day, kind, model, calls, prompt_tokens, completion_tokens) "
                    "values (%s, (now() at time zone 'America/Argentina/Buenos_Aires')::date, 'venta', 'm', %s, 0, 0) "
                    "on conflict (tenant_id, day, kind, model) do update set calls = excluded.calls", (tenant, calls))
    raw_conn.commit()


def test_default_plan_and_owner_sees_usage(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Plan Uso")
    _use(raw_conn, shop["tenant"], 400)
    p = client.get("/app/ai-usage", headers=bearer(shop["uid"])).json()["plan"]
    assert p["plan"] == "vendedor" and p["ai_calls_month"] == plans.PLANS["vendedor"]["ai_calls_month"]
    assert p["used_month"] == 400 and p["percent"] == 5 and p["over"] is False and p["renews_on"].endswith("-01")


def test_monthly_cap_turns_ai_off_only_for_that_business(client, accounts, raw_conn, monkeypatch):
    monkeypatch.setattr(limits.settings, "ai_daily_calls_per_tenant", 0)      # sólo el cupo mensual
    a = _shop(client, accounts, raw_conn, "Plan A")
    b = _shop(client, accounts, raw_conn, "Plan B")
    with tenant_tx(a["tenant"]) as cur:
        plans.set_plan(cur, a["tenant"], "mostrador")
    _use(raw_conn, a["tenant"], plans.PLANS["mostrador"]["ai_calls_month"])
    _use(raw_conn, b["tenant"], plans.PLANS["mostrador"]["ai_calls_month"])     # mismo uso, plan más grande
    assert limits.ai_allowed(a["tenant"]) is False
    assert limits.ai_allowed(b["tenant"]) is True
    assert client.get("/app/ai-usage", headers=bearer(a["uid"])).json()["plan"]["over"] is True


def test_agent_keeps_selling_without_ai_over_the_cap(client, accounts, raw_conn, monkeypatch):
    from app.agent.sales_agent import handle_sales_message
    shop = _shop(client, accounts, raw_conn, "Plan Sin IA")
    with tenant_tx(shop["tenant"]) as cur:
        plans.set_plan(cur, shop["tenant"], "mostrador")
    _use(raw_conn, shop["tenant"], plans.PLANS["mostrador"]["ai_calls_month"] + 1)
    called = []
    r = handle_sales_message(shop["tenant"], "tenés canilla?", planner=lambda m, t: called.append(1) or {"content": "x", "tool_calls": []})
    assert called == [] and r.mode == "mock" and r.reply      # responde por reglas, sin llamar al modelo


def test_unknown_plan_is_rejected(client, accounts, raw_conn):
    shop = _shop(client, accounts, raw_conn, "Plan Malo")
    with pytest.raises(ValueError), tenant_tx(shop["tenant"]) as cur:
        plans.set_plan(cur, shop["tenant"], "gratis")
