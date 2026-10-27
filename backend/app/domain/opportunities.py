"""Oportunidades, conversaciones, mensajes y auditoría. Todo scoped por tenant."""
from __future__ import annotations

import json
from typing import Any, Optional

from ..db import tenant_tx
from ..schemas import OpportunityInput, OpportunitySummary


# --- Conversaciones / mensajes -------------------------------------------
def ensure_conversation(tenant_id: str, conversation_id: Optional[str], channel: str = "web_sandbox") -> str:
    with tenant_tx(tenant_id) as cur:
        if conversation_id:
            cur.execute(
                "select id from conversations where tenant_id = %s and id = %s",
                (tenant_id, conversation_id),
            )
            if cur.fetchone():
                return conversation_id
        cur.execute(
            "insert into conversations (tenant_id, channel, status) "
            "values (%s, %s, 'open') returning id",
            (tenant_id, channel),
        )
        return str(cur.fetchone()["id"])


def get_recent_messages(tenant_id: str, conversation_id: str, limit: int = 8) -> list[dict[str, str]]:
    """Historial reciente como [{role, content}] (para el LLM en modo live)."""
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select direction, content from messages "
            "where tenant_id = %s and conversation_id = %s "
            "order by created_at desc limit %s",
            (tenant_id, conversation_id, limit),
        )
        rows = cur.fetchall()
    role = {"inbound": "user", "outbound": "assistant"}
    return [{"role": role.get(r["direction"], "user"), "content": r["content"]} for r in reversed(rows)]


