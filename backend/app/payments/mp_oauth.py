"""Mercado Pago por negocio: cada comercio conecta SU cuenta con el OAuth oficial y cobra en ella.

- **Alta:** el dueño toca «Conectar Mercado Pago» → autoriza en mercadopago.com → vuelve a nuestro
  callback con un `code` (vence a los 10 min) que se cambia por tokens en `POST /oauth/token`.
- **State:** el negocio y el usuario viajan cifrados y firmados (Fernet, 10 min de vida) y el state es
  de **un solo uso** (nonce guardado al crear el link y consumido en el callback).
- **Tokens:** cifrados en la base (clave fuera de la base, `MP_TOKEN_KEY`). Duran 180 días; el worker
  los renueva antes con el refresh token (que cambia en cada renovación), de a uno, con la fila
  bloqueada, y espaciando los reintentos de los que fallan.
- Nunca se loguean ni se devuelven al panel. Desconectar borra los tokens. Un token vencido no se usa.
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

from ..config import settings
from ..db import system_tx, tenant_tx
from ..domain import opportunities

log = logging.getLogger(__name__)

AUTH_URL = "https://auth.mercadopago.com/authorization"
STATE_TTL_S = 600
REFRESH_BEFORE = timedelta(days=30)
RETRY_EVERY = timedelta(hours=6)
TOKEN_DAYS = 180


class OAuthError(Exception):
    """El alta no se pudo completar (state inválido/vencido/usado, código rechazado, MP caído)."""


def _fernet() -> Fernet:
    return Fernet(settings.mp_token_key.encode())


def enabled() -> bool:
    if not (settings.mp_client_id and settings.mp_client_secret and settings.mp_token_key):
        return False
    try:
        _fernet()
    except (ValueError, TypeError):
        log.error("MP_TOKEN_KEY no es una clave Fernet válida: Mercado Pago por negocio queda apagado")
        return False
    return True


def redirect_uri() -> str:
    return f"{settings.public_base_url.rstrip('/')}/mp/oauth/callback"


def authorize_url(tenant_id: str, uid: str) -> str:
    if not enabled():
        raise OAuthError("Mercado Pago por negocio no está configurado.")
    nonce = secrets.token_hex(16)
    with tenant_tx(tenant_id) as cur:
        cur.execute("delete from mp_oauth_states where created_at < now() - make_interval(secs => %s)", (STATE_TTL_S,))
        cur.execute("insert into mp_oauth_states (nonce, tenant_id) values (%s, %s)", (nonce, tenant_id))
    state = _fernet().encrypt(json.dumps({"t": tenant_id, "u": uid, "n": nonce}).encode()).decode()
    return AUTH_URL + "?" + urlencode({"client_id": settings.mp_client_id, "response_type": "code",
                                       "platform_id": "mp", "state": state, "redirect_uri": redirect_uri()})


def _read_state(state: str) -> dict[str, str]:
    try:
        data = json.loads(_fernet().decrypt(state.encode(), ttl=STATE_TTL_S))
    except (InvalidToken, ValueError, TypeError):
        raise OAuthError("El enlace de conexión venció o no es válido. Probá de nuevo.") from None
    if not isinstance(data, dict) or not data.get("t") or not data.get("u") or not data.get("n"):
        raise OAuthError("El enlace de conexión no es válido.")
    return data


def _token_request(body: dict[str, Any], client: Optional[httpx.Client] = None) -> dict[str, Any]:
    c = client or httpx.Client(base_url=settings.mp_api_base, timeout=15.0)
    try:
        resp = c.post("/oauth/token", json={"client_id": settings.mp_client_id,
                                            "client_secret": settings.mp_client_secret, **body})
        if resp.status_code >= 400:
            raise OAuthError(f"Mercado Pago rechazó la autorización ({resp.status_code}).")
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OAuthError(f"Mercado Pago no respondió ({type(exc).__name__}).") from exc
    if not isinstance(data, dict) or not data.get("access_token"):
        raise OAuthError("Mercado Pago no devolvió un token.")
    return data


def _invalidate_links(cur: Any, tenant_id: str, keep_mp_user: Optional[str] = None) -> None:
    """Links de pago sin cobrar creados con otra cuenta (o con ninguna): no se vuelven a ofrecer."""
    cur.execute("update payments set checkout_url = null where tenant_id = %s and provider = 'mercadopago' "
                "and checkout_url is not null and status in ('created', 'pending', 'rejected') "
                "and (%s::text is null or mp_user_id is distinct from %s)", (tenant_id, keep_mp_user, keep_mp_user))


def _store(cur: Any, tenant_id: str, data: dict[str, Any], uid: Optional[str]) -> None:
    """Guarda/actualiza los tokens. En una renovación, lo que la respuesta no trae (usuario, modo,
    clave pública) se conserva: nunca se pisa con vacío."""
    f = _fernet()
    expires = datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in") or TOKEN_DAYS * 86400))
    user = str(data["user_id"])[:40] if data.get("user_id") else None
    cur.execute(
        "insert into mp_connections (tenant_id, mp_user_id, access_token_encrypted, refresh_token_encrypted, "
        "public_key, live_mode, expires_at, connected_by) values (%s, coalesce(%s, 'desconocido'), %s, %s, %s, %s, %s, %s) "
        "on conflict (tenant_id) do update set mp_user_id = coalesce(%s, mp_connections.mp_user_id), "
        "access_token_encrypted = excluded.access_token_encrypted, "
        "refresh_token_encrypted = coalesce(excluded.refresh_token_encrypted, mp_connections.refresh_token_encrypted), "
        "public_key = coalesce(excluded.public_key, mp_connections.public_key), "
        "live_mode = coalesce(excluded.live_mode, mp_connections.live_mode), "
        "expires_at = excluded.expires_at, connected_by = coalesce(excluded.connected_by, mp_connections.connected_by), "
        "connected_at = case when excluded.connected_by is not null then now() else mp_connections.connected_at end, "
        "refreshed_at = case when excluded.connected_by is null then now() else mp_connections.refreshed_at end, "
        "last_error = null, last_attempt_at = null",
        (tenant_id, user, f.encrypt(data["access_token"].encode()).decode(),
         f.encrypt(data["refresh_token"].encode()).decode() if data.get("refresh_token") else None,
         (data.get("public_key") or None) and str(data["public_key"])[:120],
         data.get("live_mode") if isinstance(data.get("live_mode"), bool) else None, expires, uid, user))


def complete(code: str, state: str, client: Optional[httpx.Client] = None) -> str:
    """Callback del OAuth: valida y consume el state, cambia el código por tokens y los guarda."""
    if not enabled():
        raise OAuthError("Mercado Pago por negocio no está configurado.")
    st = _read_state(state or "")
    if not code or len(code) > 200:
        raise OAuthError("Mercado Pago no devolvió el código de autorización.")
    with tenant_tx(st["t"]) as cur:          # un solo uso: se consume antes de pedir los tokens
        cur.execute("delete from mp_oauth_states where nonce = %s and tenant_id = %s "
                    "and created_at > now() - make_interval(secs => %s) returning 1", (st["n"], st["t"], STATE_TTL_S))
        if cur.fetchone() is None:
            raise OAuthError("El enlace de conexión ya se usó o venció. Probá de nuevo.")
        cur.execute("select 1 from memberships where tenant_id = %s and user_id::text = %s and role = 'owner'",
                    (st["t"], st["u"]))
        if cur.fetchone() is None:
            raise OAuthError("Sólo el dueño del negocio puede conectar Mercado Pago.")
    data = _token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri()}, client)
    with tenant_tx(st["t"]) as cur:
        _store(cur, st["t"], data, st["u"])
        cur.execute("select mp_user_id from mp_connections where tenant_id = %s", (st["t"],))
        _invalidate_links(cur, st["t"], keep_mp_user=cur.fetchone()["mp_user_id"])
        opportunities._audit(cur, st["t"], "mp_connected", None, {"actor": st["u"], "mp_user_id": str(data.get("user_id") or "")})
    return st["t"]


def status(cur: Any, tenant_id: str) -> dict[str, Any]:
    cur.execute("select mp_user_id, live_mode, expires_at, connected_at, last_error, refresh_token_encrypted is not null as "
                "renewable from mp_connections where tenant_id = %s", (tenant_id,))
    row = cur.fetchone()
    iso = lambda d: d.isoformat() if d else None     # noqa: E731
    expired = bool(row and row["expires_at"] and row["expires_at"] <= datetime.now(timezone.utc))
    error = row["last_error"] if row else None
    if row and expired:
        error = "El acceso a Mercado Pago venció."
    elif row and not row["renewable"]:
        error = error or "Mercado Pago no dio permiso para renovar el acceso: va a haber que reconectar antes de que venza."
    return {"available": enabled(), "connected": row is not None and not expired,
            "mp_user_id": row["mp_user_id"] if row else None, "live_mode": row["live_mode"] if row else None,
            "expires_at": iso(row["expires_at"]) if row else None, "connected_at": iso(row["connected_at"]) if row else None,
            "last_error": error}


def disconnect(cur: Any, tenant_id: str, uid: str) -> bool:
    cur.execute("delete from mp_connections where tenant_id = %s", (tenant_id,))
    if cur.rowcount:
        _invalidate_links(cur, tenant_id)
        opportunities._audit(cur, tenant_id, "mp_disconnected", None, {"actor": uid})
    return bool(cur.rowcount)


def account_for(tenant_id: str) -> Optional[tuple[str, str]]:
    """(access token descifrado, usuario de MP) del negocio, o None si no conectó o venció."""
    with tenant_tx(tenant_id) as cur:
        cur.execute("select access_token_encrypted, mp_user_id from mp_connections where tenant_id = %s "
                    "and (expires_at is null or expires_at > now())", (tenant_id,))
        row = cur.fetchone()
    if row is None or not enabled():
        return None
    try:
        return _fernet().decrypt(row["access_token_encrypted"].encode()).decode(), row["mp_user_id"]
    except InvalidToken:
        log.error("token de Mercado Pago ilegible para un negocio (¿cambió MP_TOKEN_KEY?)")
        return None


def token_for(tenant_id: str) -> Optional[str]:
    account = account_for(tenant_id)
    return account[0] if account else None


def tenant_for_mp_user(mp_user_id: Any) -> Optional[str]:
    """Negocio dueño de una cuenta de MP (avisos sin `?t=`: links viejos o webhook de la aplicación)."""
    if not mp_user_id:
        return None
    with system_tx() as cur:
        cur.execute("select tenant_id from mp_connections where mp_user_id = %s", (str(mp_user_id)[:40],))
        rows = cur.fetchall()
    return str(rows[0]["tenant_id"]) if len(rows) == 1 else None


def refresh_due(limit: int = 20, client: Optional[httpx.Client] = None) -> int:
    """Worker: renueva los tokens que vencen en menos de 30 días, de a uno y con la fila bloqueada (dos
    workers no gastan el mismo refresh token). Los que fallan se reintentan cada 6 h, sin tapar a los
    sanos. Ningún error corta la pasada del worker."""
    if not enabled():
        return 0
    done = 0
    for _ in range(limit):
        try:
            with system_tx() as cur:
                cur.execute(
                    "select tenant_id, refresh_token_encrypted from mp_connections where refresh_token_encrypted is not null "
                    "and expires_at < now() + %s and (last_attempt_at is null or last_attempt_at < now() - %s) "
                    "order by last_attempt_at nulls first, expires_at limit 1 for update skip locked",
                    (REFRESH_BEFORE, RETRY_EVERY))
                row = cur.fetchone()
                if row is None:
                    break
                tenant = str(row["tenant_id"])
                cur.execute("update mp_connections set last_attempt_at = now() where tenant_id = %s", (tenant,))
                try:
                    refresh = _fernet().decrypt(row["refresh_token_encrypted"].encode()).decode()
                    data = _token_request({"grant_type": "refresh_token", "refresh_token": refresh}, client)
                    _store(cur, tenant, data, None)        # en la misma transacción que bloquea la fila
                    done += 1
                except (OAuthError, InvalidToken) as exc:
                    cur.execute("update mp_connections set last_error = %s where tenant_id = %s", (str(exc)[:200], tenant))
                    log.warning("no se pudo renovar el token de Mercado Pago de un negocio: %s", exc)
        except Exception:  # noqa: BLE001 - un negocio o la base con problemas no frena al resto del worker
            log.exception("renovación de tokens de Mercado Pago interrumpida")
            break
    return done
