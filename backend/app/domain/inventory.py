"""Ofertas (producto + precio vigente + disponible) y stock consistente bajo concurrencia.

Reglas (diseño §5):
- Disponible = on_hand - reserved, leído en vivo; el agente nunca recuerda cantidades.
- Apartar es UN update condicional (`... where on_hand - reserved >= q`): sin leer-y-escribir,
  Postgres serializa compras simultáneas de la misma fila y sólo una se lleva la última unidad.
- Varias líneas se apartan en orden de item_id dentro de la transacción del llamador: todo o
  nada (OutOfStock aborta la transacción) y sin deadlocks entre carritos cruzados.
- Las restricciones de 0004 (`reserved <= on_hand`, no negativos) son la última barrera.
Las funciones `_x(cur, ...)` componen dentro de la transacción del llamador.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Optional

from ..config import settings
from ..db import tenant_tx


class OutOfStock(Exception):
    def __init__(self, item_id: str, requested: int, available: int):
        super().__init__(f"sin stock suficiente para {item_id}: pide {requested}, hay {available}")
        self.item_id = item_id
        self.requested = requested
        self.available = available


def normalize(text: str) -> str:
    """minúsculas y sin acentos (la búsqueda compara así ambos lados)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


# Precio vigente hoy (mismo criterio que catalog.get_price) y disponible, en una sola consulta.
_OFFER_SELECT = """
select c.id, c.sku, c.name, c.brand, c.category, c.pricing_mode, c.specs_json, c.currency,
       c.description, c.image_url, c.unit,
       p.amount as price,
       coalesce(s.on_hand - s.reserved, 0) as available,
       (s.item_id is not null) as stock_tracked
from catalog_items c
left join lateral (
    select amount from price_entries pe
    where pe.tenant_id = c.tenant_id and pe.item_id = c.id
      and pe.valid_from <= current_date
      and (pe.valid_until is null or pe.valid_until >= current_date)
    order by pe.valid_from desc limit 1
) p on true
left join stock_levels s on s.tenant_id = c.tenant_id and s.item_id = c.id
where c.tenant_id = %(tenant)s and c.active = true
"""

# Texto donde se busca: nombre, marca, categoría y ficha, normalizado como `normalize`.
_HAYSTACK = ("translate(lower(c.name || ' ' || coalesce(c.brand, '') || ' ' || c.category"
             " || ' ' || c.specs_json::text), 'áéíóúüñ', 'aeiouun')")


def _absolute(url: Optional[str]) -> Optional[str]:
    """Las fotos propias se guardan como ruta (/static/...); los canales necesitan URL absoluta."""
    if url and url.startswith("/"):
        return settings.public_base_url.rstrip("/") + url
    return url


def _offer(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]), "sku": row["sku"], "name": row["name"], "brand": row["brand"],
        "category": row["category"], "pricing_mode": row["pricing_mode"],
        "specs": row["specs_json"] or {}, "currency": row["currency"],
        "description": row["description"], "image_url": _absolute(row["image_url"]), "unit": row["unit"],
        "price": float(row["price"]) if row["price"] is not None else None,
        "available": int(row["available"]), "stock_tracked": bool(row["stock_tracked"]),
    }


def _offers(cur: Any, tenant_id: str, *, ids: Optional[Iterable[str]] = None,
            keywords: Iterable[str] = (), color: Optional[str] = None,
            max_price: Optional[float] = None, category: Optional[str] = None,
            ambiente: Optional[str] = None, in_stock_only: bool = False,
            exclude: Iterable[str] = (), limit: int = 10) -> list[dict[str, Any]]:
    """Ofertas activas de la empresa. Con `keywords`, devuelve sólo las que coinciden con MÁS
    palabras (todas, si alguna oferta las tiene todas); ordena por precio."""
    sql = [_OFFER_SELECT]
    params: dict[str, Any] = {"tenant": tenant_id, "limit": limit}
    if ids is not None:
        sql.append("and c.id = any(%(ids)s::uuid[])")
        params["ids"] = list(ids)
    if color:
        sql.append("and c.specs_json->>'color' = %(color)s")
        params["color"] = color
    if category:
        sql.append("and c.category = %(category)s")
        params["category"] = category
    if ambiente:
        sql.append("and translate(lower(c.specs_json->>'ambiente'), 'ñ', 'n') = %(ambiente)s")
        params["ambiente"] = normalize(ambiente)
    if max_price is not None:
        sql.append("and p.amount <= %(max_price)s")
        params["max_price"] = max_price
    if in_stock_only:
        sql.append("and coalesce(s.on_hand - s.reserved, 0) > 0")
    exclude = list(exclude)
    if exclude:
        sql.append("and c.id <> all(%(exclude)s::uuid[])")
        params["exclude"] = exclude

    kws = [normalize(k) for k in keywords if k]
    if kws:
        score = " + ".join(f"(case when {_HAYSTACK} like %(kw{i})s then 1 else 0 end)"
                           for i in range(len(kws)))
        for i, k in enumerate(kws):
            params[f"kw{i}"] = f"%{k}%"
        query = (f"select base.*, ({score}) as score from catalog_items c "
                 f"join ({chr(10).join(sql)}) base on base.id = c.id "
                 f"where ({score}) > 0 order by score desc, (base.available > 0) desc, base.price nulls last, base.name "
                 f"limit %(limit)s")
        cur.execute(query, params)
        rows = cur.fetchall()
        if not rows:
            return []
        best = rows[0]["score"]
        return [_offer(r) for r in rows if r["score"] == best]

    sql.append("order by (coalesce(s.on_hand - s.reserved, 0) > 0) desc, p.amount nulls last, c.name "
               "limit %(limit)s")
    cur.execute("\n".join(sql), params)
    return [_offer(r) for r in cur.fetchall()]


