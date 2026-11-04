/* Chat de ventas para la web del comercio.
 * Uso (una sola vez): <script src="https://<api>/widget.js" data-tienda="mi-tienda" async></script>
 * El botón, el saludo y la posición se leen en vivo de la configuración del negocio (panel → «Chat en
 * tu web»). Opcionales que pisan la configuración: data-color, data-texto, data-posicion="left".
 * La charla corre en un iframe del dominio del panel: la página del comercio nunca ve la conversación
 * ni el token del comprador. Sin dependencias ni cookies propias. */
(function () {
  var s = document.currentScript;
  if (!s || window.__pvWidget) return;
  var slug = s.getAttribute("data-tienda") || "";
  if (!/^[a-z0-9-]{3,48}$/.test(slug)) { console.warn("[chat] data-tienda inválido"); return; }
  window.__pvWidget = true;
  var api = new URL(s.src, location.href).origin;
  var KEY = "pvw:" + slug;

  function store(k, v) {
    try { if (v === undefined) return sessionStorage.getItem(KEY + k); sessionStorage.setItem(KEY + k, v); } catch (e) { return null; }
  }

  function start(cfg) {
    var color = /^#[0-9a-fA-F]{6}$/.test(s.getAttribute("data-color") || "") ? s.getAttribute("data-color") : cfg.color;
    var label = (s.getAttribute("data-texto") || cfg.label || "¿Te ayudo?").slice(0, 40);
    var side = (s.getAttribute("data-posicion") || cfg.position) === "left" ? "left" : "right";
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var css = document.createElement("style");
    css.textContent =
      ".pvw-btn{position:fixed;" + side + ":20px;bottom:20px;z-index:2147483001;border:0;border-radius:999px;padding:12px 18px;" +
      "font:600 15px/1 system-ui,sans-serif;color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.18);cursor:pointer}" +
      ".pvw-btn:focus-visible{outline:3px solid #1b1c1f;outline-offset:2px}" +
      ".pvw-frame{position:fixed;" + side + ":20px;bottom:80px;z-index:2147483000;width:380px;height:600px;max-height:calc(100vh - 100px);" +
      "border:0;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.25);background:#fff;display:none}" +
      ".pvw-open .pvw-frame{display:block}.pvw-open .pvw-tip{display:none}" +
      ".pvw-tip{position:fixed;" + side + ":20px;bottom:76px;z-index:2147483001;max-width:260px;background:#fff;color:#1b1c1f;" +
      "font:400 14px/1.4 system-ui,sans-serif;padding:12px 32px 12px 14px;border-radius:14px;box-shadow:0 8px 28px rgba(0,0,0,.18);" +
      "cursor:pointer;" + (reduce ? "" : "animation:pvw-in .25s ease-out") + "}" +
      ".pvw-tip button{position:absolute;top:6px;right:6px;border:0;background:none;font:16px/1 system-ui;color:#666;cursor:pointer;padding:4px}" +
      "@keyframes pvw-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}" +
      "@media (max-width:520px){.pvw-frame{left:0;right:0;bottom:0;width:100vw;height:100vh;max-height:100vh;border-radius:0}" +
      ".pvw-open .pvw-btn{bottom:auto;top:12px;" + side + ":12px;padding:8px 12px}.pvw-tip{max-width:calc(100vw - 40px)}}";
    document.head.appendChild(css);

    var root = document.createElement("div");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pvw-btn";
    btn.style.background = color;
    btn.textContent = label;
    btn.setAttribute("aria-expanded", "false");
    var frame, tip;
    function closeTip() { if (tip) { tip.remove(); tip = null; } store("tip", "1"); }
    function toggle(open) {
      if (open && !frame) {
        frame = document.createElement("iframe");
        frame.className = "pvw-frame";
        frame.title = "Chat con la tienda";
        frame.src = cfg.store_url;
        frame.setAttribute("allow", "clipboard-write");
        root.appendChild(frame);
      }
      if (open) closeTip();
      root.classList.toggle("pvw-open", open);
      btn.setAttribute("aria-expanded", String(open));
      btn.textContent = open ? "Cerrar" : label;
    }
    btn.addEventListener("click", function () { toggle(!root.classList.contains("pvw-open")); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") toggle(false); });
    root.appendChild(btn);
    (document.body || document.documentElement).appendChild(root);

    // Saludo: una vez por visita, sólo si el negocio lo cargó. Es un globo en la página, no un mensaje.
    if (cfg.greeting && !store("tip")) {
      setTimeout(function () {
        if (root.classList.contains("pvw-open") || store("tip")) return;
        tip = document.createElement("div");
        tip.className = "pvw-tip";
        tip.setAttribute("role", "status");
        tip.textContent = cfg.greeting;
        var x = document.createElement("button");
        x.type = "button";
        x.setAttribute("aria-label", "Cerrar saludo");
        x.textContent = "×";
        x.addEventListener("click", function (e) { e.stopPropagation(); closeTip(); });
        tip.appendChild(x);
        tip.addEventListener("click", function () { toggle(true); });
        root.appendChild(tip);
      }, Math.max(0, Math.min(120, cfg.greeting_delay_s || 0)) * 1000);
    }

    // «Instalado en»: avisa el dominio una vez por visita (texto plano: sin preflight).
    if (!store("seen") && navigator.sendBeacon) {
      navigator.sendBeacon(api + "/public/" + slug + "/widget/seen", JSON.stringify({ page: location.origin }));
      store("seen", "1");
    }
  }

  fetch(api + "/public/" + slug + "/widget").then(function (r) { return r.ok ? r.json() : null; })
    .then(function (cfg) { if (cfg && cfg.store_url) start(cfg); else console.warn("[chat] tienda no encontrada"); })
    .catch(function () { console.warn("[chat] no se pudo cargar"); });
})();
