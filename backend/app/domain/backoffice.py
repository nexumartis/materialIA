"""Operaciones del panel del negocio (catálogo, stock, importación CSV, pedidos).

Todas reciben el cursor de `user_tx` (rol app_user, RLS efectivo) y el tenant derivado de la
membresía: además del filtro explícito por tenant, la base impide tocar datos de otro negocio.
"""
from __future__ import annotations

import csv
import io
import json
import math
from typing import Any, Optional

import psycopg

from . import inventory, orders

MAX_ROWS = 2000
_TRUE = {"si", "sí", "true", "1", "x", "yes", "s"}
_SPEC_COLUMNS = ("color", "ambiente", "tipo", "material", "medida")


def list_catalog(cur: Any, tenant_id: str) -> list[dict[str, Any]]:
    cur.execute(
        "select c.id, c.active from catalog_items c where c.tenant_id = %s", (tenant_id,))
    active = {str(r["id"]): r["active"] for r in cur.fetchall()}
    # Activos con precio y disponible vigentes (misma consulta que usa el agente)...
    items = inventory._offers(cur, tenant_id, limit=MAX_ROWS)
    seen = {o["id"] for o in items}
    # ...más los inactivos, para poder reactivarlos.
    cur.execute(
        "select id, sku, name, brand, category, pricing_mode, specs_json, currency, description, "
        "image_url, unit from catalog_items where tenant_id = %s and active = false", (tenant_id,))
    for r in cur.fetchall():
        if str(r["id"]) not in seen:
            items.append({**inventory._offer({**r, "price": None, "available": 0, "stock_tracked": False})})
    for o in items:
        o["active"] = active.get(o["id"], True)
        o.update(_stock(cur, tenant_id, o["id"]))
    return sorted(items, key=lambda o: (not o["active"], o["name"]))


def _stock(cur: Any, tenant_id: str, item_id: str) -> dict[str, int]:
    cur.execute("select on_hand, reserved from stock_levels where tenant_id = %s and item_id = %s",
                (tenant_id, item_id))
    r = cur.fetchone()
    return {"on_hand": r["on_hand"], "reserved": r["reserved"]} if r else {"on_hand": 0, "reserved": 0}


def _set_price(cur: Any, tenant_id: str, item_id: str, amount: float) -> None:
    """Precio vigente desde hoy. Lo ya cotizado/vendido conserva su snapshot."""
    cur.execute(
        "update price_entries set amount = %s, valid_until = null, updated_at = now() "
        "where tenant_id = %s and item_id = %s and valid_from = current_date",
        (amount, tenant_id, item_id))
    if cur.rowcount == 0:
        cur.execute(
            "insert into price_entries (tenant_id, item_id, amount, valid_from) values (%s, %s, %s, current_date)",
            (tenant_id, item_id, amount))


def _set_stock(cur: Any, tenant_id: str, item_id: str, on_hand: int) -> None:
    """Stock físico contado por el negocio. Nunca por debajo de lo apartado por pedidos en curso."""
    cur.execute(
        "select on_hand, reserved from stock_levels where tenant_id = %s and item_id = %s for update",
        (tenant_id, item_id))
    r = cur.fetchone()
    if r is None:
        cur.execute("insert into stock_levels (tenant_id, item_id, on_hand) values (%s, %s, %s)",
                    (tenant_id, item_id, on_hand))
        delta = on_hand
    else:
        if on_hand < r["reserved"]:
            raise ValueError(f"hay {r['reserved']} apartadas por pedidos en curso; el stock no puede ser menor")
        cur.execute("update stock_levels set on_hand = %s, updated_at = now() where tenant_id = %s and item_id = %s",
                    (on_hand, tenant_id, item_id))
        delta = on_hand - r["on_hand"]
    if delta:
        inventory._movement(cur, tenant_id, item_id, None, "adjust", delta, 0)


