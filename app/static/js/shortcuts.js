/* ============================================================
   CIRCE Intel Desk — shortcuts.js
   Registro central de atalhos de teclado globais.

   Atalhos cadastrados na Sprint 0.5:
     - Ctrl+K  -> abrir command palette
     - Ctrl+/  -> abrir modal de atalhos
     - Esc     -> fechar palette / modal aberto

   Atalhos previstos (registrados na lista de exibição mas não
   funcionais ainda):
     - Ctrl+L     -> Sprint 01 (bloqueio)
     - Ctrl+N/P   -> Sprint 01 (novo caso/pessoa em listagem)
     - Ctrl+1..9  -> Sprint 03–05 (workspaces, ADR-010)

   Sprints futuras registram atalhos novos via:
     window.CIRCE.shortcuts.register(predicate, handler);
   ============================================================ */

(function () {
  "use strict";

  const handlers = [];

  function register(predicate, handler, description) {
    handlers.push({ predicate: predicate, handler: handler, description: description || "" });
  }

  function isCtrlKey(e, key) {
    // Aceita Ctrl ou Cmd (macOS), comparação case-insensitive.
    return (e.ctrlKey || e.metaKey)
        && !e.shiftKey
        && !e.altKey
        && e.key.toLowerCase() === key.toLowerCase();
  }

  function handleGlobal(e) {
    for (let i = 0; i < handlers.length; i++) {
      const h = handlers[i];
      if (h.predicate(e)) {
        h.handler(e);
        // Não retornamos — múltiplos predicates podem ser válidos
        // (ex.: Esc fecha tanto palette quanto shortcuts modal).
      }
    }
  }

  function setup() {
    document.addEventListener("keydown", handleGlobal);

    // Ctrl+K — abrir command palette.
    register(
      function (e) { return isCtrlKey(e, "k"); },
      function (e) {
        e.preventDefault();
        if (window.CIRCE && window.CIRCE.palette) {
          window.CIRCE.palette.open();
        }
      },
      "Abrir command palette"
    );

    // Ctrl+/ — abrir modal de atalhos.
    register(
      function (e) { return isCtrlKey(e, "/"); },
      function (e) {
        e.preventDefault();
        const m = document.getElementById("shortcuts-modal");
        if (m) m.setAttribute("data-open", "true");
      },
      "Mostrar atalhos disponíveis"
    );

    // Esc — fechar palette se aberto, OU fechar shortcuts modal se aberto.
    register(
      function (e) { return e.key === "Escape"; },
      function (e) {
        // Palette tem seu próprio handler de Esc (mais específico, no input).
        // Aqui tratamos o caso de Esc enquanto o foco não está no input do palette.
        const shortcutsModal = document.getElementById("shortcuts-modal");
        if (shortcutsModal && shortcutsModal.getAttribute("data-open") === "true") {
          shortcutsModal.setAttribute("data-open", "false");
          e.preventDefault();
          return;
        }
        if (window.CIRCE && window.CIRCE.palette && window.CIRCE.palette.isOpen()) {
          window.CIRCE.palette.close();
          e.preventDefault();
        }
      },
      "Fechar modal aberto"
    );

    // Botão de fechar do shortcuts modal.
    const closeBtn = document.querySelector("[data-shortcuts-close]");
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        const m = document.getElementById("shortcuts-modal");
        if (m) m.setAttribute("data-open", "false");
      });
    }

    // Backdrop click no shortcuts modal fecha.
    const shortcutsModal = document.getElementById("shortcuts-modal");
    if (shortcutsModal) {
      shortcutsModal.addEventListener("click", function (e) {
        if (e.target === shortcutsModal) {
          shortcutsModal.setAttribute("data-open", "false");
        }
      });
    }
  }

  // API pública.
  window.CIRCE = window.CIRCE || {};
  window.CIRCE.shortcuts = {
    register: register
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();