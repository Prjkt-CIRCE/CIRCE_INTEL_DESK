/* ============================================================
   CIRCE Intel Desk — accent.js
   Gerenciamento da cor de destaque (accent) configurável.

   6 paletas conforme 09_DESIGN_SYSTEM.md seção 4:
     amber, green, blue, bone, bordeaux, amethyst.

   Cada paleta tem 3 variantes (base, soft, strong) por tema.
   Valores espelham o que tokens.css define como default (amber),
   mas precisam estar duplicados aqui porque o operador escolhe
   uma paleta diferente de amber, e o JS sobrescreve as variáveis.

   Persistência: localStorage (Sprint 0.5; D6 candidata).
   ============================================================ */

(function () {
  "use strict";

  const STORAGE_KEY = "circe:default:accent";
  const DEFAULT_ACCENT = "amber";

  // Paletas — cada chave é o id da paleta; cada valor tem
  // sub-objetos por tema, com as três variáveis CSS.
  const PALETTES = {
    amber: {
      label: "Âmbar CRT",
      dark:  { accent: "#E8B559", soft: "#4A3A1F", strong: "#F5C870" },
      light: { accent: "#A87317", soft: "#E8DCC0", strong: "#8E5F0E" }
    },
    green: {
      label: "Verde-fósforo",
      dark:  { accent: "#74C475", soft: "#1F3A1F", strong: "#8FD58F" },
      light: { accent: "#3F7B3F", soft: "#D8E8D8", strong: "#2E5E2E" }
    },
    blue: {
      label: "Azul-petróleo",
      dark:  { accent: "#5FB3CF", soft: "#1F3340", strong: "#7AC8E0" },
      light: { accent: "#1F6F8A", soft: "#D0E4EE", strong: "#155670" }
    },
    bone: {
      label: "Branco-osso",
      dark:  { accent: "#D4D2CC", soft: "#34332F", strong: "#E8E5DA" },
      light: { accent: "#3A3A35", soft: "#DEDACE", strong: "#1F1E18" }
    },
    bordeaux: {
      label: "Vermelho-bordô",
      dark:  { accent: "#D88078", soft: "#3F2826", strong: "#E59891" },
      light: { accent: "#A03828", soft: "#F0D8D5", strong: "#7A2418" }
    },
    amethyst: {
      label: "Roxo-ametista",
      dark:  { accent: "#B594D4", soft: "#34243F", strong: "#C9AFE0" },
      light: { accent: "#6E4495", soft: "#E2D5EE", strong: "#54307A" }
    }
  };

  function getStoredAccent() {
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return PALETTES[value] ? value : null;
    } catch (e) {
      return null;
    }
  }

  function getCurrentTheme() {
    return document.documentElement.getAttribute("data-theme") || "dark";
  }

  function applyAccent(accentId) {
    if (!PALETTES[accentId]) {
      accentId = DEFAULT_ACCENT;
    }
    const theme = getCurrentTheme();
    const palette = PALETTES[accentId][theme];
    const root = document.documentElement.style;
    root.setProperty("--accent", palette.accent);
    root.setProperty("--accent-soft", palette.soft);
    root.setProperty("--accent-strong", palette.strong);
    try {
      localStorage.setItem(STORAGE_KEY, accentId);
    } catch (e) {
      // Sem persistência.
    }
    document.dispatchEvent(new CustomEvent("circe:accent-changed", {
      detail: { accent: accentId }
    }));
  }

  // Reagir a mudança de tema — variantes da paleta atual mudam por tema.
  document.addEventListener("circe:theme-changed", function () {
    const current = getStoredAccent() || DEFAULT_ACCENT;
    applyAccent(current);
  });

  // Aplicação inicial.
  const stored = getStoredAccent();
  if (stored) {
    applyAccent(stored);
  }

  // API pública.
  window.CIRCE = window.CIRCE || {};
  window.CIRCE.accent = {
    get: function () {
      return getStoredAccent() || DEFAULT_ACCENT;
    },
    set: applyAccent,
    list: function () {
      return Object.keys(PALETTES).map(function (id) {
        return { id: id, label: PALETTES[id].label };
      });
    },
    hasUserPreference: function () {
      return getStoredAccent() !== null;
    }
  };
})();