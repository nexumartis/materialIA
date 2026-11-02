import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type CatalogItem, type ImportResult } from "../lib/api";
import { Download, Package, Pause, Play, Upload } from "lucide-react";
import { SheetSync } from "../components/SheetSync";
import { Badge, EmptyState, PageHeader, SelectionBar, Stats } from "../components/ui";

// Plantillas CSV por rubro (mismas columnas; las vacías se pueden borrar). El rubro sale del perfil.
const COLS = "sku,nombre,categoria,marca,precio,stock,descripcion,foto_url,ficha_url,modelo,variante,color,talle,sabor,ambiente,tipo,a_pedido,activo,complementos\n";
const TEMPLATES: Record<string, string> = {
  ferreteria: COLS +
    "CAN-001,Canilla de cocina monocomando negra,griferia,Mi Marca,89900,6,Pico alto giratorio,https://...,https://.../ficha.pdf,Canilla monocomando,Negro,negro,,,cocina,monocomando,,si,FLX-001\n" +
    "CAN-002,Canilla de cocina monocomando cromo,griferia,Mi Marca,68000,10,Pico alto giratorio,https://...,,Canilla monocomando,Cromo,cromo,,,cocina,monocomando,,si,FLX-001\n" +
    "FLX-001,Flexible de acero 40 cm,griferia,Mi Marca,4500,30,,,,,,,,,,,,si,\n" +
    "INO-001,Inodoro largo blanco,sanitarios,Mi Marca,,,Se encarga a fábrica,,,,,blanco,,,baño,,si,si,\n",
  ropa: COLS +
    "REM-NEG-M,Remera básica,remeras,Mi Marca,15000,8,Algodón peinado,https://...,,Remera básica,Negra M,negro,M,,,,,si,JEA-AZ-42\n" +
    "REM-NEG-L,Remera básica,remeras,Mi Marca,15000,5,Algodón peinado,https://...,,Remera básica,Negra L,negro,L,,,,,si,JEA-AZ-42\n" +
    "JEA-AZ-42,Jean recto,pantalones,Mi Marca,45000,3,,https://...,,Jean recto,Azul 42,azul,42,,,,,si,CIN-001\n" +
    "CIN-001,Cinturón de cuero,accesorios,Mi Marca,12000,6,,,,,,marron,,,,,,si,\n" +
    "VES-001,Vestido a medida,vestidos,Mi Marca,,,Se confecciona a pedido,,,,,,,,,,si,si,\n",
  gastronomia: COLS +
    "HAM-001,Hamburguesa clásica,hamburguesas,,8500,50,Doble carne y cheddar,https://...,,,,,,,,,,si,PAP-001 GAS-001\n" +
    "PAP-001,Papas fritas,acompañamientos,,3500,80,,,,,,,,,,,,si,\n" +
    "GAS-001,Gaseosa 500 ml,bebidas,,2000,100,,,,,,,,,,,,si,\n" +
    "TOR-001,Torta brownie,postres,,22000,2,,,,,,,,chocolate,,,,si,\n" +
    "TOR-002,Torta de cumpleaños,postres,,,,Se encarga con 48 h,,,,,,,,,,si,si,\n",
  generico: COLS +
    "PROD-001,Producto de ejemplo,general,Mi Marca,10000,5,Descripción corta,https://...,,,,,,,,,,si,PROD-002\n" +
    "PROD-002,Producto complementario,general,Mi Marca,3000,10,,,,,,,,,,,,si,\n" +
    "PROD-003,Producto a pedido,general,,,,Precio y plazo los confirma una persona,,,,,,,,,,si,si,\n",
};
const RUBRO: Record<string, string> = { sanitarios: "ferreteria", ferreteria: "ferreteria", construccion: "ferreteria",
  ropa: "ropa", gastronomia: "gastronomia" };

