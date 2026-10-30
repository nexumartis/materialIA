import { useEffect, useState } from "react";
import { ExternalLink, FileSpreadsheet, RefreshCw, Unplug } from "lucide-react";
import { ApiError, api, type CatalogSheet } from "../lib/api";
import { Badge } from "./ui";

function when(iso: string): string {
  return new Date(iso).toLocaleString("es-AR", {
    timeZone: "America/Argentina/Buenos_Aires", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

/** Conectar el catálogo a una planilla de Google Sheets y ver cómo fue la última sincronización.
 *  `onSynced`: para que la pantalla que lo usa recargue los productos. */
export function SheetSync({ onSynced }: { onSynced?: () => void }) {
  const [sheet, setSheet] = useState<CatalogSheet | null | undefined>(undefined);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  // Si no se pudo consultar, NO se ofrece «Conectar»: podría haber una planilla conectada y
  // reconectarla reiniciaría su estado.
  const load = () => {
    setLoadFailed(false);
    api.catalogSheet().then((r) => setSheet(r.sheet)).catch(() => setLoadFailed(true));
  };
  useEffect(load, []);

  async function run(action: () => Promise<{ sheet: CatalogSheet | null } | { disconnected: boolean }>) {
    setBusy(true);
    setError(null);
    try {
      const r = await action();
      setSheet("sheet" in r ? r.sheet : null);
      onSynced?.();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No pude conectar con el servidor.");
    } finally {
      setBusy(false);
    }
  }

  if (loadFailed) {
    return (
      <section className="setup-card sheet-sync" aria-label="Planilla de Google">
        <div className="state err" role="alert">No pude consultar la planilla conectada.</div>
        <div><button className="btn sm" type="button" onClick={load}>Reintentar</button></div>
      </section>
    );
  }
  if (sheet === undefined) return null;
  const result = sheet?.last_result;
  return (
    <section className="setup-card sheet-sync" aria-label="Planilla de Google">
      <div className="sheet-sync-head">
        <FileSpreadsheet size={18} strokeWidth={1.8} aria-hidden />
        <div>
          <h2 className="panel-title">Planilla de Google</h2>
          <p className="panel-sub">
            Tu catálogo se actualiza solo desde tu planilla, cada 15 minutos. Mismas columnas que la plantilla CSV.
          </p>
        </div>
      </div>

      {!sheet ? (
        <form className="inline" onSubmit={(e) => { e.preventDefault(); if (url.trim()) void run(() => api.connectCatalogSheet(url.trim())); }}>
          <input className="field-select sheet-url" type="url" aria-label="Link de la planilla" value={url}
            placeholder="https://docs.google.com/spreadsheets/d/…" onChange={(e) => setUrl(e.target.value)} />
          <button className="btn primary" type="submit" disabled={busy || !url.trim()}>
            {busy ? "Conectando…" : "Conectar"}
          </button>
          <p className="note">
            En Google Sheets: <b>Compartir → Cualquier persona con el enlace → Lector</b>, y pegá el link de la pestaña
            con tus productos.
          </p>
        </form>
      ) : (
        <>
          <div className="inline sheet-status" role="status">
            {sheet.last_status === "ok" ? <Badge tone="pos">Sincronizada</Badge>
              : sheet.last_status === "error" ? <Badge tone="neg">No se pudo leer</Badge>
              : <Badge tone="neu">Pendiente</Badge>}
            {sheet.last_synced_at && <span className="muted">Última lectura: {when(sheet.last_synced_at)}</span>}
            {sheet.last_status === "ok" && result && (
              <span className="muted">· {result.created} nuevos · {result.updated} actualizados</span>
            )}
          </div>
          {sheet.last_status === "error" && sheet.last_error && <div className="state err">{sheet.last_error}</div>}
          <p className="note">
            Con la planilla conectada, <b>los precios se editan en la planilla</b>: un precio cambiado en la tabla de
            abajo se reemplaza en la próxima sincronización. El stock que cambies acá se respeta hasta que cambies ese
            número en la planilla.
          </p>
          {sheet.last_status === "ok" && result && result.errors.length > 0 && (
            <details className="sheet-errors">
              <summary>{result.errors.length} {result.errors.length === 1 ? "fila con error" : "filas con error"}</summary>
              <ul>{result.errors.map((e) => <li key={e.fila}>Fila {e.fila}{e.sku ? ` (${e.sku})` : ""}: {e.error}</li>)}</ul>
            </details>
          )}
          {sheet.last_status === "ok" && result?.missing && result.missing.count > 0 && (
            <p className="note">
              {result.missing.count} {result.missing.count === 1 ? "producto activo no está" : "productos activos no están"} en
              la planilla ({result.missing.skus.join(", ")}{result.missing.count > result.missing.skus.length ? "…" : ""}).
              No se pausan solos: si ya no los vendés, pausalos en la tabla.
            </p>
          )}
          <div className="inline">
            <button className="btn" type="button" disabled={busy} onClick={() => void run(api.syncCatalogSheet)}>
              <RefreshCw size={15} strokeWidth={1.8} aria-hidden /> {busy ? "Sincronizando…" : "Sincronizar ahora"}
            </button>
            <a className="btn ghost" href={sheet.url} target="_blank" rel="noopener noreferrer">
              <ExternalLink size={15} strokeWidth={1.8} aria-hidden /> Abrir planilla
            </a>
            <button className="btn ghost" type="button" disabled={busy}
              onClick={() => { if (window.confirm("¿Desconectar la planilla? Los productos quedan como están.")) void run(api.disconnectCatalogSheet); }}>
              <Unplug size={15} strokeWidth={1.8} aria-hidden /> Desconectar
            </button>
          </div>
        </>
      )}
      {error && <div className="state err" role="alert">{error}</div>}
    </section>
  );
}
