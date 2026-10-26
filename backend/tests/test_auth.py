"""Autenticación del panel: verificación del JWT de Supabase Auth (asimétrico, por JWKS)
y `/app/me`. Cualquier token dudoso => 401; token válido sin negocio => 403."""
from __future__ import annotations

import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from jwt_helpers import KEY, OTHER_KEY, make_token



@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    """Reemplaza la descarga del JWKS por la clave pública de prueba."""
    monkeypatch.setattr(auth, "_signing_key", lambda token: KEY.public_key())


def bearer(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


def test_verify_jwt_returns_sub():
    sub = str(uuid.uuid4())
    assert auth.verify_jwt(make_token(sub)) == sub


@pytest.mark.parametrize("token", [
    make_token(str(uuid.uuid4()), key=OTHER_KEY),                 # firma de otra clave
    make_token(str(uuid.uuid4()), exp_in=-10),                     # vencido
    make_token(str(uuid.uuid4()), iss="https://otro.supabase.co/auth/v1"),
    make_token(str(uuid.uuid4()), aud="anon"),
    make_token("no-es-uuid"),
    jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 600},
               "secreto-compartido", algorithm="HS256"),
    jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 600},
               None, algorithm="none"),
    "basura",
])
def test_verify_jwt_rejects_invalid(token):
    with pytest.raises(auth.AuthError):
        auth.verify_jwt(token)


@pytest.mark.parametrize("headers", [{}, {"authorization": "Basic abc"}, {"authorization": "Bearer "},
                                     bearer("basura")])
def test_me_requires_valid_bearer(headers):
    assert TestClient(app).get("/app/me", headers=headers).status_code == 401


def test_me_without_membership_is_403():
    r = TestClient(app).get("/app/me", headers=bearer(make_token(str(uuid.uuid4()))))
    assert r.status_code == 403


def test_me_returns_own_business(accounts):
    uid, tid = accounts("Vidriería Té")
    r = TestClient(app).get("/app/me", headers=bearer(make_token(uid)))
    assert r.status_code == 200
    assert r.json() == {"user_id": uid, "tenant_id": tid, "business_name": "Vidriería Té"}


def test_jwks_unreachable_is_503_not_401(monkeypatch):
    """Si no se puede consultar el JWKS es una falla del servicio, no una sesión inválida:
    el front no debe cerrar la sesión del usuario."""
    def down(token):
        raise jwt.PyJWKClientConnectionError("jwks caído")
    monkeypatch.setattr(auth, "_signing_key", down)
    r = TestClient(app).get("/app/me", headers=bearer(make_token(str(uuid.uuid4()))))
    assert r.status_code == 503
