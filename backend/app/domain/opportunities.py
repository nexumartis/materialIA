"""Oportunidades, conversaciones, mensajes y auditoría. Todo scoped por tenant."""
from __future__ import annotations

import json
from typing import Any, Optional

from ..db import tenant_tx
from ..schemas import OpportunityInput, OpportunitySummary


# --- Conversaciones / mensajes -------------------------------------------
def ensure_conversation(tenant_id: str, conversation_id: Optional[str]) -> str:
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
            "values (%s, 'web_sandbox', 'open') returning id",
            (tenant_id,),
        )
        return str(cur.fetchone()["id"])


def add_message(tenant_id: str, conversation_id: str, direction: str, content: str) -> None:
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "insert into messages (tenant_id, conversation_id, direction, content) "
            "values (%s, %s, %s, %s)",
            (tenant_id, conversation_id, direction, content),
        )
        if direction == "inbound":
            cur.execute(
                "update conversations set last_customer_message_at = now() "
                "where tenant_id = %s and id = %s",
                (tenant_id, conversation_id),
            )


# --- Oportunidades --------------------------------------------------------
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
                      requirements_json, created_at
            """,
            (
                tenant_id, data.conversation_id, data.customer_id,
                json.dumps(data.requirements), data.stage, data.origin,
                data.requires_human_quote, data.estimated_amount,
                json.dumps(data.price_snapshot) if data.price_snapshot else None,
            ),
        )
        row = cur.fetchone()
    return _row_to_opp(row)


def list_opportunities(tenant_id: str, limit: int = 50) -> list[OpportunitySummary]:
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select id, stage, requires_human_quote, estimated_amount, "
            "requirements_json, created_at from opportunities "
            "where tenant_id = %s order by created_at desc limit %s",
            (tenant_id, limit),
        )
        rows = cur.fetchall()
    return [_row_to_opp(r) for r in rows]


def get_opportunity(tenant_id: str, opportunity_id: str) -> Optional[OpportunitySummary]:
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "select id, stage, requires_human_quote, estimated_amount, "
            "requirements_json, created_at from opportunities "
            "where tenant_id = %s and id = %s",
            (tenant_id, opportunity_id),
        )
        row = cur.fetchone()
    return _row_to_opp(row) if row else None


def _row_to_opp(row: dict[str, Any]) -> OpportunitySummary:
    return OpportunitySummary(
        id=str(row["id"]),
        stage=row["stage"],
        requires_human_quote=row["requires_human_quote"],
        estimated_amount=float(row["estimated_amount"]) if row["estimated_amount"] is not None else None,
        requirements=row["requirements_json"] or {},
        created_at=str(row["created_at"]),
    )


# --- Auditoría (sin secretos ni datos sensibles) -------------------------
def audit(tenant_id: Optional[str], event_type: str, entity_id: Optional[str] = None,
          metadata: Optional[dict[str, Any]] = None) -> None:
    with tenant_tx(tenant_id or "00000000-0000-0000-0000-000000000000") as cur:
        cur.execute(
            "insert into audit_events (tenant_id, event_type, entity_id, metadata_redacted) "
            "values (%s, %s, %s, %s::jsonb)",
            (tenant_id, event_type, entity_id, json.dumps(metadata or {})),
        )
