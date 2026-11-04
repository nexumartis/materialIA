"""Reparto e instalación: entregas agendadas de pedidos pagados y la hoja de ruta del repartidor.

- **Agendar** (dueño o empleado): un pedido PAGADO con envío a domicilio recibe día, franja, tipo
  (entrega, instalación o ambas) y quién va. Al cliente le llega el aviso en su charla.
- **Hoja de ruta** (repartidor): ve SÓLO sus entregas del día con lo necesario para hacerlas
  (qué lleva, dirección, contacto, nota). No ve otras conversaciones ni el panel.
- **Pasos:** salí (con demora estimada) → llegué → entregado / no pude (motivo). Cada paso avisa al
  cliente con un mensaje fijo, sin inventar nada, y avanza el pedido (despachado → en camino →
  entregado). El repartidor también puede escribirle un mensaje corto a SU cliente.
- Los avisos van a la charla web que el cliente ya tiene abierta (no es mensajería saliente).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from . import opportunities, orders

AR = ZoneInfo("America/Argentina/Buenos_Aires")
WINDOWS = {"am": "de 8 a 13 h", "pm": "de 13 a 18 h", "day": "durante el día"}
KINDS = {"delivery": "Entrega", "install": "Instalación", "delivery_install": "Entrega e instalación"}
STATUS_LABELS = {"scheduled": "Agendada", "on_the_way": "En camino", "arrived": "En el domicilio",
                 "done": "Hecha", "failed": "No se pudo", "cancelled": "Cancelada"}
# Qué paso sigue a cuál (el repartidor no salta ni vuelve atrás).
NEXT = {"scheduled": {"on_the_way", "failed"}, "on_the_way": {"arrived", "done", "failed"},
        "arrived": {"done", "failed"}}
SCHEDULABLE = ("PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT")
MAX_MESSAGE = 300
_DAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

_COLS = ("j.id, j.order_id, j.conversation_id, j.kind, j.scheduled_date, j.time_window, j.assigned_to, j.status, "
         "j.eta_minutes, j.note, j.failure_reason, j.started_at, j.arrived_at, j.finished_at, j.updated_at, j.created_at, "
         "o.number, o.status as order_status, o.total, o.delivery_address, o.delivery_contact, o.delivery_note, "
         "u.email as driver_email")
_FROM = ("from delivery_jobs j join orders o on o.tenant_id = j.tenant_id and o.id = j.order_id "
         "left join auth.users u on u.id = j.assigned_to")


def today() -> date:
    return datetime.now(AR).date()


def _when(d: date, window: str) -> str:
    rel = {0: "hoy", 1: "mañana"}.get((d - today()).days)
    day = f"{_DAYS[d.weekday()]} {d.day}/{d.month}"
    return f"{rel + ', ' if rel else 'el '}{day}, {WINDOWS[window]}"


def _address(row: dict[str, Any]) -> str:
    a = row.get("delivery_address") or {}
    return a.get("texto") or ", ".join(x for x in (f"{a.get('calle', '')} {a.get('altura', '')}".strip(),
                                                   a.get("localidad")) if x)


def _maps(row: dict[str, Any]) -> Optional[str]:
    a = row.get("delivery_address") or {}
    if a.get("lat") is not None and a.get("lon") is not None:
        return f"https://www.google.com/maps/search/?api=1&query={a['lat']},{a['lon']}"
    text = _address(row)
    return f"https://www.google.com/maps/search/?api=1&query={text.replace(' ', '+')}" if text else None


def _items(cur: Any, tenant_id: str, order_id: str) -> list[dict[str, Any]]:
    cur.execute("select name, qty from order_items where tenant_id = %s and order_id = %s order by name",
                (tenant_id, order_id))
    return [{"name": r["name"], "qty": r["qty"]} for r in cur.fetchall()]


def _view(cur: Any, tenant_id: str, row: dict[str, Any], driver: bool = False) -> dict[str, Any]:
    iso = lambda d: d.isoformat() if d else None     # noqa: E731
    contact = row.get("delivery_contact") or {}
    view = {"id": str(row["id"]), "order_id": str(row["order_id"]), "order_number": row["number"],
            "kind": row["kind"], "kind_label": KINDS[row["kind"]], "date": row["scheduled_date"].isoformat(),
            "window": row["time_window"], "window_label": WINDOWS[row["time_window"]],
            "status": row["status"], "status_label": STATUS_LABELS[row["status"]],
            "assigned_to": str(row["assigned_to"]) if row["assigned_to"] else None,
            "driver_email": row.get("driver_email"), "eta_minutes": row["eta_minutes"], "note": row["note"],
            "failure_reason": row["failure_reason"], "started_at": iso(row["started_at"]),
            "arrived_at": iso(row["arrived_at"]), "finished_at": iso(row["finished_at"]),
            "address": _address(row), "maps_url": _maps(row), "delivery_note": row.get("delivery_note"),
            "contact": {"name": contact.get("name") or "", "phone": contact.get("phone") or ""},
            "items": _items(cur, tenant_id, str(row["order_id"]))}
    if driver and row.get("conversation_id"):
        # Lo que escribió el cliente DESDE que se agendó la entrega («toquen timbre»), nada más.
        cur.execute("select content, created_at from messages where tenant_id = %s and conversation_id = %s "
                    "and direction = 'inbound' and created_at > %s order by created_at desc limit 3",
                    (tenant_id, row["conversation_id"], row["created_at"]))
        view["customer_messages"] = [{"text": r["content"], "at": r["created_at"].isoformat()}
                                     for r in reversed(cur.fetchall())]
    return view


def _fetch(cur: Any, tenant_id: str, job_id: str, lock: bool = False) -> Optional[dict[str, Any]]:
    cur.execute(f"select {_COLS} {_FROM} where j.tenant_id = %s and j.id = %s"
                + (" for update of j" if lock else ""), (tenant_id, job_id))
    return cur.fetchone()


def _notify(cur: Any, tenant_id: str, row: dict[str, Any], text: str, by: Optional[str] = None) -> None:
    if row.get("conversation_id"):
        opportunities._add_message(cur, tenant_id, str(row["conversation_id"]), "outbound", text,
                                   {"type": "delivery", "by": by, "job_id": str(row["id"])})


def _first_name(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    name = email.split("@")[0].split(".")[0].split("_")[0]
    return name[:1].upper() + name[1:20] if name.isalpha() else None


# --- Panel (dueño / empleado) ---------------------------------------------------------------
def drivers(cur: Any, tenant_id: str) -> list[dict[str, Any]]:
    cur.execute("select m.user_id, m.role, u.email from memberships m join auth.users u on u.id = m.user_id "
                "where m.tenant_id = %s order by m.role = 'driver' desc, u.email", (tenant_id,))
    return [{"user_id": str(r["user_id"]), "email": r["email"], "role": r["role"]} for r in cur.fetchall()]


def board(cur: Any, tenant_id: str, day: date) -> dict[str, Any]:
    cur.execute(f"select {_COLS} {_FROM} where j.tenant_id = %s and j.scheduled_date = %s "
                "order by j.time_window, o.number", (tenant_id, day))
    jobs = [_view(cur, tenant_id, r) for r in cur.fetchall()]
    # Pedidos pagados con envío a domicilio que todavía no tienen una entrega activa ni están entregados.
    cur.execute("select o.id, o.number, o.status, o.total, o.paid_at, o.delivery_address, o.delivery_contact "
                "from orders o where o.tenant_id = %s and o.status = any(%s) and o.delivery_method = 'delivery' "
                "and not exists (select 1 from delivery_jobs j where j.tenant_id = o.tenant_id and j.order_id = o.id "
                "and j.status not in ('failed', 'cancelled')) order by o.paid_at nulls last limit 100",
                (tenant_id, list(SCHEDULABLE)))
    pending = [{"order_id": str(r["id"]), "order_number": r["number"], "status": r["status"],
                "status_label": orders.STATUS_LABELS[r["status"]], "total": float(r["total"]),
                "address": _address(r), "contact": (r["delivery_contact"] or {}).get("name") or "",
                "items": _items(cur, tenant_id, str(r["id"]))} for r in cur.fetchall()]
    return {"date": day.isoformat(), "windows": [{"id": k, "label": v} for k, v in WINDOWS.items()],
            "kinds": [{"id": k, "label": v} for k, v in KINDS.items()], "drivers": drivers(cur, tenant_id),
            "pending": pending, "jobs": jobs}


def _parse_day(value: Any) -> date:
    try:
        d = date.fromisoformat(str(value))
    except ValueError:
        raise ValueError("Elegí un día válido.") from None
    if not today() - timedelta(days=1) <= d <= today() + timedelta(days=90):
        raise ValueError("El día tiene que ser desde hoy y hasta 90 días adelante.")
    return d


def _check_driver(cur: Any, tenant_id: str, uid: Any) -> Optional[str]:
    if uid in (None, ""):
        return None
    cur.execute("select 1 from memberships where tenant_id = %s and user_id::text = %s", (tenant_id, str(uid)))
    if cur.fetchone() is None:
        raise ValueError("Esa persona no es del equipo.")
    return str(uid)


def schedule(cur: Any, tenant_id: str, uid: str, body: dict[str, Any]) -> dict[str, Any]:
    day = _parse_day(body.get("date"))
    window = body.get("window")
    kind = body.get("kind") or "delivery"
    if window not in WINDOWS or kind not in KINDS:
        raise ValueError("Elegí una franja y un tipo válidos.")
    note = (str(body.get("note") or "").strip() or None)
    if note and len(note) > 300:
        raise ValueError("La nota puede tener hasta 300 caracteres.")
    driver = _check_driver(cur, tenant_id, body.get("assigned_to"))
    cur.execute("select id, conversation_id, status, delivery_method from orders where tenant_id = %s and id::text = %s "
                "for update", (tenant_id, str(body.get("order_id"))))
    order = cur.fetchone()
    if order is None:
        raise LookupError("order")
    if order["status"] not in SCHEDULABLE or order["delivery_method"] != "delivery":
        raise ValueError("Sólo se agendan pedidos pagados con envío a domicilio.")
    cur.execute("select 1 from delivery_jobs where tenant_id = %s and order_id = %s and status not in ('failed', 'cancelled', 'done')",
                (tenant_id, order["id"]))
    if cur.fetchone():
        raise ValueError("Ese pedido ya tiene una entrega agendada.")
    cur.execute("insert into delivery_jobs (tenant_id, order_id, conversation_id, kind, scheduled_date, time_window, "
                "assigned_to, note, created_by) values (%s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
                (tenant_id, order["id"], order["conversation_id"], kind, day, window, driver, note, uid))
    job_id = str(cur.fetchone()["id"])
    row = _fetch(cur, tenant_id, job_id)
    verb = {"delivery": "te lo llevamos", "install": "vamos a instalarlo", "delivery_install": "te lo llevamos e instalamos"}[kind]
    _notify(cur, tenant_id, row, f"Tu pedido #{row['number']}: {verb} {_when(day, window)}. "
                                 "Te avisamos por acá cuando salgamos.")
    opportunities._audit(cur, tenant_id, "delivery_scheduled", job_id, {"actor": uid, "order": str(order["id"])})
    return _view(cur, tenant_id, row)


def update(cur: Any, tenant_id: str, uid: str, job_id: str, body: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Reprogramar, reasignar, cambiar la nota o cancelar (antes de salir)."""
    row = _fetch(cur, tenant_id, job_id, lock=True)
    if row is None:
        return None
    if row["status"] not in ("scheduled",) and body.get("status") != "cancelled":
        raise ValueError("Ya salieron con esta entrega: no se puede cambiar.")
    if body.get("status") == "cancelled":
        if row["status"] not in ("scheduled", "on_the_way", "arrived"):
            raise ValueError("Esta entrega ya terminó.")
        cur.execute("update delivery_jobs set status = 'cancelled', updated_at = now() where tenant_id = %s and id = %s",
                    (tenant_id, job_id))
        opportunities._audit(cur, tenant_id, "delivery_cancelled", job_id, {"actor": uid})
        return _view(cur, tenant_id, _fetch(cur, tenant_id, job_id))
    day = _parse_day(body["date"]) if "date" in body else row["scheduled_date"]
    window = body.get("window", row["time_window"])
    if window not in WINDOWS:
        raise ValueError("Franja inválida.")
    driver = _check_driver(cur, tenant_id, body["assigned_to"]) if "assigned_to" in body else row["assigned_to"]
    note = (str(body.get("note") or "").strip()[:300] or None) if "note" in body else row["note"]
    cur.execute("update delivery_jobs set scheduled_date = %s, time_window = %s, assigned_to = %s, note = %s, "
                "updated_at = now() where tenant_id = %s and id = %s", (day, window, driver, note, tenant_id, job_id))
    if (day, window) != (row["scheduled_date"], row["time_window"]):
        _notify(cur, tenant_id, row, f"Cambiamos el día de tu pedido #{row['number']}: {_when(day, window)}.")
    opportunities._audit(cur, tenant_id, "delivery_updated", job_id, {"actor": uid})
    return _view(cur, tenant_id, _fetch(cur, tenant_id, job_id))


