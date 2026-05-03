/* ============================================================
   CIRCE Intel Desk — theme.js
   Gerenciamento do tema visual (escuro / claro).

   Persistência: localStorage (Sprint 0.5).
   Migração para banco prevista para Sprint 01 (D6 — registrar no
   fechamento).

   Aplica o tema ANTES do primeiro paint para evitar flash de tema
   incorreto (FOUC). Por isso este script roda síncrono no <head>,
   sem 'defer'.
   ============================================================ */

(function () {
  "use strict";

  const STORAGE_KEY = "circe:default:theme";
  const VALID_THEMES = ["dark", "light"];
  const DEFAULT_THEME = "dark";

  function getStoredTheme() {
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return VALID_THEMES.includes(value) ? value : null;
    } catch (e) {
      // localStorage pode estar indisponível em modo privacidade extrema.
      return null;
    }
  }

  function applyTheme(theme) {
    if (!VALID_THEMES.includes(theme)) {
      theme = DEFAULT_THEME;
    }
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      // Sem persistência. O tema vale apenas para esta sessão.
    }
    // Notifica consumidores (botões de toggle, modal de primeira execução).
    document.dispatchEvent(new CustomEvent("circe:theme-changed", {
      detail: { theme: theme }
    }));
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || DEFAULT_THEME;
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
  }

  // Aplicação inicial — antes do primeiro paint.
  // Se nada foi guardado, mantém o default que já está no HTML (dark).
  const stored = getStoredTheme();
  if (stored) {
    applyTheme(stored);
  }

  // Expor API mínima no namespace global para uso pelo command palette
  // (Bloco 6) e pelo botão toggle no header.
  window.CIRCE = window.CIRCE || {};
  window.CIRCE.theme = {
    get: function () {
      return document.documentElement.getAttribute("data-theme") || DEFAULT_THEME;
    },
    set: applyTheme,
    toggle: toggleTheme,
    hasUserPreference: function () {
      return getStoredTheme() !== null;
    }
  };
})();