def update_product(cur: Any, tenant_id: str, item_id: str, price: Optional[float] = None,
                   stock: Optional[int] = None, active: Optional[bool] = None) -> Optional[dict[str, Any]]:
    cur.execute("select pricing_mode from catalog_items where tenant_id = %s and id = %s",
                (tenant_id, item_id))
    item = cur.fetchone()
    if item is None:
        return None
    if price is not None:
        if price < 0:
            raise ValueError("el precio no puede ser negativo")
        _set_price(cur, tenant_id, item_id, price)
    if stock is not None:
        if stock < 0:
            raise ValueError("el stock no puede ser negativo")
        _set_stock(cur, tenant_id, item_id, stock)
    if active is not None:
        cur.execute("update catalog_items set active = %s, updated_at = now() where tenant_id = %s and id = %s",
                    (active, tenant_id, item_id))
    return next((o for o in list_catalog(cur, tenant_id) if o["id"] == item_id), None)


def _number(raw: str, field: str, integer: bool = False) -> Optional[float]:
    raw = (raw or "").strip().replace("$", "").replace(" ", "")
    if not raw:
        return None
    # Formato argentino: 89.900,50 -> 89900.50
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif raw.count(".") > 1 or (raw.count(".") == 1 and len(raw.split(".")[1]) == 3):
        raw = raw.replace(".", "")
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{field} inválido: {raw!r}")
    # Una celda rara («1e999», un número gigante) es un error de ESA fila, no de toda la importación.
    if not math.isfinite(value) or value > (MAX_STOCK if integer else MAX_PRICE):
        raise ValueError(f"{field} fuera de rango: {raw!r}")
    if value < 0:
        raise ValueError(f"{field} no puede ser negativo")
    if integer and value != int(value):
        raise ValueError(f"{field} debe ser un número entero")
    return value


MAX_PRICE = 99_999_999_999.99    # numeric(14,2)
MAX_STOCK = 10_000_000


def import_csv(cur: Any, tenant_id: str, text: str, from_sheet: bool = False) -> dict[str, Any]:
    """Alta/actualización del catálogo desde CSV (upsert por sku). Cada fila se aplica en su
    propio savepoint: una fila con error no frena al resto y se informa con su número.

    `from_sheet` (Google Sheets conectada): el stock de una fila se aplica sólo si cambió desde la
    última lectura de la planilla (`sheet_stock`), para no borrar lo vendido. Informa además los
    SKU del catálogo que ya no están en la planilla (no se pausan solos)."""
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("El archivo está vacío.")
    headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    missing = [h for h in ("sku", "nombre") if h not in headers]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}.")
    created = updated = 0
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    changes = {"prices": 0, "stock": 0}
    seen: set[str] = set()
    for line, raw in enumerate(reader, start=2):
        if line - 1 > MAX_ROWS:
            errors.append({"fila": line, "error": f"máximo {MAX_ROWS} filas por archivo"})
            break
        row = {k: (raw.get(orig) or "").strip() for k, orig in headers.items()}
        if not any(row.values()):
            continue
        seen.add(row.get("sku", "")[:64])
        try:
            with cur.connection.transaction():
                was_new, warning = _import_row(cur, tenant_id, row, from_sheet, changes)
            created += was_new
            updated += not was_new
            if warning:
                warnings.append({"fila": line, "sku": row.get("sku"), "error": warning})
        except (ValueError, psycopg.DataError) as exc:   # DataError: valor que la base no acepta
            errors.append({"fila": line, "sku": row.get("sku"), "error": str(exc).splitlines()[0]})
    result: dict[str, Any] = {"created": created, "updated": updated, "errors": errors + warnings}
    if from_sheet:
        result["changes"] = changes            # para auditar la sincronización (no cambia la importación manual)
        cur.execute("select sku from catalog_items where tenant_id = %s and active and not (sku = any(%s)) "
                    "order by sku", (tenant_id, list(seen)))
        missing = [r["sku"] for r in cur.fetchall()]
        result["missing"] = {"count": len(missing), "skus": missing[:20]}
    return result


