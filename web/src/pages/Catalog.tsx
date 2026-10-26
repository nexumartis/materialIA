import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type CatalogItem, type ImportResult } from "../lib/api";
import { fmtAmount } from "../lib/format";

const TEMPLATE =
  "sku,nombre,categoria,marca,precio,stock,descripcion,foto_url,color,ambiente,tipo,a_pedido,activo\n" +
  "CAN-001,Canilla de cocina monocomando negra,griferia,Mi Marca,89900,6,Pico alto giratorio,https://...,negro,cocina,monocomando,,si\n" +
  "INO-001,Inodoro largo blanco,sanitarios,Mi Marca,,,Se encarga a fábrica,,blanco,baño,,si,si\n";

function downloadTemplate() {
  const url = URL.createObjectURL(new Blob([TEMPLATE], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "catalogo-plantilla.csv";
  a.click();
  URL.revokeObjectURL(url);
}

/** Catálogo del negocio: importación CSV y edición de precio, stock y estado. */
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

  return (
    <div className="sheet">
      <div className="titlebar">
        <div>
          <h1>Catálogo</h1>
          <p className="finding">Lo que tu agente puede ofrecer: precio y stock reales. Lo apartado por pedidos en curso no se vende dos veces.</p>
        </div>
        <div className="right">
          <button className="btn sm ghost" type="button" onClick={downloadTemplate}>Descargar plantilla CSV</button>
          <label className={`btn sm primary ${busy ? "disabled" : ""}`}>
            {busy ? "Importando…" : "Subir CSV"}
            <input
              type="file"
              accept=".csv,text/csv"
              hidden
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (f) void onFile(f);
              }}
            />
          </label>
        </div>
      </div>

      {error && <div className="state err" role="alert">{error}</div>}
      {result && (
        <div className="import-result" role="status">
          <span className="pill pos">{result.created} nuevos</span>
          <span className="pill neu">{result.updated} actualizados</span>
          {result.errors.length > 0 && <span className="pill neg">{result.errors.length} con error</span>}
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
        <div className="state">Cargando…</div>
      ) : items.length === 0 ? (
        <div className="empty-box">Todavía no cargaste productos. Descargá la plantilla, completala y subila.</div>
      ) : (
        <div className="catalog">
          {items.map((it) => {
            const e = edit[it.id];
            const custom = it.pricing_mode !== "fixed";
            return (
              <div className={`crow ${it.active ? "" : "off"}`} key={it.id}>
                <div className="cimg">{it.image_url ? <img src={it.image_url} alt="" loading="lazy" /> : null}</div>
                <div className="cinfo">
                  <b>{it.name}</b>
                  <span className="muted">{it.sku}{it.brand ? ` · ${it.brand}` : ""} · {it.category}</span>
                </div>
                <label className="cfield">
                  <span>Precio</span>
                  {custom ? (
                    <em className="muted">a pedido</em>
                  ) : (
                    <input
                      inputMode="decimal"
                      value={e?.price ?? (it.price != null ? String(it.price) : "")}
                      placeholder="—"
                      onChange={(ev) => setEdit({ ...edit, [it.id]: { price: ev.target.value, stock: e?.stock ?? String(it.on_hand) } })}
                    />
                  )}
                </label>
                <label className="cfield">
                  <span>Stock</span>
                  <input
                    inputMode="numeric"
                    value={e?.stock ?? String(it.on_hand)}
                    onChange={(ev) => setEdit({ ...edit, [it.id]: { stock: ev.target.value, price: e?.price ?? String(it.price ?? "") } })}
                  />
                </label>
                <div className="cstate">
                  {it.reserved > 0 && <span className="pill warn">{it.reserved} apartadas</span>}
                  {!custom && it.price != null && <span className="muted">${fmtAmount(it.price)}</span>}
                </div>
                <div className="cactions">
                  {e && <button className="btn sm primary" type="button" onClick={() => void saveRow(it)}>Guardar</button>}
                  <button className="btn sm ghost" type="button" onClick={() => void toggle(it)}>
                    {it.active ? "Pausar" : "Activar"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