/** Descarga la plantilla del rubro del negocio (si no se puede saber, la genérica). */
export async function downloadTemplate(businessType?: string) {
  let kind = businessType;
  if (kind === undefined) {
    try { kind = (await api.agentProfile()).business_type; } catch { kind = ""; }
  }
  const key = RUBRO[kind ?? ""] ?? "generico";
  const url = URL.createObjectURL(new Blob([TEMPLATES[key]], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `catalogo-plantilla-${key}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

/** Catálogo del negocio: importación CSV y edición de precio, stock y estado. */
const LOW_STOCK = 3;

export function Catalog() {
  const [items, setItems] = useState<CatalogItem[] | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [edit, setEdit] = useState<Record<string, { price: string; stock: string }>>({});

  const load = useCallback(() => {
    api.catalog().then(setItems).catch(() => setError("No pude cargar el catálogo."));
  }, []);
  useEffect(load, [load]);

  async function onFile(file: File) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.importCatalog(await file.text()));
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No pude importar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  async function saveRow(it: CatalogItem) {
    const e = edit[it.id];
    if (!e) return;
    const body: { price?: number; stock?: number } = {};
    if (e.price !== "" && Number(e.price) !== it.price) body.price = Number(e.price);
    if (e.stock !== "" && Number(e.stock) !== it.on_hand) body.stock = Number(e.stock);
    try {
      const updated = await api.updateProduct(it.id, body);
      setItems((list) => list?.map((x) => (x.id === it.id ? updated : x)) ?? null);
      setEdit(({ [it.id]: _, ...rest }) => rest);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No pude guardar el producto.");
    }
  }

  async function toggle(it: CatalogItem) {
    try {
      const updated = await api.updateProduct(it.id, { active: !it.active });
      setItems((list) => list?.map((x) => (x.id === it.id ? updated : x)) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No pude cambiar el estado.");
    }
  }

  const [selected, setSelected] = useState<string[]>([]);
  const [history, setHistory] = useState<CatalogItem | null>(null);
  const allIds = items?.map((it) => it.id) ?? [];
  const toggleSel = (id: string) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  async function setActive(active: boolean) {
    const targets = (items ?? []).filter((it) => selected.includes(it.id) && it.active !== active);
    try {
      const updated = await Promise.all(targets.map((it) => api.updateProduct(it.id, { active })));
      setItems((list) => list?.map((x) => updated.find((u) => u.id === x.id) ?? x) ?? null);
      setSelected([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No pude cambiar el estado.");
    }
  }

  const active = items?.filter((it) => it.active) ?? [];
  // Por agotarse: activos con precio fijo y pocas unidades disponibles (sin contar lo apartado).
  const low = (it: CatalogItem) => it.active && it.pricing_mode === "fixed" && it.available > 0 && it.available <= LOW_STOCK;
  return (
    <div className="sheet">
      <PageHeader
        title="Catálogo"
        description="Lo que tu agente puede ofrecer: precio y stock reales. Lo apartado por pedidos en curso no se vende dos veces."
        actions={
          <>
            <button className="btn" type="button" onClick={() => void downloadTemplate()}>
              <Download size={15} strokeWidth={1.8} aria-hidden /> Plantilla CSV
            </button>
            <label className={`btn primary${busy ? " disabled" : ""}`}>
              <Upload size={15} strokeWidth={1.8} aria-hidden /> {busy ? "Importando…" : "Subir CSV"}
              <input type="file" accept=".csv,text/csv" hidden disabled={busy}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  e.target.value = "";
                  if (f) void onFile(f);
                }} />
            </label>
          </>
        }
      />

      {error && <div className="state err" role="alert">{error}</div>}
      <SheetSync onSynced={load} />
      {result && (
        <div className="import-result" role="status">
          <Badge tone="pos">{result.created} nuevos</Badge>
          <Badge tone="neu">{result.updated} actualizados</Badge>
          {result.errors.length > 0 && <Badge tone="neg">{result.errors.length} con error</Badge>}
          {result.errors.length > 0 && (
            <ul>
              {result.errors.map((e) => (
                <li key={e.fila}>Fila {e.fila}{e.sku ? ` (${e.sku})` : ""}: {e.error}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {items === null ? (
        <div className="tablewrap" aria-busy="true" aria-label="Cargando catálogo">
          {[0, 1, 2, 3].map((k) => <div className="skel-row" key={k}><span className="skel" style={{ width: "40%" }} /></div>)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon={Package} title="Todavía no cargaste productos">
          Descargá la plantilla, completala y subila.
        </EmptyState>
      ) : (
        <>
          <Stats label="Resumen del catálogo" items={[
            { label: "Productos activos", value: active.length, hint: `de ${items.length} cargados` },
            { label: "Sin stock", value: active.filter((it) => it.pricing_mode === "fixed" && it.available <= 0).length,
              hint: "activos que no se pueden vender" },
            { label: "Por agotarse", value: items.filter(low).length, hint: `${LOW_STOCK} o menos disponibles` },
            { label: "A pedido", value: items.filter((it) => it.pricing_mode !== "fixed").length, hint: "los cotiza una persona" },
          ]} />
          <div className="tablewrap">
            <table className="catalog-table">
              <thead>
                <tr>
                  <th className="check">
                    <input type="checkbox" aria-label="Seleccionar todos"
                      checked={selected.length > 0 && selected.length === allIds.length}
                      ref={(el) => { if (el) el.indeterminate = selected.length > 0 && selected.length < allIds.length; }}
                      onChange={(e) => setSelected(e.target.checked ? allIds : [])} />
                  </th>
                  <th>Producto</th>
                  <th>Categoría</th>
                  <th className="num">Precio</th>
                  <th className="num">Stock</th>
                  <th>Estado</th>
                  <th><span className="sr">Acciones</span></th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => {
                  const e = edit[it.id];
                  const custom = it.pricing_mode !== "fixed";
                  const isSel = selected.includes(it.id);
                  return (
                    <tr key={it.id} className={`${isSel ? "selected" : ""}${it.active ? "" : " off"}`}>
                      <td className="check">
                        <input type="checkbox" checked={isSel} onChange={() => toggleSel(it.id)} aria-label={`Seleccionar ${it.name}`} />
                      </td>
                      <td>
                        <div className="cprod">
                          <div className="cimg">{it.image_url ? <img src={it.image_url} alt="" loading="lazy" /> : null}</div>
                          <div className="cinfo">
                            <b title={it.name}>{it.name}</b>
                            <span className="muted">
                              {it.sku}{it.brand ? ` · ${it.brand}` : ""}
                              {it.variant_group ? ` · ${it.variant_group}${it.variant_label ? ` (${it.variant_label})` : ""}` : ""}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="muted">{it.category}</td>
                      <td className="num">
                        {custom ? (
                          <em className="muted">a pedido</em>
                        ) : (
                          <input className="amount-input" inputMode="decimal" aria-label={`Precio de ${it.name}`}
                            value={e?.price ?? (it.price != null ? String(it.price) : "")} placeholder="—"
                            onChange={(ev) => setEdit({ ...edit, [it.id]: { price: ev.target.value, stock: e?.stock ?? String(it.on_hand) } })} />
                        )}
                      </td>
                      <td className="num">
                        <input className="amount-input qty-input" inputMode="numeric" aria-label={`Stock de ${it.name}`}
                          value={e?.stock ?? String(it.on_hand)}
                          onChange={(ev) => setEdit({ ...edit, [it.id]: { stock: ev.target.value, price: e?.price ?? String(it.price ?? "") } })} />
                      </td>
                      <td>
                        {!it.active ? <Badge tone="neu">Pausado</Badge>
                          : custom ? <Badge tone="info">A pedido</Badge>
                          : it.available <= 0 ? <Badge tone="neg">Sin stock</Badge>
                          : low(it) ? <Badge tone="warn">Quedan {it.available}</Badge>
                          : <Badge tone="pos">Activo</Badge>}
                        {it.reserved > 0 && <Badge tone="warn">{it.reserved} apartadas</Badge>}
                      </td>
                      <td className="actions-cell">
                        {e && <button className="btn sm primary" type="button" onClick={() => void saveRow(it)}>Guardar</button>}
                        <button className="btn sm ghost" type="button" onClick={() => setHistory(it)}>Historial</button>
                        <button className="btn sm ghost" type="button" onClick={() => void toggle(it)}>
                          {it.active ? "Pausar" : "Activar"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {history && <MovementsModal item={history} onClose={() => setHistory(null)} />}
          <SelectionBar count={selected.length} onClear={() => setSelected([])}>
            <button className="btn sm" type="button" onClick={() => void setActive(true)}>
              <Play size={14} strokeWidth={1.8} aria-hidden /> Activar
            </button>
            <button className="btn sm" type="button" onClick={() => void setActive(false)}>
              <Pause size={14} strokeWidth={1.8} aria-hidden /> Pausar
            </button>
          </SelectionBar>
        </>
      )}
    </div>
  );
}

/** Historial de stock de un producto: ventas, apartados, liberaciones y ajustes. */
function MovementsModal({ item, onClose }: { item: CatalogItem; onClose: () => void }) {
  type Move = Awaited<ReturnType<typeof api.stockMovements>>[number];
  const [moves, setMoves] = useState<Move[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api.stockMovements(item.id).then(setMoves).catch(() => setFailed(true));
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [item.id, onClose]);
  const sign = (n: number) => (n > 0 ? `+${n}` : String(n));
  return (
    <div className="pmodal-scrim" onClick={onClose}>
      <div className="pmodal history-modal" role="dialog" aria-modal="true" aria-label={`Historial de ${item.name}`}
        onClick={(e) => e.stopPropagation()}>
        <div className="pmodal-body">
          <h2>Historial de stock</h2>
          <p>{item.name} · stock {item.on_hand}, apartadas {item.reserved}</p>
          {failed ? <div className="state err">No pude cargar el historial.</div> : !moves ? <p>Cargando…</p>
            : moves.length === 0 ? <p>Todavía no hay movimientos.</p> : (
              <div className="kv">
                {moves.map((m, i) => (
                  <div className="row" key={i}>
                    <span className="k">
                      {new Date(m.at).toLocaleString("es-AR", { timeZone: "America/Argentina/Buenos_Aires",
                        day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })} · {m.label}
                      {m.order_number ? ` · pedido #${m.order_number}` : ""}
                    </span>
                    <span className="v">
                      {m.on_hand !== 0 && `stock ${sign(m.on_hand)}`}{m.on_hand !== 0 && m.reserved !== 0 ? " · " : ""}
                      {m.reserved !== 0 && `apartadas ${sign(m.reserved)}`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          <button className="btn" type="button" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}
