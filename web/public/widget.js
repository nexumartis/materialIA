/* Presupuesto Vivo — chat para la web del comercio.
 * Uso: <script src="https://<panel>/widget.js" data-tienda="mi-tienda" async></script>
 * Opcionales: data-color="#2563eb" (botón), data-texto="¿Te ayudo?" (etiqueta).
 * Abre la tienda en un iframe del dominio del panel: la página del comercio nunca ve la conversación
 * ni el token del comprador (el navegador los aísla por origen). Sin dependencias ni cookies propias. */
(function () {
  var s = document.currentScript;
  if (!s || window.__pvWidget) return;
  var slug = s.getAttribute("data-tienda") || "";
  if (!/^[a-z0-9-]{3,48}$/.test(slug)) { console.warn("[Presupuesto Vivo] data-tienda inválido"); return; }
  window.__pvWidget = true;
  var base = new URL(s.src, location.href).origin;
  var color = /^#[0-9a-fA-F]{6}$/.test(s.getAttribute("data-color") || "") ? s.getAttribute("data-color") : "#2563eb";
  var label = (s.getAttribute("data-texto") || "¿Te ayudo?").slice(0, 40);

  var css = document.createElement("style");
  css.textContent =
    ".pvw-btn{position:fixed;right:20px;bottom:20px;z-index:2147483001;border:0;border-radius:999px;padding:12px 18px;" +
    "font:600 15px/1 system-ui,sans-serif;color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.18);cursor:pointer}" +
    ".pvw-btn:focus-visible{outline:3px solid #1b1c1f;outline-offset:2px}" +
    ".pvw-frame{position:fixed;right:20px;bottom:80px;z-index:2147483000;width:380px;height:600px;max-height:calc(100vh - 100px);" +
    "border:0;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.25);background:#fff;display:none}" +
    ".pvw-open .pvw-frame{display:block}" +
    "@media (max-width:520px){.pvw-frame{right:0;bottom:0;width:100vw;height:100vh;max-height:100vh;border-radius:0}" +
    ".pvw-open .pvw-btn{bottom:auto;top:12px;right:12px;padding:8px 12px}}";
  document.head.appendChild(css);

  var root = document.createElement("div");
  var btn = document.createElement("button");
  btn.type = "button";
  btn.className = "pvw-btn";
  btn.style.background = color;
  btn.textContent = label;
  btn.setAttribute("aria-expanded", "false");
  var frame;
  function toggle(open) {
    if (open && !frame) {
      frame = document.createElement("iframe");
      frame.className = "pvw-frame";
      frame.title = "Chat con la tienda";
      frame.src = base + "/?embed=1#/tienda/" + slug;
      frame.setAttribute("allow", "clipboard-write");
      root.appendChild(frame);
    }
    root.classList.toggle("pvw-open", open);
    btn.setAttribute("aria-expanded", String(open));
    btn.textContent = open ? "Cerrar" : label;
  }
  btn.addEventListener("click", function () { toggle(!root.classList.contains("pvw-open")); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") toggle(false); });
  root.appendChild(btn);
  (document.body || document.documentElement).appendChild(root);
})();