def _import_row(cur: Any, tenant_id: str, row: dict[str, str], from_sheet: bool = False,
                changes: Optional[dict[str, int]] = None) -> tuple[bool, Optional[str]]:
    """Aplica una fila. Devuelve (era nuevo, aviso). Aviso: el stock de la planilla no se pudo
    aplicar (queda por debajo de lo apartado); el resto de la fila sí se aplicó."""
    changes = changes if changes is not None else {"prices": 0, "stock": 0}
    sku, name = row.get("sku", ""), row.get("nombre", "")
    if not sku or not name:
        raise ValueError("sku y nombre son obligatorios")
    custom = row.get("a_pedido", "").lower() in _TRUE
    price = _number(row.get("precio", ""), "precio")
    stock = _number(row.get("stock", ""), "stock", integer=True)
    if not custom and price is None:
        raise ValueError("falta el precio (o marcá a_pedido = si)")
    active = row.get("activo", "").lower() not in {"no", "false", "0", "n"}
    photo = row.get("foto_url", "")
    if photo and not photo.startswith(("https://", "http://", "/static/")):
        raise ValueError("foto_url debe ser un link https://")
    specs = {k: row[k] for k in _SPEC_COLUMNS if row.get(k)}
    cur.execute(
        "insert into catalog_items (tenant_id, sku, name, category, pricing_mode, specs_json, brand, "
        "description, image_url, active) values (%(t)s, %(sku)s, %(name)s, %(cat)s, %(mode)s, %(specs)s::jsonb, "
        "%(brand)s, %(desc)s, %(img)s, %(active)s) "
        "on conflict (tenant_id, sku) do update set name = excluded.name, category = excluded.category, "
        "pricing_mode = excluded.pricing_mode, specs_json = excluded.specs_json, brand = excluded.brand, "
        "description = excluded.description, image_url = coalesce(excluded.image_url, catalog_items.image_url), "
        "active = excluded.active, updated_at = now() "
        "returning id, (xmax = 0) as inserted",
        {"t": tenant_id, "sku": sku[:64], "name": name[:200], "cat": (row.get("categoria") or "general")[:80],
         "mode": "custom_quote" if custom else "fixed", "specs": json.dumps(specs),
         "brand": row.get("marca") or None, "desc": row.get("descripcion", "")[:1000],
         "img": photo or None, "active": active},
    )
    r = cur.fetchone()
    item_id = str(r["id"])
    if price is not None:
        current = inventory._offer_by_id(cur, tenant_id, item_id)
        if current is None or current["price"] is None or abs(current["price"] - price) > 0.005:
            _set_price(cur, tenant_id, item_id, price)
            changes["prices"] += 1
    warning = None
    if stock is not None:
        if not from_sheet:
            _set_stock(cur, tenant_id, item_id, int(stock))
            changes["stock"] += 1
        else:
            # Planilla: el número manda sólo si el dueño lo cambió desde la última lectura.
            cur.execute("select sheet_stock from catalog_items where tenant_id = %s and id = %s", (tenant_id, item_id))
            if cur.fetchone()["sheet_stock"] != int(stock):
                try:
                    with cur.connection.transaction():
                        _set_stock(cur, tenant_id, item_id, int(stock))
                        cur.execute("update catalog_items set sheet_stock = %s where tenant_id = %s and id = %s",
                                    (int(stock), tenant_id, item_id))
                    changes["stock"] += 1
                except ValueError as exc:
                    # Precio y datos ya se aplicaron; el stock se reintenta en la próxima lectura.
                    warning = f"stock no aplicado: {exc}"
    return bool(r["inserted"]), warning


# --- Pedidos -------------------------------------------------------------------
def list_orders(cur: Any, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
    cur.execute(
        f"select {orders._ORDER_COLUMNS} from orders where tenant_id = %s and status <> 'CART_OPEN' "
        "order by created_at desc limit %s", (tenant_id, limit))
    return [orders._view(cur, r) for r in cur.fetchall()]


def advance_order(cur: Any, tenant_id: str, order_id: str, new_status: str) -> Optional[dict[str, Any]]:
    return orders._advance(cur, tenant_id, order_id, new_status)
