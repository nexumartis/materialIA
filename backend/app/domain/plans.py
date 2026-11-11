"""Planes por negocio y su cupo mensual de IA (founder/pricing-v3.md).

El cupo cuenta **respuestas con IA** (llamadas al modelo) del mes calendario, hora Argentina. Al
pasarlo, el agente sigue atendiendo SIN IA (reglas) hasta el mes siguiente: la venta no se corta y el
gasto queda acotado. Así cada negocio gasta sólo lo suyo y ninguno deja sin IA a los demás (el tope
global queda sólo como freno de emergencia).

Los cupos son una estimación inicial: se ajustan con el uso real de los pilotos.
El plan lo asigna la plataforma (es facturación), no el dueño desde el panel.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Any

from ..db import tenant_tx

PLANS: dict[str, dict[str, Any]] = {
    "mostrador": {"label": "Mostrador", "ai_calls_month": 3_000},
    "vendedor": {"label": "Vendedor", "ai_calls_month": 8_000},
    "entrega": {"label": "Entrega", "ai_calls_month": 15_000},
}
DEFAULT = "vendedor"


def plan_of(cur: Any, tenant_id: str) -> str:
    cur.execute("select settings_json ->> 'plan' as plan from tenants where id = %s", (tenant_id,))
    row = cur.fetchone()
    plan = (row or {}).get("plan")
    return plan if plan in PLANS else DEFAULT


def set_plan(cur: Any, tenant_id: str, plan: str) -> None:
    if plan not in PLANS:
        raise ValueError(f"Plan desconocido: {plan}")
    cur.execute("update tenants set settings_json = jsonb_set(coalesce(settings_json, '{}'::jsonb), '{plan}', %s::jsonb) "
                "where id = %s", (json.dumps(plan), tenant_id))
    if not cur.rowcount:
        raise LookupError(tenant_id)


def _month_start(cur: Any) -> date:
    cur.execute("select date_trunc('month', now() at time zone 'America/Argentina/Buenos_Aires')::date as d")
    return cur.fetchone()["d"]


def month_calls(cur: Any, tenant_id: str) -> int:
    cur.execute("select coalesce(sum(calls), 0) as n from llm_usage where tenant_id = %s and day >= %s",
                (tenant_id, _month_start(cur)))
    return int(cur.fetchone()["n"])


def usage(cur: Any, tenant_id: str) -> dict[str, Any]:
    """Para el panel: plan, cupo, usado en el mes y cuándo se renueva."""
    key = plan_of(cur, tenant_id)
    cap = PLANS[key]["ai_calls_month"]
    used = month_calls(cur, tenant_id)
    start = _month_start(cur)
    renews = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return {"plan": key, "label": PLANS[key]["label"], "ai_calls_month": cap, "used_month": used,
            "percent": min(100, round(used * 100 / cap)) if cap else 0, "over": used >= cap,
            "renews_on": renews.isoformat()}


def main(argv: list[str]) -> None:
    """Asignar el plan de un negocio: `python -m app.domain.plans <tenant_id> <mostrador|vendedor|entrega>`."""
    p = argparse.ArgumentParser(prog="python -m app.domain.plans")
    p.add_argument("tenant_id")
    p.add_argument("plan", choices=sorted(PLANS))
    a = p.parse_args(argv)
    with tenant_tx(a.tenant_id) as cur:
        set_plan(cur, a.tenant_id, a.plan)
    print(f"plan {a.plan} asignado")


if __name__ == "__main__":
    main(sys.argv[1:])
