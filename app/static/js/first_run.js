/* ============================================================
   CIRCE Intel Desk — first_run.js
   Controla o modal de primeira execução (escolha de tema + accent).

   Critério de aceite CA-0.5.9 — primeira execução exibe modal;
   execuções subsequentes não.

   Depende de theme.js e accent.js (devem estar carregados antes).
   ============================================================ */

(function () {
  "use strict";

  function isFirstRun() {
    if (!window.CIRCE || !window.CIRCE.theme || !window.CIRCE.accent) {
      return false;
    }
    return !window.CIRCE.theme.hasUserPreference()
        && !window.CIRCE.accent.hasUserPreference();
  }

  function setupChoiceGroups(modalEl) {
    const groups = modalEl.querySelectorAll("[data-choice-group]");
    groups.forEach(function (group) {
      const groupName = group.getAttribute("data-choice-group");
      const cards = group.querySelectorAll(".choice-card");
      cards.forEach(function (card) {
        card.addEventListener("click", function () {
          // Marca apenas o clicado como selecionado neste grupo.
          cards.forEach(function (c) {
            c.setAttribute("data-selected", "false");
          });
          card.setAttribute("data-selected", "true");
          // Aplica imediatamente — operador vê preview.
          const value = card.getAttribute("data-value");
          if (groupName === "theme") {
            window.CIRCE.theme.set(value);
          } else if (groupName === "accent") {
            window.CIRCE.accent.set(value);
          }
        });
      });
    });
  }

  function preselectDefaults(modalEl) {
    // Pre-seleciona escuro + âmbar como defaults visuais; não persiste
    // até o operador clicar Confirmar.
    const themeDark = modalEl.querySelector('[data-choice-group="theme"] [data-value="dark"]');
    const accentAmber = modalEl.querySelector('[data-choice-group="accent"] [data-value="amber"]');
    if (themeDark) themeDark.setAttribute("data-selected", "true");
    if (accentAmber) accentAmber.setAttribute("data-selected", "true");
  }

  function setupConfirmButton(modalEl) {
    const btn = modalEl.querySelector("[data-first-run-confirm]");
    if (!btn) return;
    btn.addEventListener("click", function () {
      // theme.js e accent.js já persistem ao serem chamados
      // por setupChoiceGroups; mas garantimos persistência aqui
      // mesmo que o operador não tenha clicado em nenhum card
      // (clica direto em Confirmar com defaults pré-selecionados).
      const themeSelected = modalEl.querySelector('[data-choice-group="theme"] [data-selected="true"]');
      const accentSelected = modalEl.querySelector('[data-choice-group="accent"] [data-selected="true"]');
      if (themeSelected) {
        window.CIRCE.theme.set(themeSelected.getAttribute("data-value"));
      } else {
        window.CIRCE.theme.set("dark");
      }
      if (accentSelected) {
        window.CIRCE.accent.set(accentSelected.getAttribute("data-value"));
      } else {
        window.CIRCE.accent.set("amber");
      }
      modalEl.setAttribute("data-open", "false");
    });
  }

  function start() {
    const modalEl = document.getElementById("first-run-modal");
    if (!modalEl) return;
    if (!isFirstRun()) return;
    preselectDefaults(modalEl);
    setupChoiceGroups(modalEl);
    setupConfirmButton(modalEl);
    modalEl.setAttribute("data-open", "true");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();