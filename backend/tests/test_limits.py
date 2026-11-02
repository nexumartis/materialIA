"""Frenos de abuso y gasto: límite de pedidos del chat público y del panel, y tope diario de IA que
apaga el modelo sin cortar la venta (sigue con reglas, mode "mock" explícito)."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.agent import llm_sales, llm_tasks, sales_agent
from app.config import settings
from app.domain import ai_usage, limits
from app.main import app
from jwt_helpers import KEY, bearer
from test_payment_documents import _shop


@pytest.fixture(autouse=True)
def _jwks(monkeypatch):
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())
    monkeypatch.setattr(limits, "_CACHE_S", 0)


@pytest.fixture
def client():
    return TestClient(app)


def _ip():
    return f"10.9.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"


def test_public_chat_limited_per_ip(client, accounts, raw_conn, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "Tienda Límite")
    monkeypatch.setattr(settings, "rate_ip_per_minute", 3)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    ip = _ip()
    say = lambda who: client.post(f"/public/{shop['slug']}/chat", json={"message": "hola"},
                                  headers={"x-forwarded-for": f"1.2.3.4, {who}"})
    assert [say(ip).status_code for _ in range(3)] == [200, 200, 200]
    r = say(ip)
    assert r.status_code == 429 and "Esperá" in r.json()["detail"] and 1 <= int(r.headers["retry-after"]) <= 61
    assert say(_ip()).status_code == 200            # otra persona no queda bloqueada
    # Cambiar lo que el cliente pone a la IZQUIERDA del X-Forwarded-For no saltea el límite.
    r = client.post(f"/public/{shop['slug']}/chat", json={"message": "hola"},
                    headers={"x-forwarded-for": f"9.9.9.9, {ip}"})
    assert r.status_code == 429


def test_store_wide_and_message_size_limits(client, accounts, raw_conn, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "Tienda Límite 2")
    monkeypatch.setattr(settings, "rate_store_per_hour", 2)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    planned = []
    monkeypatch.setattr(llm_sales, "default_planner", lambda: lambda m, t: planned.append(1) or {"content": "ok"})
    replies = [client.post(f"/public/{shop['slug']}/chat", json={"message": "hola"},
                           headers={"x-forwarded-for": _ip()}) for _ in range(3)]
    # Repartido en IPs: la tienda NO se bloquea (los clientes reales siguen), pero el 3.º va sin IA.
    assert [r.status_code for r in replies] == [200, 200, 200]
    assert [r.json()["mode"] for r in replies][2] == "mock" and len(planned) <= 2 * llm_sales.MAX_STEPS
    assert client.post(f"/public/{shop['slug']}/chat", json={"message": "x" * 2001}).status_code == 422
    assert client.post(f"/public/{shop['slug']}/chat", json={"message": "   "}).status_code == 422


def test_panel_ai_actions_limited_per_user(client, accounts, raw_conn, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "Tienda Límite 3")
    monkeypatch.setattr(settings, "rate_user_ai_per_minute", 2)
    h = bearer(shop["uid"])
    codes = [client.post("/app/agent-preview", headers=h, json={"message": "hola"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def _use(raw_conn, tenant, calls, tokens=0):
    with raw_conn.cursor() as cur:
        cur.execute("insert into llm_usage (tenant_id, day, kind, model, calls, prompt_tokens, completion_tokens) "
                    "values (%s, (now() at time zone 'America/Argentina/Buenos_Aires')::date, 'venta', 'test', %s, %s, 0) "
                    "on conflict (tenant_id, day, kind, model) do update set calls = excluded.calls, "
                    "prompt_tokens = excluded.prompt_tokens", (tenant, calls, tokens))
    raw_conn.commit()


def test_daily_ai_cap_turns_model_off_but_sale_continues(client, accounts, raw_conn, monkeypatch):
    shop = _shop(client, accounts, raw_conn, "Tienda Tope IA")
    other, other_tenant = accounts("Otra Tope IA")
    monkeypatch.setattr(settings, "ai_daily_calls_per_tenant", 5)
    monkeypatch.setattr(settings, "ai_daily_calls_global", 0)
    monkeypatch.setattr(settings, "ai_daily_tokens_global", 0)
    assert limits.ai_allowed(shop["tenant"])
    _use(raw_conn, shop["tenant"], 5)
    assert not limits.ai_allowed(shop["tenant"])
    assert limits.ai_allowed(other_tenant)             # el tope de un negocio no apaga a otro

    called = []

    def planner(messages, tools):
        called.append(1)
        return {"content": "respuesta del modelo", "tool_calls": []}
    res = sales_agent.handle_sales_message(shop["tenant"], "hola, quiero una canilla", None, planner=planner)
    assert called == [] and res.mode == "mock" and res.reply     # respondió con reglas, sin IA


def test_global_cap_and_http_gate(raw_conn, accounts, monkeypatch):
    _, tenant = accounts("Tope Global")
    monkeypatch.setattr(settings, "ai_daily_calls_per_tenant", 0)
    monkeypatch.setattr(settings, "ai_daily_tokens_per_tenant", 100)
    _use(raw_conn, tenant, 1, tokens=100)
    posted = []
    monkeypatch.setattr(llm_tasks.httpx, "post", lambda *a, **k: posted.append(1))
    with ai_usage.for_tenant(tenant, "otro"):
        with pytest.raises(limits.AIBudgetExceeded):
            llm_tasks._ollama("s", "u")
        with pytest.raises(limits.AIBudgetExceeded):
            llm_sales._ollama_planner([], [])
        assert llm_tasks.ask_json("s", "u", llm_tasks._ollama) is None   # las tareas usan su respaldo
    assert posted == []                                                    # nunca se llamó al modelo