# --- Hoja de ruta (repartidor) --------------------------------------------------------------
def route(cur: Any, tenant_id: str, uid: str, day: date) -> list[dict[str, Any]]:
    cur.execute(f"select {_COLS} {_FROM} where j.tenant_id = %s and j.assigned_to = %s and j.scheduled_date = %s "
                "and j.status <> 'cancelled' order by j.status in ('done', 'failed'), j.time_window, o.number",
                (tenant_id, uid, day))
    return [_view(cur, tenant_id, r, driver=True) for r in cur.fetchall()]


def _mine(cur: Any, tenant_id: str, uid: str, role: str, job_id: str) -> dict[str, Any]:
    row = _fetch(cur, tenant_id, job_id, lock=True)
    # El repartidor sólo toca lo suyo; dueño y empleados pueden marcar cualquiera (p. ej. si avisan por teléfono).
    if row is None or row["status"] == "cancelled" or (role == "driver" and str(row["assigned_to"]) != uid):
        raise LookupError("job")
    return row


def _order_to(cur: Any, tenant_id: str, order_id: str, target: str) -> None:
    """Avanza el pedido paso a paso hasta `target` (despachado → en camino → entregado)."""
    path = {"DISPATCHED": ["DISPATCHED"], "IN_TRANSIT": ["DISPATCHED", "IN_TRANSIT"],
            "DELIVERED": ["DISPATCHED", "IN_TRANSIT", "DELIVERED"]}[target]
    order = ["PAID", "PREPARING", "DISPATCHED", "IN_TRANSIT", "DELIVERED"]
    cur.execute("select status from orders where tenant_id = %s and id = %s", (tenant_id, order_id))
    current = cur.fetchone()["status"]
    for step in path:
        if current in order and order.index(step) > order.index(current) and step in orders.FULFILLMENT_NEXT.get(current, set()):
            orders._advance(cur, tenant_id, order_id, step)
            current = step


