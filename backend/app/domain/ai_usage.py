"""Uso de IA por negocio: llamadas y tokens que informa el proveedor (Ollama: prompt_eval_count y
eval_count), agrupados por día y tipo de tarea. Sirve para saber cuánto cuesta atender a cada
negocio. Registrar nunca rompe la respuesta al cliente."""
from __future__ import annotations

import contextlib
import logging
from contextvars import ContextVar
from typing import Any, Iterator, Optional

from ..config import settings
from ..db import tenant_tx

log = logging.getLogger(__name__)
_current: ContextVar[Optional[tuple[str, str]]] = ContextVar("ai_usage", default=None)


@contextlib.contextmanager
def for_tenant(tenant_id: str, kind: str) -> Iterator[None]:
    """Las llamadas al modelo dentro de este bloque se cuentan para este negocio y tarea."""
    token = _current.set((tenant_id, kind))
    try:
        yield
    finally:
        _current.reset(token)


def record(model: str, response: dict[str, Any]) -> None:
    ctx = _current.get()
    if ctx is None:
        return
    tenant_id, kind = ctx
    try:
        with tenant_tx(tenant_id) as cur:
            cur.execute(
                "insert into llm_usage (tenant_id, day, kind, model, calls, prompt_tokens, completion_tokens) "
                "values (%s, (now() at time zone 'America/Argentina/Buenos_Aires')::date, %s, %s, 1, %s, %s) "
                "on conflict (tenant_id, day, kind, model) do update set calls = llm_usage.calls + 1, "
                "prompt_tokens = llm_usage.prompt_tokens + excluded.prompt_tokens, "
                "completion_tokens = llm_usage.completion_tokens + excluded.completion_tokens",
                (tenant_id, kind, model[:80], int(response.get("prompt_eval_count") or 0),
                 int(response.get("eval_count") or 0)))
    except Exception:  # noqa: BLE001 - medir no puede romper la atención
        log.exception("no pude registrar el uso de IA")


def summary(cur: Any, tenant_id: str, days: int = 30) -> dict[str, Any]:
    """Uso de los últimos `days` días. Costo sólo si hay precio configurado (no se inventa)."""
    cur.execute("select kind, sum(calls) calls, sum(prompt_tokens) prompt, sum(completion_tokens) completion "
                "from llm_usage where tenant_id = %s and day > current_date - %s group by kind order by kind",
                (tenant_id, days))
    rows = [{"kind": r["kind"], "calls": int(r["calls"]), "prompt_tokens": int(r["prompt"]),
             "completion_tokens": int(r["completion"])} for r in cur.fetchall()]
    total_in = sum(r["prompt_tokens"] for r in rows)
    total_out = sum(r["completion_tokens"] for r in rows)
    price_in, price_out = settings.llm_price_in_per_mtok, settings.llm_price_out_per_mtok
    cost = (total_in * price_in + total_out * price_out) / 1_000_000 if price_in is not None and price_out is not None else None
    return {"days": days, "by_kind": rows, "calls": sum(r["calls"] for r in rows),
            "prompt_tokens": total_in, "completion_tokens": total_out,
            "cost": round(cost, 4) if cost is not None else None, "currency": settings.llm_price_currency}
