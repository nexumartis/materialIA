"""Autenticación del panel: verificación del JWT de Supabase Auth (asimétrico, por JWKS)
y `/app/me`. Cualquier token dudoso => 401; token válido sin negocio => 403."""
from __future__ import annotations

import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.main import app

_KEY = ec.generate_private_key(ec.SECP256R1())
_OTHER_KEY = ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def _test_jwks(monkeypatch):
    """Reemplaza la descarga del JWKS por la clave pública de prueba."""
    monkeypatch.setattr(auth, "_signing_key", lambda token: _KEY.public_key())


def make_token(sub: str, *, key=_KEY, alg: str = "ES256", exp_in: int = 600,
               iss: str | None = None, aud: str = "authenticated") -> str:
    claims = {"sub": sub, "aud": aud, "iss": iss or settings.supabase_issuer,
              "exp": int(time.time()) + exp_in, "role": "authenticated"}
    return jwt.encode(claims, key, algorithm=alg)


def bearer(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


def test_verify_jwt_returns_sub():
    sub = str(uuid.uuid4())
    assert auth.verify_jwt(make_token(sub)) == sub


@pytest.mark.parametrize("token", [
    make_token(str(uuid.uuid4()), key=_OTHER_KEY),                 # firma de otra clave
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