def offers(tenant_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    with tenant_tx(tenant_id) as cur:
        return _offers(cur, tenant_id, **kwargs)


def _offer_by_id(cur: Any, tenant_id: str, item_id: str) -> Optional[dict[str, Any]]:
    found = _offers(cur, tenant_id, ids=[item_id], limit=1)
    return found[0] if found else None


# --- Movimientos de stock ---------------------------------------------------
def _movement(cur: Any, tenant_id: str, item_id: str, order_id: Optional[str], kind: str,
              d_on_hand: int, d_reserved: int) -> None:
    cur.execute(
        "insert into stock_movements (tenant_id, item_id, order_id, kind, delta_on_hand, delta_reserved) "
        "values (%s, %s, %s, %s, %s, %s)",
        (tenant_id, item_id, order_id, kind, d_on_hand, d_reserved),
    )


def _sorted(lines: Iterable[tuple[str, int]]) -> list[tuple[str, int]]:
    return sorted(((str(i), int(q)) for i, q in lines), key=lambda line: line[0])


def _reserve(cur: Any, tenant_id: str, order_id: str, lines: Iterable[tuple[str, int]]) -> None:
    """Aparta todas las líneas o ninguna: OutOfStock aborta la transacción del llamador."""
    for item_id, qty in _sorted(lines):
        cur.execute(
            "update stock_levels set reserved = reserved + %(q)s, updated_at = now() "
            "where tenant_id = %(t)s and item_id = %(i)s and on_hand - reserved >= %(q)s "
            "returning on_hand",
            {"q": qty, "t": tenant_id, "i": item_id},
        )
        if cur.fetchone() is None:
            cur.execute(
                "select coalesce(max(on_hand - reserved), 0) as available from stock_levels "
                "where tenant_id = %s and item_id = %s",
                (tenant_id, item_id),
            )
            raise OutOfStock(item_id, qty, int(cur.fetchone()["available"]))
        _movement(cur, tenant_id, item_id, order_id, "reserve", 0, qty)


def _release(cur: Any, tenant_id: str, order_id: str, lines: Iterable[tuple[str, int]]) -> None:
    for item_id, qty in _sorted(lines):
        cur.execute(
            "update stock_levels set reserved = reserved - %s, updated_at = now() "
            "where tenant_id = %s and item_id = %s",
            (qty, tenant_id, item_id),
        )
        _movement(cur, tenant_id, item_id, order_id, "release", 0, -qty)


def _sell(cur: Any, tenant_id: str, order_id: str, lines: Iterable[tuple[str, int]]) -> None:
    """Convierte lo apartado en venta: baja on_hand y reserved (pago confirmado)."""
    for item_id, qty in _sorted(lines):
        cur.execute(
            "update stock_levels set on_hand = on_hand - %s, reserved = reserved - %s, "
            "updated_at = now() where tenant_id = %s and item_id = %s",
            (qty, qty, tenant_id, item_id),
        )
        _movement(cur, tenant_id, item_id, order_id, "sale", -qty, -qty)


def restock(tenant_id: str, item_id: str, qty: int) -> int:
    """Ingreso de mercadería (admin/tests). Devuelve el nuevo on_hand."""
    if qty <= 0:
        raise ValueError("la cantidad a ingresar debe ser positiva")
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            "insert into stock_levels (tenant_id, item_id, on_hand) values (%s, %s, %s) "
            "on conflict (tenant_id, item_id) do update "
            "set on_hand = stock_levels.on_hand + excluded.on_hand, updated_at = now() "
            "returning on_hand",
            (tenant_id, item_id, qty),
        )
        on_hand = int(cur.fetchone()["on_hand"])
        _movement(cur, tenant_id, item_id, None, "restock", qty, 0)
    return on_hand


def vocabulary(tenant_id: str) -> set[str]:
    """Palabras del catálogo activo de la empresa (normalizadas), para tolerar errores de tipeo."""
    with tenant_tx(tenant_id) as cur:
        cur.execute(
            f"select {_HAYSTACK} as text from catalog_items c where c.tenant_id = %s and c.active = true",
            (tenant_id,),
        )
        rows = cur.fetchall()
    words: set[str] = set()
    for r in rows:
        words.update(w for w in re.findall(r"[a-z]+", r["text"]) if len(w) >= 4)
    return words
