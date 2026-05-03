/* ============================================================
   CIRCE Intel Desk — header_toggles.js
   Conecta os botões de toggle no header.

   Bloco 3: toggle de tema. (Toggle de accent é feito via command
   palette no Bloco 6, não no header — econômico em espaço visual.)
   ============================================================ */

(function () {
  "use strict";

  function updateLabel(btn) {
    if (!window.CIRCE || !window.CIRCE.theme) return;
    const current = window.CIRCE.theme.get();
    // Texto do botão indica para qual tema ele alterna ao clicar.
    btn.textContent = current === "dark" ? "☼" : "☾";
    btn.setAttribute("aria-label",
      current === "dark" ? "Alternar para tema claro" : "Alternar para tema escuro");
  }

  function setup() {
    const btn = document.querySelector("[data-toggle-theme]");
    if (!btn) return;
    updateLabel(btn);
    btn.addEventListener("click", function () {
      window.CIRCE.theme.toggle();
    });
    document.addEventListener("circe:theme-changed", function () {
      updateLabel(btn);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();