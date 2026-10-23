// Shell compartido: abrir/cerrar la navegación en móvil.
(function () {
  function wire() {
    var body = document.body;
    var menu = document.querySelector(".topbar .menu");
    var scrim = document.querySelector(".scrim");
    if (menu) menu.addEventListener("click", function () { body.classList.toggle("nav-open"); });
    if (scrim) scrim.addEventListener("click", function () { body.classList.remove("nav-open"); });
    document.querySelectorAll(".sidebar .nav a").forEach(function (a) {
      a.addEventListener("click", function () { body.classList.remove("nav-open"); });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();
