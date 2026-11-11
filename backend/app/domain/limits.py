"""Frenos de abuso y de gasto. Dos capas:

1. **Límite de pedidos** (`hit`): cuántos mensajes puede mandar una persona del chat público (por IP),
   una conversación, una tienda entera o un usuario del panel en una ventana de tiempo. Pasado el
   tope, 429 «esperá un momento». Contadores en Postgres (sirven con varias instancias).
2. **Tope diario de IA** (`ai_allowed`): llamadas y tokens por negocio y en total, según `llm_usage`.
   Pasado el tope, la IA se apaga hasta el día siguiente (hora AR) y el agente sigue con las reglas
   (`mode: "mock"`): precios y stock reales y derivación a una persona. No se corta la venta.

Los topes salen de la configuración (`RATE_*`, `AI_DAILY_*`); 0 = sin límite en ese eje.
"""
from __future__ import annotations

import hashlib
import logging
import time
from contextvars import ContextVar
from typing import Optional

from fastapi import HTTPException, Request

from ..config import settings
from ..db import system_tx

log = logging.getLogger(__name__)


class AIBudgetExceeded(RuntimeError):
    """Se alcanzó el tope diario de IA (del negocio o global): usar el respaldo sin IA."""


# La tienda superó su ritmo por hora en ESTE pedido: se atiende igual, pero sin IA (ver guard_public_chat).
_shed: ContextVar[bool] = ContextVar("ai_shed", default=False)
_allowed_cache: dict[Optional[str], tuple[float, bool]] = {}
_CACHE_S = 5.0


def _bucket(scope: str, key: str) -> str:
    # Hash: el contador no guarda IPs ni ids en claro.
    return scope + ":" + hashlib.sha256(f"{scope}:{key}".encode()).hexdigest()[:32]


def _count(checks: list[tuple[str, str, int, int]], weight: int = 1) -> Optional[tuple[str, int]]:
    """Suma `weight` a cada cubo (en UNA transacción) y devuelve (cubo, ventana) del primero que
    superó su límite, o None. Si la base falla, deja pasar (un contador caído no puede cortar la
    atención) y lo registra."""
    checks = [c for c in checks if c[2] > 0]
    if not checks:
        return None
    try:
        with system_tx() as cur:
            for scope, key, limit, window in checks:
                cur.execute(
                    "insert into rate_limits (bucket, window_start, hits) values "
                    "(%s, to_timestamp(floor(extract(epoch from now()) / %s) * %s), %s) "
                    "on conflict (bucket, window_start) do update set hits = rate_limits.hits + excluded.hits "
                    "returning hits", (_bucket(scope, key), window, window, weight))
                if cur.fetchone()["hits"] > limit:
                    return scope, window
    except Exception:  # noqa: BLE001
        log.exception("no pude contar los límites %s", [c[0] for c in checks])
    return None


def hit(scope: str, key: str, limit: int, window_s: int, weight: int = 1) -> bool:
    return _count([(scope, key, limit, window_s)], weight) is None


def cleanup() -> int:
    """Worker: borra ventanas viejas (fuera del camino de los pedidos)."""
    with system_tx() as cur:
        cur.execute("delete from rate_limits where window_start < now() - interval '2 days'")
        return cur.rowcount


def client_ip(request: Request) -> str:
    """IP del cliente. Detrás de proxies que agregan X-Forwarded-For se toma la entrada que puso el
    proxy de confianza más externo: `TRUSTED_PROXY_HOPS` contados desde la derecha (Cloud Run
    directo: 1; detrás de un balanceador de Google: 2). Lo que agrega el cliente a la izquierda no
    cuenta. Si la cadena es más corta de lo esperado, se usa la IP del socket y se avisa en el log."""
    hops = settings.trusted_proxy_hops
    if hops > 0:
        chain = [p.strip() for p in (request.headers.get("x-forwarded-for") or "").split(",") if p.strip()]
        if len(chain) >= hops:
            return chain[-hops]
        log.warning("X-Forwarded-For con %d entradas y TRUSTED_PROXY_HOPS=%d: revisar la configuración",
                    len(chain), hops)
    return request.client.host if request.client else "desconocida"


_SLOW = "Estás mandando mensajes muy rápido. Esperá un momento y probá de nuevo."


