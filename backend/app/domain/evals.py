"""Evaluaciones por negocio: casos que el agente debe pasar antes de activar un perfil nuevo.

Un caso es uno o más mensajes del cliente (uno por línea, se envían en orden) y lo que la
ÚLTIMA respuesta debe contener y no contener. Se corren contra el perfil vigente o contra un
borrador sin guardarlo, en una conversación descartable que se borra al terminar (con su
carrito y su lead), así no ensucian el panel ni apartan stock.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from ..db import tenant_tx
from ..schemas import MAX_PREVIEW_MESSAGES
from .inventory import normalize

MAX_CASES = 20


def _case(r: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(r["id"]), "message": r["message"], "expect_contains": r["expect_contains"],
            "expect_not_contains": r["expect_not_contains"]}


def list_cases(cur: Any, tenant_id: str) -> list[dict[str, Any]]:
    cur.execute("select id, message, expect_contains, expect_not_contains from agent_eval_cases "
                "where tenant_id = %s order by created_at", (tenant_id,))
    return [_case(r) for r in cur.fetchall()]


def add_case(cur: Any, tenant_id: str, data: dict[str, Any]) -> dict[str, Any]:
    message = str(data.get("message") or "").strip()[:1000]
    contains = [str(x).strip()[:200] for x in data.get("expect_contains") or [] if str(x).strip()][:10]
    not_contains = [str(x).strip()[:200] for x in data.get("expect_not_contains") or [] if str(x).strip()][:10]
    if not message or not (contains or not_contains):
        raise ValueError("El caso necesita un mensaje y al menos una expectativa.")
    cur.execute("select count(*) as n from agent_eval_cases where tenant_id = %s", (tenant_id,))
    if cur.fetchone()["n"] >= MAX_CASES:
        raise ValueError(f"Máximo {MAX_CASES} casos por negocio.")
    cur.execute("insert into agent_eval_cases (tenant_id, message, expect_contains, expect_not_contains) "
                "values (%s, %s, %s::jsonb, %s::jsonb) returning id, message, expect_contains, expect_not_contains",
                (tenant_id, message, json.dumps(contains, ensure_ascii=False),
                 json.dumps(not_contains, ensure_ascii=False)))
    return _case(cur.fetchone())


def delete_case(cur: Any, tenant_id: str, case_id: str) -> bool:
    cur.execute("delete from agent_eval_cases where tenant_id = %s and id = %s", (tenant_id, case_id))
    return cur.rowcount > 0


def _cleanup(tenant_id: str, conversation_id: str) -> None:
    with tenant_tx(tenant_id) as cur:
        cur.execute("delete from orders where tenant_id = %s and conversation_id = %s and status = 'CART_OPEN'",
                    (tenant_id, conversation_id))
        cur.execute("delete from opportunities where tenant_id = %s and conversation_id = %s",
                    (tenant_id, conversation_id))
        cur.execute("delete from conversations where tenant_id = %s and id = %s", (tenant_id, conversation_id))


def preview_turn(tenant_id: str, message: str, conversation_id: Optional[str],
                 profile: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Un mensaje de la vista previa del asistente, con el perfil BORRADOR, en una conversación de
    prueba (canal `eval`: sin pedidos, stock ni cobros) que el panel reutiliza mensaje a mensaje.
    LookupError si la conversación no es una vista previa de este negocio; ValueError si llegó al tope."""
    from ..agent import sales_agent
    from . import opportunities

    with tenant_tx(tenant_id) as cur:
        if conversation_id:
            cur.execute("select (select count(*) from messages m where m.tenant_id = c.tenant_id "
                        "and m.conversation_id = c.id and m.direction = 'inbound') as sent "
                        "from conversations c where c.tenant_id = %s and c.id = %s and c.channel = 'eval'",
                        (tenant_id, conversation_id))
            row = cur.fetchone()
            if row is None:
                raise LookupError("vista previa inexistente")
            if row["sent"] >= MAX_PREVIEW_MESSAGES:
                raise ValueError(f"la vista previa admite hasta {MAX_PREVIEW_MESSAGES} mensajes: reiniciala")
    # La conversación existe ANTES del turno: si el turno falla, igual se puede borrar.
    conv = conversation_id or opportunities.ensure_conversation(tenant_id, None, "eval")
    try:
        res = sales_agent.handle_sales_message(tenant_id, message, conv, profile_override=profile, channel="eval")
    except Exception:
        if not conversation_id:   # una vista previa que no llegó a empezar no queda guardada
            _cleanup(tenant_id, conv)
        raise
    return {"conversation_id": conv, "reply": res.reply, "mode": res.mode, "ui": res.ui}


def end_preview(tenant_id: str, conversation_id: str) -> bool:
    with tenant_tx(tenant_id) as cur:
        cur.execute("select 1 from conversations where tenant_id = %s and id = %s and channel = 'eval'",
                    (tenant_id, conversation_id))
        if cur.fetchone() is None:
            return False
    _cleanup(tenant_id, conversation_id)
    return True


def cleanup_stale(max_age: str = "1 hour") -> int:
    """Borra conversaciones de prueba (vistas previas abandonadas, pruebas interrumpidas). Worker."""
    from ..db import system_tx
    with system_tx() as cur:
        cur.execute("select tenant_id, id from conversations where channel = 'eval' "
                    "and created_at < now() - %s::interval", (max_age,))
        stale = cur.fetchall()
    for row in stale:
        _cleanup(str(row["tenant_id"]), str(row["id"]))
    return len(stale)


def run(tenant_id: str, cases: list[dict[str, Any]], profile: Optional[dict[str, Any]] = None,
        planner: Any = None) -> dict[str, Any]:
    """Corre los casos. `profile`: borrador a probar (si no, el vigente)."""
    from ..agent import sales_agent

    from . import opportunities

    results = []
    for case in cases[:MAX_CASES]:
        turns = [t.strip() for t in case["message"].splitlines() if t.strip()]
        reply = ""
        # Creada antes del primer turno: si un turno falla, igual se borra.
        conv = opportunities.ensure_conversation(tenant_id, None, "eval")
        try:
            for message in turns:
                res = sales_agent.handle_sales_message(tenant_id, message, conv, planner=planner,
                                                       profile_override=profile, channel="eval")
                conv, reply = res.conversation_id, res.reply
        finally:
            _cleanup(tenant_id, conv)
        text = normalize(reply)
        failures = ([f"no dice «{x}»" for x in case["expect_contains"] if normalize(x) not in text]
                    + [f"dice «{x}»" for x in case["expect_not_contains"] if normalize(x) in text])
        results.append({"id": case.get("id"), "message": case["message"], "reply": reply,
                        "passed": not failures, "failures": failures})
    return {"passed": sum(r["passed"] for r in results), "total": len(results), "results": results}