def conversation_messages(tenant_id: str, conversation_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Historial para mostrar en el chat, con el contenido interactivo de cada mensaje."""
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select direction, content, payload from messages "
            "where tenant_id = %s and conversation_id = %s order by created_at, id limit %s",
            (tenant_id, conversation_id, limit),
        )
        rows = cur.fetchall()
    role = {"inbound": "user", "outbound": "assistant"}
    return [{"role": role.get(r["direction"], "user"), "content": r["content"], "ui": r["payload"]}
            for r in rows]


def add_message(tenant_id: str, conversation_id: str, direction: str, content: str,
                payload: Optional[dict[str, Any]] = None, profile_version: Optional[int] = None) -> None:
    """`profile_version`: versión del perfil del agente que generó la respuesta (auditoría)."""
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "insert into messages (tenant_id, conversation_id, direction, content, payload, profile_version) "
            "values (%s, %s, %s, %s, %s::jsonb, %s)",
            (tenant_id, conversation_id, direction, content,
             json.dumps(payload) if payload else None, profile_version),
        )
        if direction == "inbound":
            cur.execute(
                "update conversations set last_customer_message_at = now() "
                "where tenant_id = %s and id = %s",
                (tenant_id, conversation_id),
            )


# --- Oportunidades --------------------------------------------------------
def get_conversation_requirements(tenant_id: str, conversation_id: Optional[str]) -> dict[str, Any]:
    """Requisitos ya acumulados para esta conversación (memoria del chat)."""
    if not conversation_id:
        return {}
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select requirements_json from opportunities "
            "where tenant_id = %s and conversation_id = %s "
            "order by created_at desc limit 1",
            (tenant_id, conversation_id),
        )
        row = cur.fetchone()
    return (row["requirements_json"] or {}) if row else {}


def upsert_opportunity(tenant_id: str, data: OpportunityInput) -> OpportunitySummary:
    """Una oportunidad por conversación: inserta la primera vez, luego actualiza la
    misma (acumula requisitos en vez de duplicar leads)."""
    existing_id = None
    existing_stage = None
    row = None
    with tenant_tx(tenant_id) as cur:
        if data.conversation_id:
            cur.execute(
                "select id, stage from opportunities where tenant_id = %s and conversation_id = %s "
                "order by created_at desc limit 1",
                (tenant_id, data.conversation_id),
            )
            r = cur.fetchone()
            if r:
                existing_id = str(r["id"])
                existing_stage = r["stage"]

        if existing_id:
            cur.execute(
                """
                update opportunities set
                    requirements_json = %s::jsonb, stage = %s, requires_human_quote = %s,
                    estimated_amount = %s, price_snapshot_json = %s::jsonb, updated_at = now()
                where tenant_id = %s and id = %s
                returning id, stage, requires_human_quote, estimated_amount,
                          requirements_json, created_at, next_action_at
                """,
                (json.dumps(data.requirements), data.stage, data.requires_human_quote,
                 data.estimated_amount,
                 json.dumps(data.price_snapshot) if data.price_snapshot else None,
                 tenant_id, existing_id),
            )
            row = cur.fetchone()

    if existing_id:
        opp = _row_to_opp(row)
        # El agente avanzó el lead entre turnos: queda en el timeline.
        if data.stage != existing_stage:
            log_activity(tenant_id, opp.id, "cambio_estado", f"{existing_stage} → {data.stage}")
        return opp
    # sin conversación o sin oportunidad previa -> insertar
    return create_or_update_opportunity(tenant_id, data)


def create_or_update_opportunity(tenant_id: str, data: OpportunityInput) -> OpportunitySummary:
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            """
            insert into opportunities
                (tenant_id, conversation_id, customer_id, requirements_json, stage,
                 origin, requires_human_quote, estimated_amount, price_snapshot_json,
                 next_action_at)
            values (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, now() + interval '2 days')
            returning id, stage, requires_human_quote, estimated_amount,
                      requirements_json, created_at, next_action_at
            """,
            (
                tenant_id, data.conversation_id, data.customer_id,
                json.dumps(data.requirements), data.stage, data.origin,
                data.requires_human_quote, data.estimated_amount,
                json.dumps(data.price_snapshot) if data.price_snapshot else None,
            ),
        )
        row = cur.fetchone()
    opp = _row_to_opp(row)
    log_activity(tenant_id, opp.id, "creada", f"estado {opp.stage}, origen {data.origin}")
    return opp


# Cada operación tiene una versión interna que recibe el cursor (`_list`, `_get`,
# `_update`, `_log_activity`, `_activity`, `_audit`): el panel autenticado las compone
# dentro de UNA transacción `user_tx` (rol app_user + RLS). Las funciones públicas
# conservan su firma y abren `tenant_tx` para el sandbox y el agente.
_OPP_COLUMNS = ("id, stage, requires_human_quote, estimated_amount, "
                "requirements_json, created_at, next_action_at")


def list_opportunities(tenant_id: str, limit: int = 50, *,
                       exclude_buyer_threads: bool = False) -> list[OpportunitySummary]:
    with tenant_tx(tenant_id) as cur:
        return _list(cur, tenant_id, limit, exclude_buyer_threads=exclude_buyer_threads)


def _list(cur: Any, tenant_id: str, limit: int = 50, *,
          exclude_buyer_threads: bool = False) -> list[OpportunitySummary]:
    # El sandbox no lista las de conversaciones de compradores de la tienda pública (0006).
    buyer_filter = (" and not exists (select 1 from conversations c where c.tenant_id = opportunities.tenant_id"
                    " and c.id = opportunities.conversation_id and c.access_token_hash is not null)"
                    if exclude_buyer_threads else "")
    cur.execute(
        f"select {_OPP_COLUMNS} from opportunities "
        f"where tenant_id = %s{buyer_filter} order by created_at desc limit %s",
        (tenant_id, limit),
    )
    return [_row_to_opp(r) for r in cur.fetchall()]


def get_opportunity(tenant_id: str, opportunity_id: str) -> Optional[OpportunitySummary]:
    with tenant_tx(tenant_id) as cur:
        return _get(cur, tenant_id, opportunity_id)


def _get(cur: Any, tenant_id: str, opportunity_id: str) -> Optional[OpportunitySummary]:
    cur.execute(
        f"select {_OPP_COLUMNS} from opportunities where tenant_id = %s and id = %s",
        (tenant_id, opportunity_id),
    )
    row = cur.fetchone()
    return _row_to_opp(row) if row else None


ALLOWED_STAGES = {"nueva", "datos_incompletos", "para_cotizar", "cotizada", "seguimiento", "cerrada"}


def update_opportunity(tenant_id: str, opportunity_id: str, stage: Optional[str] = None,
                       estimated_amount: Optional[float] = None,
                       next_action_at: Optional[str] = None) -> Optional[OpportunitySummary]:
    with tenant_tx(tenant_id) as cur:
        return _update(cur, tenant_id, opportunity_id, stage=stage,
                       estimated_amount=estimated_amount, next_action_at=next_action_at)


def _update(cur: Any, tenant_id: str, opportunity_id: str, stage: Optional[str] = None,
            estimated_amount: Optional[float] = None,
            next_action_at: Optional[str] = None) -> Optional[OpportunitySummary]:
    """Actualiza estado, importe y/o fecha de seguimiento de una oportunidad de ESTA empresa.
    Registra la transición de estado y aplica la regla: una oportunidad cerrada no tiene
    seguimiento pendiente (se limpia `next_action_at`)."""
    if stage is not None and stage not in ALLOWED_STAGES:
        raise ValueError(f"stage inválido: {stage}")
    current = _get(cur, tenant_id, opportunity_id)
    if current is None:
        return None

    sets, params = [], {"tenant": tenant_id, "id": opportunity_id}
    stage_changed = stage is not None and stage != current.stage
    if stage is not None:
        sets.append("stage = %(stage)s")
        params["stage"] = stage
    if estimated_amount is not None:
        sets.append("estimated_amount = %(amount)s")
        params["amount"] = estimated_amount
    if stage == "cerrada":
        # Una cerrada no "vence": el seguimiento se limpia aunque venga una fecha.
        sets.append("next_action_at = null")
    elif next_action_at is not None:
        sets.append("next_action_at = %(next_action)s")
        params["next_action"] = next_action_at or None
    if not sets:
        return current
    sets.append("updated_at = now()")
    cur.execute(
        f"update opportunities set {', '.join(sets)} "
        f"where tenant_id = %(tenant)s and id = %(id)s returning {_OPP_COLUMNS}",
        params,
    )
    row = cur.fetchone()
    if row is None:
        return None
    if stage_changed:
        _log_activity(cur, tenant_id, opportunity_id, "cambio_estado", f"{current.stage} → {stage}")
    return _row_to_opp(row)


# --- Actividad (timeline) de una oportunidad ------------------------------
def log_activity(tenant_id: str, opportunity_id: str, kind: str, detail: str = "") -> None:
    """Registra una acción sobre la oportunidad (sin datos personales del cliente)."""
    with tenant_tx(tenant_id) as cur:
        _log_activity(cur, tenant_id, opportunity_id, kind, detail)


def _log_activity(cur: Any, tenant_id: str, opportunity_id: str, kind: str, detail: str = "") -> None:
    cur.execute(
        "insert into opportunity_activity (tenant_id, opportunity_id, kind, detail) "
        "values (%s, %s, %s, %s)",
        (tenant_id, opportunity_id, kind, detail),
    )


def get_activity(tenant_id: str, opportunity_id: str, limit: int = 50) -> list[dict[str, str]]:
    """Timeline cronológico (más antiguo primero) de la oportunidad de ESTA empresa."""
    with tenant_tx(tenant_id) as cur:
        return _activity(cur, tenant_id, opportunity_id, limit)


def _activity(cur: Any, tenant_id: str, opportunity_id: str, limit: int = 50) -> list[dict[str, str]]:
    cur.execute(
        "select kind, detail, created_at from opportunity_activity "
        "where tenant_id = %s and opportunity_id = %s "
        "order by created_at asc, id asc limit %s",
        (tenant_id, opportunity_id, limit),
    )
    return [{"kind": r["kind"], "detail": r["detail"], "created_at": str(r["created_at"])}
            for r in cur.fetchall()]


def _row_to_opp(row: dict[str, Any]) -> OpportunitySummary:
    return OpportunitySummary(
        id=str(row["id"]),
        stage=row["stage"],
        requires_human_quote=row["requires_human_quote"],
        estimated_amount=float(row["estimated_amount"]) if row["estimated_amount"] is not None else None,
        requirements=row["requirements_json"] or {},
        created_at=str(row["created_at"]),
        next_action_at=str(row["next_action_at"]) if row.get("next_action_at") else None,
    )


# --- Auditoría (sin secretos ni datos sensibles) -------------------------
def audit(tenant_id: Optional[str], event_type: str, entity_id: Optional[str] = None,
          metadata: Optional[dict[str, Any]] = None) -> None:
    with tenant_tx(tenant_id or "00000000-0000-0000-0000-000000000000") as cur:
        _audit(cur, tenant_id, event_type, entity_id, metadata)


def _audit(cur: Any, tenant_id: Optional[str], event_type: str, entity_id: Optional[str] = None,
           metadata: Optional[dict[str, Any]] = None) -> None:
    cur.execute(
        "insert into audit_events (tenant_id, event_type, entity_id, metadata_redacted) "
        "values (%s, %s, %s, %s::jsonb)",
        (tenant_id, event_type, entity_id, json.dumps(metadata or {})),
    )
