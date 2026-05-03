/* ============================================================
   CIRCE Intel Desk — status_bar.js
   Atualiza o relógio da status bar a cada segundo.
   Demais indicadores (OP, CRYPT, WS) são populados em sprints futuras.
   ============================================================ */

(function () {
  "use strict";

  function pad(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  function formatTime(date) {
    return pad(date.getHours()) +
           ":" + pad(date.getMinutes()) +
           ":" + pad(date.getSeconds());
  }

  function tick() {
    const el = document.querySelector("[data-status-clock]");
    if (!el) return;
    el.textContent = formatTime(new Date());
  }

  function start() {
    tick();
    // Sincronizar o tick com a borda do segundo, para o relógio
    // não ficar arrastando. Calcula o ms restante até o próximo
    // segundo cheio e dispara o setInterval a partir dali.
    const now = new Date();
    const msUntilNextSecond = 1000 - now.getMilliseconds();
    setTimeout(function () {
      tick();
      setInterval(tick, 1000);
    }, msUntilNextSecond);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();