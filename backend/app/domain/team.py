"""Equipo del negocio: el dueño invita empleados por email y les quita el acceso; el equipo deja
notas internas en las conversaciones de la bandeja.

Roles: `owner` (todo) y `staff` (bandeja, pedidos, oportunidades, comprobantes). Lo que toca
plata, catálogo, configuración del agente o el equipo es sólo del dueño (`OWNER_ONLY` en main).
No se envían emails: el dueño le avisa al empleado que se registre con ese email; la membresía
la crea la base al registrarse (y confirmar) ese email (migración 0016).
"""
from __future__ import annotations

import re
from typing import Any, Optional

from . import opportunities, webhooks

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
MAX_NOTE = 2000


def role(cur: Any) -> str:
    """Rol del usuario de la transacción `user_tx` (RLS: sólo su propia membresía)."""
    cur.execute("select app_member_role() as role")
    return cur.fetchone()["role"]


def members(cur: Any, tenant_id: str) -> dict[str, Any]:
    """Equipo e invitaciones pendientes. Corre como backend (lee emails de auth.users)."""
    cur.execute("select m.user_id, m.role, m.created_at, u.email from memberships m "
                "left join auth.users u on u.id = m.user_id where m.tenant_id = %s "
                "order by m.role = 'owner' desc, m.created_at", (tenant_id,))
    team = [{"user_id": str(r["user_id"]), "email": r["email"], "role": r["role"],
             "since": r["created_at"].isoformat()} for r in cur.fetchall()]
    cur.execute("select email, role, created_at from team_invites where tenant_id = %s order by created_at",
                (tenant_id,))
    invites = [{"email": r["email"], "role": r["role"], "created_at": r["created_at"].isoformat()}
               for r in cur.fetchall()]
    return {"members": team, "invites": invites}


def invite(cur: Any, tenant_id: str, uid: str, email: str, role: str = "staff") -> None:
    """`role`: «staff» (atiende el panel) o «driver» (reparto: sólo ve su hoja de ruta)."""
    if role not in ("staff", "driver"):
        raise ValueError("Rol inválido.")
    email = (email or "").strip().lower()
    if not _EMAIL.match(email):
        raise ValueError("Escribí un email válido.")
    cur.execute("select 1 from auth.users where lower(email) = %s", (email,))
    if cur.fetchone():
        # Una persona = un negocio: una cuenta existente ya tiene el suyo.
        raise ValueError("Ese email ya tiene una cuenta. Pedile que se registre con otro email.")
    cur.execute("select tenant_id from team_invites where email = %s", (email,))
    row = cur.fetchone()
    if row and str(row["tenant_id"]) != tenant_id:
        raise ValueError("Ese email ya tiene una invitación pendiente de otro negocio.")
    cur.execute("insert into team_invites (email, tenant_id, invited_by, role) values (%s, %s, %s, %s) "
                "on conflict (email) do nothing", (email, tenant_id, uid, role))
    opportunities._audit(cur, tenant_id, "team_invited", None, {"actor": uid, "role": role})


def cancel_invite(cur: Any, tenant_id: str, email: str) -> bool:
    cur.execute("delete from team_invites where tenant_id = %s and email = %s",
                (tenant_id, (email or "").strip().lower()))
    return bool(cur.rowcount)


def remove(cur: Any, tenant_id: str, uid: str, member_id: str) -> bool:
    """Quita a un empleado. El dueño no se puede quitar. Lo que tenía tomado vuelve al agente
    con aviso de derivación, para que nadie quede sin atender."""
    cur.execute("delete from memberships where tenant_id = %s and user_id = %s and role in ('staff', 'driver')",
                (tenant_id, member_id))
    if not cur.rowcount:
        return False
    cur.execute("update conversations set taken_by = null, taken_at = null, "
                "needs_human_at = coalesce(needs_human_at, now()), "
                "needs_human_reason = coalesce(needs_human_reason, 'asked') "
                "where tenant_id = %s and taken_by = %s returning id", (tenant_id, member_id))
    for r in cur.fetchall():
        webhooks.enqueue(cur, tenant_id, "conversation.needs_human",
                         {"conversation_id": str(r["id"]), "reason": "member_removed"})
        cur.execute("insert into handoff_events (tenant_id, conversation_id, reason) select %s, %s, 'member_removed' "
                    "where not exists (select 1 from handoff_events where tenant_id = %s and conversation_id = %s "
                    "and answered_at is null)", (tenant_id, r["id"], tenant_id, r["id"]))
    opportunities._audit(cur, tenant_id, "team_member_removed", member_id, {"actor": uid})
    return True


# --- Notas internas de la bandeja -------------------------------------------------------
def notes(cur: Any, tenant_id: str, conversation_id: str) -> list[dict[str, Any]]:
    cur.execute("select id, author_id, author_email, body, created_at from conversation_notes "
                "where tenant_id = %s and conversation_id = %s order by created_at limit 200",
                (tenant_id, conversation_id))
    return [{"id": str(r["id"]), "author_id": str(r["author_id"]) if r["author_id"] else None,
             "author": r["author_email"] or "Ex integrante", "body": r["body"],
             "at": r["created_at"].isoformat()} for r in cur.fetchall()]


def add_note(cur: Any, tenant_id: str, uid: str, email: Optional[str], conversation_id: str,
             body: str) -> Optional[dict[str, Any]]:
    """None si la conversación no es del negocio. Corre en `user_tx` (RLS exige autor = uid)."""
    body = (body or "").strip()
    if not body:
        raise ValueError("La nota está vacía.")
    if len(body) > MAX_NOTE:
        raise ValueError(f"La nota supera {MAX_NOTE} caracteres.")
    cur.execute("select 1 from conversations where tenant_id = %s and id = %s", (tenant_id, conversation_id))
    if cur.fetchone() is None:
        return None
    cur.execute("insert into conversation_notes (tenant_id, conversation_id, author_id, author_email, body) "
                "values (%s, %s, %s, %s, %s) returning id, created_at",
                (tenant_id, conversation_id, uid, email, body))
    r = cur.fetchone()
    return {"id": str(r["id"]), "author_id": uid, "author": email or "Vos", "body": body,
            "at": r["created_at"].isoformat()}
