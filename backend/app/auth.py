"""Autenticación del panel con Supabase Auth.

El backend verifica el JWT de acceso con las claves PÚBLICAS del proyecto (JWKS,
firma asimétrica ES256/RS256): firma, vencimiento, emisor, audiencia y `sub` UUID.
Nunca se acepta HS256 con secreto compartido ni `alg=none`. El `sub` verificado es la
única identidad que llega a la base (`db.user_tx`); el negocio sale de `memberships`.
"""
from __future__ import annotations

import uuid
from typing import Any

import jwt
from fastapi import Header, HTTPException

from .config import settings

ALGORITHMS = ["ES256", "RS256"]
AUDIENCE = "authenticated"

_jwks_client: jwt.PyJWKClient | None = None


class AuthError(Exception):
    """Token ausente, mal formado o no verificable."""


def _signing_key(token: str) -> Any:
    """Clave pública que firmó el token, según su `kid` en el JWKS (cacheado)."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(settings.supabase_jwks_url, cache_keys=True, lifespan=600)
    return _jwks_client.get_signing_key_from_jwt(token).key


def verify_jwt(token: str) -> str:
    """Devuelve el `sub` (uuid del usuario) de un token válido; si no, `AuthError`."""
    try:
        claims = jwt.decode(
            token,
            _signing_key(token),
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=settings.supabase_issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
        return str(uuid.UUID(claims["sub"]))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise AuthError(type(exc).__name__) from exc


def current_uid(authorization: str | None = Header(default=None)) -> str:
    """Dependencia FastAPI: uid del `Authorization: Bearer <jwt>` o 401."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Falta iniciar sesión.")
    try:
        return verify_jwt(token.strip())
    except AuthError:
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida.")
