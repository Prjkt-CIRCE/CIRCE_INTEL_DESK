/* ============================================================
   CIRCE Intel Desk — toast.js
   Helper de notificação efêmera (toast).

   Resolve a pendência da Sprint 0.5: o showcase tinha apenas
   markup estático de toast; este módulo cria o MECANISMO de
   disparo dinâmico via JS. Reaproveita as classes canônicas
   .toast / .toast--{success,warning,error,info} / .toast__title
   / .toast__body já definidas em components.css. Zero CSS novo.

   API pública (window.CIRCE.toast):
     show(variant, title, body)  -> exibe um toast
     success(title, body)        -> atalho variant="success"
     warning(title, body)        -> atalho variant="warning"
     error(title, body)          -> atalho variant="error"
     info(title, body)           -> atalho variant="info"

   Comportamento (09_DESIGN_SYSTEM.md §8.7):
     - Aparece no canto inferior direito.
     - Tempo padrão: 4s. ERROS não somem sozinhos (exigem dispensa).
     - Clique no toast o dispensa.
     - Sem animações elaboradas.

   Padrão da casa: IIFE, "use strict", namespace window.CIRCE,
   setup no DOMContentLoaded com guarda de readyState.
   ============================================================ */

(function () {
  "use strict";

  var VARIANTS = ["success", "warning", "error", "info"];
  var DEFAULT_TIMEOUT_MS = 4000;

  // Container único, criado sob demanda no primeiro toast.
  var containerEl = null;

  function ensureContainer() {
    if (containerEl) return containerEl;
    containerEl = document.getElementById("toast-container");
    if (!containerEl) {
      containerEl = document.createElement("div");
      containerEl.id = "toast-container";
      containerEl.className = "toast-container";
      // Posicionamento inline mínimo: não depende de CSS novo para
      // ancorar o container. Os toasts em si herdam .toast do design system.
      containerEl.style.position = "fixed";
      containerEl.style.right = "var(--space-5, 24px)";
      containerEl.style.bottom = "var(--space-5, 24px)";
      containerEl.style.display = "flex";
      containerEl.style.flexDirection = "column";
      containerEl.style.gap = "var(--space-2, 8px)";
      containerEl.style.zIndex = "9999";
      containerEl.setAttribute("role", "status");
      containerEl.setAttribute("aria-live", "polite");
      document.body.appendChild(containerEl);
    }
    return containerEl;
  }

  function dismiss(toastEl) {
    if (!toastEl || !toastEl.parentNode) return;
    toastEl.parentNode.removeChild(toastEl);
  }

  function show(variant, title, body) {
    if (VARIANTS.indexOf(variant) < 0) {
      variant = "info";
    }
    var container = ensureContainer();

    var toastEl = document.createElement("div");
    toastEl.className = "toast toast--" + variant;

    var inner = document.createElement("div");

    if (title) {
      var titleEl = document.createElement("div");
      titleEl.className = "toast__title";
      titleEl.textContent = title;
      inner.appendChild(titleEl);
    }
    if (body) {
      var bodyEl = document.createElement("div");
      bodyEl.className = "toast__body";
      bodyEl.textContent = body;
      inner.appendChild(bodyEl);
    }
    toastEl.appendChild(inner);

    // Clique dispensa.
    toastEl.addEventListener("click", function () { dismiss(toastEl); });

    container.appendChild(toastEl);

    // Erros não somem sozinhos (§8.7). Demais variantes expiram em 4s.
    if (variant !== "error") {
      setTimeout(function () { dismiss(toastEl); }, DEFAULT_TIMEOUT_MS);
    }

    return toastEl;
  }

  function setup() {
    // Nada a montar no DOM até o primeiro toast. setup() existe só
    // para manter o padrão da casa e permitir extensão futura.
  }

  // ---------- API pública ----------
  window.CIRCE = window.CIRCE || {};
  window.CIRCE.toast = {
    show: show,
    success: function (title, body) { return show("success", title, body); },
    warning: function (title, body) { return show("warning", title, body); },
    error: function (title, body) { return show("error", title, body); },
    info: function (title, body) { return show("info", title, body); }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
