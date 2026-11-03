"""Respuestas rápidas del equipo en la bandeja: textos que carga el dueño y usa cualquiera del
equipo. Honestidad: no se guardan montos — un precio escrito a mano envejece; el precio sale del
catálogo al momento."""
from __future__ import annotations

from typing import Any

from . import opportunities
from .handoff import _MONEY

MAX = 30


def list_all(cur: Any, tenant_id: str) -> list[dict[str, Any]]:
    cur.execute("select id, title, body from quick_replies where tenant_id = %s order by title", (tenant_id,))
    return [{"id": str(r["id"]), "title": r["title"], "body": r["body"]} for r in cur.fetchall()]


def create(cur: Any, tenant_id: str, uid: str, title: str, body: str) -> dict[str, Any]:
    title, body = (title or "").strip(), (body or "").strip()
    if not 1 <= len(title) <= 60 or not 1 <= len(body) <= 1000:
        raise ValueError("Poné un título (hasta 60) y un texto (hasta 1000 caracteres).")
    if _MONEY.search(body):
        raise ValueError("Sin precios ni montos: el precio sale del catálogo al momento (uno escrito a mano envejece).")
    cur.execute("select count(*) as n from quick_replies where tenant_id = %s", (tenant_id,))
    if cur.fetchone()["n"] >= MAX:
        raise ValueError(f"Podés tener hasta {MAX} respuestas rápidas.")
    cur.execute("insert into quick_replies (tenant_id, title, body) values (%s, %s, %s) returning id",
                (tenant_id, title, body))
    rid = str(cur.fetchone()["id"])
    opportunities._audit(cur, tenant_id, "quick_reply_created", rid, {"actor": uid})
    return {"id": rid, "title": title, "body": body}


def delete(cur: Any, tenant_id: str, reply_id: str) -> bool:
    cur.execute("delete from quick_replies where tenant_id = %s and id = %s", (tenant_id, reply_id))
    return bool(cur.rowcount)