def step(cur: Any, tenant_id: str, uid: str, role: str, email: Optional[str], job_id: str,
         body: dict[str, Any]) -> dict[str, Any]:
    row = _mine(cur, tenant_id, uid, role, job_id)
    new = body.get("status")
    if new not in NEXT.get(row["status"], set()):
        raise ValueError("Ese paso no corresponde ahora.")
    by = _first_name(email)
    n = row["number"]
    if new == "on_the_way":
        try:
            eta = int(body.get("eta_minutes") or 0) or None
        except (TypeError, ValueError):
            eta = None
        if eta is not None and not 1 <= eta <= 600:
            raise ValueError("La demora tiene que estar entre 1 y 600 minutos.")
        cur.execute("update delivery_jobs set status = 'on_the_way', eta_minutes = %s, started_at = now(), updated_at = now() "
                    "where tenant_id = %s and id = %s", (eta, tenant_id, job_id))
        _order_to(cur, tenant_id, str(row["order_id"]), "IN_TRANSIT")
        _notify(cur, tenant_id, row, f"¡Salimos con tu pedido #{n}!" + (f" Llegamos en unos {eta} minutos." if eta else ""), by)
    elif new == "arrived":
        cur.execute("update delivery_jobs set status = 'arrived', arrived_at = now(), updated_at = now() "
                    "where tenant_id = %s and id = %s", (tenant_id, job_id))
        _notify(cur, tenant_id, row, f"Llegamos con tu pedido #{n} a {_address(row) or 'la dirección'}. ¿Nos abrís?", by)
    elif new == "done":
        cur.execute("update delivery_jobs set status = 'done', finished_at = now(), updated_at = now() "
                    "where tenant_id = %s and id = %s", (tenant_id, job_id))
        _order_to(cur, tenant_id, str(row["order_id"]), "DELIVERED")
        verb = {"delivery": "Entregamos", "install": "Instalamos", "delivery_install": "Entregamos e instalamos"}[row["kind"]]
        _notify(cur, tenant_id, row, f"{verb} tu pedido #{n}. ¡Gracias por tu compra!", by)
    else:   # failed
        reason = " ".join(str(body.get("reason") or "").split())[:200]
        if not reason:
            raise ValueError("Contá brevemente qué pasó.")
        cur.execute("update delivery_jobs set status = 'failed', failure_reason = %s, finished_at = now(), updated_at = now() "
                    "where tenant_id = %s and id = %s", (reason, tenant_id, job_id))
        _notify(cur, tenant_id, row, f"No pudimos completar la entrega de tu pedido #{n} ({reason}). "
                                     "Te escribimos para coordinar otro día.", by)
    opportunities._audit(cur, tenant_id, f"delivery_{new}", job_id, {"actor": uid})
    return _view(cur, tenant_id, _fetch(cur, tenant_id, job_id), driver=True)


def message(cur: Any, tenant_id: str, uid: str, role: str, email: Optional[str], job_id: str, text: Any) -> None:
    """Mensaje corto del repartidor a SU cliente (p. ej. «estoy en la puerta, toco timbre»). Sólo con
    la entrega en curso o agendada; queda en la charla del cliente con el nombre de quien escribe."""
    row = _mine(cur, tenant_id, uid, role, job_id)
    if row["status"] not in ("scheduled", "on_the_way", "arrived"):
        raise ValueError("Esta entrega ya terminó.")
    text = " ".join(str(text or "").split())
    if not 1 <= len(text) <= MAX_MESSAGE:
        raise ValueError(f"El mensaje tiene que tener entre 1 y {MAX_MESSAGE} caracteres.")
    _notify(cur, tenant_id, row, text, _first_name(email) or "Reparto")
    opportunities._audit(cur, tenant_id, "delivery_message", job_id, {"actor": uid, "chars": len(text)})