def _too_many(window: int) -> HTTPException:
    retry = int(window - time.time() % window) + 1        # hasta que empiece la ventana siguiente
    return HTTPException(status_code=429, detail=_SLOW, headers={"Retry-After": str(retry)})


def guard_public_chat(request: Request, tenant_id: str, conversation_id: Optional[str]) -> None:
    """Chat público. Por IP (minuto y día) y por conversación (hora): pasado el tope, 429. Por tienda
    (hora) NO se bloquea —si no, unos pocos atacantes dejarían sin chat a los clientes reales—: se
    sigue atendiendo sin IA (reglas) hasta la hora siguiente, lo que también frena el gasto."""
    ip = client_ip(request)
    checks = [("ip-min", ip, settings.rate_ip_per_minute, 60),
              ("ip-day", ip, settings.rate_ip_per_day, 86_400)]
    if conversation_id:
        checks.append(("conv-hour", conversation_id, settings.rate_conversation_per_hour, 3_600))
    over = _count(checks)
    if over:
        log.warning("límite %s superado (tienda %s)", over[0], tenant_id)
        raise _too_many(over[1])
    if _count([("store-hour", tenant_id, settings.rate_store_per_hour, 3_600)]):
        log.warning("tienda %s sobre su ritmo por hora: atiende sin IA", tenant_id)
        _shed.set(True)


def guard_user(uid: str, scope: str = "panel-ai", weight: int = 1) -> None:
    """Acciones del panel que llaman a la IA. `weight`: cuántas corridas del agente implica (las
    evaluaciones corren un caso por vez)."""
    over = _count([(scope, uid, settings.rate_user_ai_per_minute, 60)], weight)
    if over:
        raise _too_many(over[1])


def ai_allowed(tenant_id: Optional[str]) -> bool:
    """¿Queda IA hoy (hora AR) para este negocio y en total? Sin negocio (tareas internas) sólo
    cuenta el tope global. Si la base falla, NO se permite: ante la duda, no se gasta.

    Es un tope «blando»: el uso se registra al terminar cada llamada, así que pedidos simultáneos
    pueden pasarlo por poco (como mucho, los turnos en curso × MAX_STEPS). El freno duro de gasto
    es el tope mensual en la consola del proveedor."""
    if _shed.get():
        return False
    now = time.monotonic()
    cached = _allowed_cache.get(tenant_id)
    if cached and now - cached[0] < _CACHE_S:
        return cached[1]
    try:
        with system_tx() as cur:
            cur.execute(
                "select coalesce(sum(calls), 0) as calls, "
                "coalesce(sum(prompt_tokens + completion_tokens), 0) as tokens, "
                "coalesce(sum(calls) filter (where tenant_id = %s), 0) as t_calls, "
                "coalesce(sum(prompt_tokens + completion_tokens) filter (where tenant_id = %s), 0) as t_tokens "
                "from llm_usage where day = (now() at time zone 'America/Argentina/Buenos_Aires')::date",
                (tenant_id, tenant_id))
            u = cur.fetchone()
    except Exception:  # noqa: BLE001
        log.exception("no pude leer el uso de IA: la apago por las dudas")
        return False
    over = [(settings.ai_daily_calls_global, u["calls"]), (settings.ai_daily_tokens_global, u["tokens"])]
    if tenant_id:
        over += [(settings.ai_daily_calls_per_tenant, u["t_calls"]),
                 (settings.ai_daily_tokens_per_tenant, u["t_tokens"])]
        # Cupo mensual del plan del negocio: cada uno gasta lo suyo y nadie deja sin IA a los demás.
        try:
            from . import plans
            with system_tx() as cur:
                cap = plans.PLANS[plans.plan_of(cur, tenant_id)]["ai_calls_month"]
                over.append((cap, plans.month_calls(cur, tenant_id)))
        except Exception:  # noqa: BLE001
            log.exception("no pude leer el cupo mensual de IA: la apago por las dudas")
            return False
    allowed = not any(limit > 0 and used >= limit for limit, used in over)
    if not allowed:
        log.warning("tope de IA alcanzado (negocio %s): sigue sin IA", tenant_id)
    if len(_allowed_cache) > 5000:
        _allowed_cache.clear()
    _allowed_cache[tenant_id] = (now, allowed)
    return allowed
