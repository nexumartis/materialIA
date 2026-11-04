import { useRef, useState, type KeyboardEvent } from "react";
import { Check, Copy } from "lucide-react";

/** Pasos por plataforma. Son orientativos: los menús de cada plataforma cambian con el tiempo,
 *  por eso se nombran de forma genérica y siempre terminan en «pegá el código». */
const PLATFORMS: { key: string; label: string; steps: string[] }[] = [
  { key: "tiendanube", label: "Tiendanube", steps: [
    "Entrá al administrador de tu Tiendanube.",
    "Andá a Configuración → Códigos externos (puede figurar como «Códigos de tracking»).",
    "Pegá el código en el campo para todas las páginas (por ejemplo, «Código para todas las páginas»).",
    "Guardá y abrí tu tienda para ver el botón.",
  ] },
  { key: "wordpress", label: "WordPress / WooCommerce", steps: [
    "En el escritorio de WordPress, instalá un plugin para insertar código, como «WPCode» o «Insert Headers and Footers».",
    "Abrí el plugin y buscá la sección del pie de página (Footer).",
    "Pegá el código ahí y guardá.",
    "Si usás un plugin de caché, vacialo y recargá tu web.",
  ] },
  { key: "shopify", label: "Shopify", steps: [
    "En el admin de Shopify, andá a Tienda online → Temas.",
    "En tu tema activo, abrí el menú «…» y elegí Editar código.",
    "Abrí el archivo theme.liquid (carpeta Layout).",
    "Pegá el código justo antes de </body> y guardá.",
  ] },
  { key: "wix", label: "Wix", steps: [
    "En el panel de tu sitio, andá a Configuración → Código personalizado.",
    "Tocá «Agregar código personalizado» y pegá el código.",
    "Elegí que se cargue en todas las páginas y ubicalo en «Body - final».",
    "Aplicá los cambios y publicá el sitio.",
  ] },
  { key: "gtm", label: "Google Tag Manager", steps: [
    "En tu contenedor, creá una etiqueta nueva de tipo «HTML personalizado».",
    "Pegá el código en la etiqueta.",
    "Elegí el activador «All Pages» (todas las páginas).",
    "Guardá y publicá el contenedor.",
  ] },
  { key: "html", label: "HTML", steps: [
    "Abrí el archivo HTML de tu página (o la plantilla que comparten todas).",
    "Pegá el código justo antes de </body>.",
    "Subí el archivo a tu hosting y recargá la página.",
  ] },
];

/** Paso 2: el código para pegar y cómo hacerlo en cada plataforma (pestañas accesibles). */
export function WidgetInstallGuide({ snippet }: { snippet: string }) {
  const [copied, setCopied] = useState<"ok" | "err" | null>(null);
  const [tab, setTab] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);

  function copy() {
    const done = (r: "ok" | "err") => { setCopied(r); window.setTimeout(() => setCopied(null), 2500); };
    if (!navigator.clipboard) { done("err"); return; }
    navigator.clipboard.writeText(snippet).then(() => done("ok"), () => done("err"));
  }

  // Flechas, Inicio y Fin mueven entre pestañas (patrón ARIA de tabs con foco itinerante).
  function onKey(e: KeyboardEvent<HTMLDivElement>) {
    const last = PLATFORMS.length - 1;
    const next = e.key === "ArrowRight" ? (tab === last ? 0 : tab + 1)
      : e.key === "ArrowLeft" ? (tab === 0 ? last : tab - 1)
      : e.key === "Home" ? 0 : e.key === "End" ? last : null;
    if (next == null) return;
    e.preventDefault();
    setTab(next);
    tabs.current[next]?.focus();
  }

  const p = PLATFORMS[tab];
  return (
    <>
      <div className="wc-code">
        <pre tabIndex={0} aria-label="Código para pegar en tu web"><code>{snippet}</code></pre>
        <button className="btn sm" type="button" onClick={copy}>
          {copied === "ok" ? <Check size={14} strokeWidth={2} aria-hidden /> : <Copy size={14} strokeWidth={1.8} aria-hidden />}
          {copied === "ok" ? "Copiado" : "Copiar"}
        </button>
      </div>
      <p className="muted small" aria-live="polite">
        {copied === "err" ? "No pude copiar solo: seleccioná el código y copialo a mano."
          : "Lo pegás una sola vez; los cambios se ven solos."}
      </p>

      <div className="tabs wc-tabs" role="tablist" aria-label="Plataforma de tu web" onKeyDown={onKey}>
        {PLATFORMS.map((x, i) => (
          <button key={x.key} ref={(el) => { tabs.current[i] = el; }} id={`wc-tab-${x.key}`} role="tab" type="button"
            aria-selected={i === tab} aria-controls="wc-tabpanel" tabIndex={i === tab ? 0 : -1} onClick={() => setTab(i)}>
            {x.label}
          </button>
        ))}
      </div>
      <div id="wc-tabpanel" role="tabpanel" aria-labelledby={`wc-tab-${p.key}`} tabIndex={0}>
        <ol className="wc-steps">{p.steps.map((s) => <li key={s}>{s}</li>)}</ol>
      </div>
    </>
  );
}
