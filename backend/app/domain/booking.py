"""Turnos: el negocio configura servicios (con duración), días y horarios, y cuántos turnos acepta a
la vez; el cliente elige en el chat uno de los próximos horarios LIBRES y queda reservado.

- Nunca se ofrece un horario lleno: se calcula contra los turnos reservados y, al reservar, se vuelve
  a verificar con un bloqueo por negocio (dos clientes no se llevan el último lugar).
- Hora de Argentina. Se ofrecen turnos desde 2 horas después de ahora y hasta 14 días.
- Configuración en las políticas del perfil (`booking`):
  {"services": [{"name": "Medición", "minutes": 60}], "hours": {"0": [["09:00","18:00"]], ...},
   "capacity": 1}  — días 0 = lunes … 6 = domingo.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from . import opportunities, webhooks
from .inventory import normalize

TZ = ZoneInfo("America/Argentina/Buenos_Aires")
LEAD = timedelta(hours=2)
HORIZON_DAYS = 14
MAX_SERVICES = 6
_DAYS = {"lun": 0, "mar": 1, "mie": 2, "jue": 3, "vie": 4, "sab": 5, "dom": 6}
_DAY_NAMES = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


# --- Configuración ---------------------------------------------------------------------
def _hhmm(text: str) -> str:
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?", text.strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2) or 0) > 59:
        raise ValueError(f"Hora inválida: «{text}». Usá 9, 9:30 o 18:00.")
    return f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"


def parse_hours(raw: Any) -> dict[str, list[list[str]]]:
    """«lun-vie 9-18; sab 9-13» -> {"0": [["09:00","18:00"]], …}. También acepta el dict guardado."""
    if isinstance(raw, dict):
        items = raw
    else:
        items = {}
        for part in re.split(r"[;\n]+", str(raw or "")):
            part = normalize(part).strip()
            if not part:
                continue
            m = re.fullmatch(r"([a-z]{3})(?:\s*-\s*([a-z]{3}))?\s+(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)", part)
            if not m or m.group(1) not in _DAYS or (m.group(2) and m.group(2) not in _DAYS):
                raise ValueError(f"No entiendo «{part}». Ejemplo: lun-vie 9-18; sab 9-13")
            a, b = _DAYS[m.group(1)], _DAYS[m.group(2) or m.group(1)]
            for d in range(a, b + 1):
                items.setdefault(str(d), []).append([m.group(3), m.group(4)])
    out: dict[str, list[list[str]]] = {}
    for day, ranges in items.items():
        if day not in {str(d) for d in range(7)}:
            raise ValueError("Día inválido en los horarios.")
        for start, end in ranges:
            s, e = _hhmm(start), _hhmm(end)
            if s >= e:
                raise ValueError("Cada horario tiene que terminar después de empezar.")
            out.setdefault(day, []).append([s, e])
    return out


def validate(raw: Any) -> Optional[dict[str, Any]]:
    """Normaliza la configuración de turnos (o None si no hay servicios)."""
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Configuración de turnos inválida.")
    services = raw.get("services")
    if isinstance(services, str):     # «Medición: 60, Retiro: 15»
        parsed = []
        for part in services.split(","):
            if part.strip():
                name, _, mins = part.partition(":")
                parsed.append({"name": name.strip(), "minutes": mins.strip() or "30"})
        services = parsed
    clean = []
    if not isinstance(services, list):
        raise ValueError("Servicios de turnos inválidos.")
    for s in services:
        if not isinstance(s, dict):
            raise ValueError("Cada servicio necesita nombre y duración (ej.: Retiro: 15).")
        name = str(s.get("name") or "").strip()[:60]
        try:
            minutes = int(s.get("minutes"))
        except (TypeError, ValueError):
            raise ValueError(f"Duración inválida para «{name}» (en minutos).") from None
        if not name or not 10 <= minutes <= 480:
            raise ValueError("Cada servicio necesita nombre y una duración de 10 a 480 minutos.")
        clean.append({"name": name, "minutes": minutes})
    if not clean:
        return None
    if len(clean) > MAX_SERVICES:
        raise ValueError(f"Hasta {MAX_SERVICES} servicios.")
    hours = parse_hours(raw.get("hours"))
    if not hours:
        raise ValueError("Cargá días y horarios para los turnos (ej.: lun-vie 9-18).")
    try:
        capacity = int(raw["capacity"]) if raw.get("capacity") not in (None, "") else 1
    except (TypeError, ValueError):
        capacity = 0
    if not 1 <= capacity <= 20:
        raise ValueError("Turnos simultáneos: de 1 a 20.")
    return {"services": clean, "hours": hours, "capacity": capacity}


def config(profile: dict[str, Any]) -> Optional[dict[str, Any]]:
    return (profile.get("policies") or {}).get("booking")


def pick_service(cfg: dict[str, Any], text: str) -> Optional[dict[str, Any]]:
    if len(cfg["services"]) == 1:
        return cfg["services"][0]
    for s in cfg["services"]:
        words = [w for w in re.findall(r"[a-z0-9]+", normalize(s["name"])) if len(w) > 3]
        if any(re.search(rf"\b{w[:-1]}\w*", text) for w in words):
            return s
    return None


# --- Disponibilidad y reserva ----------------------------------------------------------
def _booked(cur: Any, tenant_id: str, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    cur.execute("select starts_at, ends_at from appointments where tenant_id = %s and status = 'booked' "
                "and starts_at < %s and ends_at > %s", (tenant_id, end, start))
    return [(r["starts_at"], r["ends_at"]) for r in cur.fetchall()]


def free_slots(cur: Any, tenant_id: str, cfg: dict[str, Any], service: dict[str, Any], limit: int = 6,
               now: Optional[datetime] = None) -> list[datetime]:
    now = (now or datetime.now(TZ)).astimezone(TZ)
    first, horizon = now + LEAD, now + timedelta(days=HORIZON_DAYS)
    taken = _booked(cur, tenant_id, now, horizon)
    step = timedelta(minutes=service["minutes"])
    out: list[datetime] = []
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    while day < horizon and len(out) < limit:
        for start_s, end_s in cfg["hours"].get(str(day.weekday()), []):
            h1, m1 = map(int, start_s.split(":"))
            h2, m2 = map(int, end_s.split(":"))
            t, close = day.replace(hour=h1, minute=m1), day.replace(hour=h2, minute=m2)
            while t + step <= close and len(out) < limit:
                if t >= first and sum(1 for a, b in taken if a < t + step and b > t) < cfg["capacity"]:
                    out.append(t)
                t += step
        day += timedelta(days=1)
    return out


def book(cur: Any, tenant_id: str, conversation_id: str, cfg: dict[str, Any], service: dict[str, Any],
         start: datetime, now: Optional[datetime] = None) -> dict[str, Any]:
    """Reserva si el horario sigue con anticipación suficiente y con lugar (bloqueo por negocio).
    Si no, {"error": "too_soon"} (quedó muy cerca) o {"error": "full"} (se ocupó)."""
    cur.execute("select pg_advisory_xact_lock(hashtext('booking:' || %s))", (tenant_id,))
    end = start + timedelta(minutes=service["minutes"])
    if start < (now or datetime.now(TZ)) + LEAD - timedelta(minutes=1):
        return {"error": "too_soon"}
    if len(_booked(cur, tenant_id, start, end)) >= cfg["capacity"]:
        return {"error": "full"}
    cur.execute("insert into appointments (tenant_id, conversation_id, service, starts_at, ends_at) "
                "values (%s, %s, %s, %s, %s) returning id", (tenant_id, conversation_id, service["name"], start, end))
    appt_id = str(cur.fetchone()["id"])
    opportunities._audit(cur, tenant_id, "appointment_booked", appt_id, {"service": service["name"]})
    webhooks.enqueue(cur, tenant_id, "appointment.booked", {"appointment_id": appt_id, "service": service["name"],
                                                            "starts_at": start.isoformat(), "ends_at": end.isoformat(),
                                                            "conversation_id": conversation_id})
    return {"id": appt_id, "service": service["name"], "starts_at": start.isoformat(), "ends_at": end.isoformat()}


def label(dt: datetime) -> str:
    dt = dt.astimezone(TZ)
    return f"{_DAY_NAMES[dt.weekday()]} {dt.day}/{dt.month} {dt:%H:%M}"


def upcoming(cur: Any, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
    cur.execute("select id, conversation_id, service, starts_at, ends_at from appointments where tenant_id = %s "
                "and status = 'booked' and ends_at >= now() order by starts_at limit %s", (tenant_id, limit))
    return [{"id": str(r["id"]), "conversation_id": str(r["conversation_id"]) if r["conversation_id"] else None,
             "service": r["service"], "starts_at": r["starts_at"].isoformat(), "ends_at": r["ends_at"].isoformat(),
             "label": label(r["starts_at"])} for r in cur.fetchall()]


def cancel(cur: Any, tenant_id: str, uid: str, appointment_id: str) -> bool:
    cur.execute("update appointments set status = 'cancelled', cancelled_at = now(), cancelled_by = %s "
                "where tenant_id = %s and id = %s and status = 'booked'", (uid, tenant_id, appointment_id))
    return bool(cur.rowcount)
