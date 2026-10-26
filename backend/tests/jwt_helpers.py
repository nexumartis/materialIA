"""Tokens de prueba firmados con una clave EC local (sustituye al JWKS del proyecto)."""
from __future__ import annotations

import time

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.config import settings

KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_KEY = ec.generate_private_key(ec.SECP256R1())


def make_token(sub: str, *, key=KEY, alg: str = "ES256", exp_in: int = 600,
               iss: str | None = None, aud: str = "authenticated") -> str:
    claims = {"sub": sub, "aud": aud, "iss": iss or settings.supabase_issuer,
              "exp": int(time.time()) + exp_in, "role": "authenticated"}
    return jwt.encode(claims, key, algorithm=alg)


def bearer(sub_or_token: str, *, raw: bool = False) -> dict:
    token = sub_or_token if raw else make_token(sub_or_token)
    return {"authorization": f"Bearer {token}"}
