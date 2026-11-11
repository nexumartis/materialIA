"""Fuera de local/dev, la configuración insegura se detecta (el servidor no arranca) y las rutas
/sandbox no existen."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.main import app


def test_unsafe_production_config_is_detected():
    s = Settings(app_env="production", payment_provider="simulated", cors_origins="", sandbox_admin=True)
    problems = " ".join(s.unsafe_for_production())
    assert "simulated" in problems and "CORS" in problems and "SANDBOX" in problems
    shared = Settings(app_env="production", payment_provider="mercadopago", cors_origins="https://panel.ejemplo.com")
    assert "OAuth por negocio" in " ".join(shared.unsafe_for_production())      # una sola cuenta para todos
    ok = Settings(app_env="production", payment_provider="mercadopago", cors_origins="https://panel.ejemplo.com",
                  mp_client_id="app", mp_client_secret="secreto", mp_token_key="k")
    assert ok.unsafe_for_production() == [] and ok.cors_list == ["https://panel.ejemplo.com"]
    assert Settings(app_env="local").cors_list == ["*"]


def test_sandbox_routes_hidden_in_production(monkeypatch):
    client = TestClient(app)
    assert client.get("/sandbox/products?company=C").status_code != 404
    monkeypatch.setattr(settings, "app_env", "production")
    assert client.get("/sandbox/products?company=C").status_code == 404
