/* ============================================================
   CIRCE Intel Desk — command_palette.js
   Componente central da experiência de teclado.

   Atalho: Ctrl+K (registro feito em shortcuts.js).
   Saída : Esc.
   Navegação interna: setas + Enter.

   Cada ação é um objeto:
     {
       id: string (único),
       label: string (visível ao operador),
       group: string ("Ações" | "Workspaces" | "Páginas"),
       keywords: string[] (termos extras para casamento),
       hint: string|null (texto à direita, ex.: "Ctrl+L"),
       handler: function (chamado ao executar)
     }

   Modo FTS5 (D-02-8-01):
   - Query >= 2 chars: busca FTS5 + filtra ações em paralelo.
   - Resultados FTS5 aparecem no grupo "Resultados" acima das ações.
   - Debounce de 250ms na chamada à API.
   - allRenderItems[] unifica FTS5 + ações para navegação por setas/Enter.

   Sprints futuras adicionam ações via window.CIRCE.palette.register().
   ============================================================ */

(function () {
  "use strict";

  // ---------- Estado de ações ----------
  const state = {
    actions: [],
    filtered: [],
    activeIndex: 0,
    isOpen: false
  };

  // ---------- Estado FTS5 ----------
  let searchDebounceTimer = null;
  let lastSearchQuery = "";
  let searchResults = [];
  let isSearching = false;

  // allRenderItems: lista unificada [FTS5 results, ...filtered actions]
  // usada por executeAt e pela navegação por setas.
  let allRenderItems = [];

  // ---------- DOM refs ----------
  let modalEl = null;
  let inputEl = null;
  let resultsEl = null;
  let emptyEl = null;

  // ---------- Registro de ações ----------
  function register(action) {
    if (!action || !action.id || !action.label || typeof action.handler !== "function") {
      console.warn("[palette] ação inválida ignorada", action);
      return;
    }
    // Substitui se já existir mesmo id (re-registro idempotente).
    const existing = state.actions.findIndex(function (a) { return a.id === action.id; });
    if (existing >= 0) {
      state.actions[existing] = action;
    } else {
      state.actions.push(action);
    }
  }

  // ---------- Filtragem ----------
  function normalize(s) {
    return (s || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "");
  }

  function matches(action, query) {
    if (!query) return true;
    const q = normalize(query);
    if (normalize(action.label).indexOf(q) >= 0) return true;
    if (Array.isArray(action.keywords)) {
      for (let i = 0; i < action.keywords.length; i++) {
        if (normalize(action.keywords[i]).indexOf(q) >= 0) return true;
      }
    }
    if (normalize(action.group).indexOf(q) >= 0) return true;
    return false;
  }

  function recomputeFiltered(query) {
    state.filtered = state.actions.filter(function (a) { return matches(a, query); });
    // activeIndex será revalidado após render() reconstruir allRenderItems.
  }

  // ---------- FTS5 ----------
  function handlerForResult(result) {
    return function () {
      switch (result.type) {
        case "case":
          window.location.href = "/cases/" + result.id;
          break;
        case "person":
          window.location.href = "/persons/" + result.id;
          break;
        case "organization":
          window.location.href = "/organizations/" + result.id;
          break;
        case "document":
          // Documento não tem tela própria ainda — navega para lista de casos.
          window.location.href = "/cases";
          break;
        default:
          break;
      }
    };
  }

  function hintForType(type) {
    switch (type) {
      case "case":         return "[CASO]";
      case "person":       return "[PESSOA]";
      case "organization": return "[ORG]";
      case "document":     return "[DOC]";
      default:             return "";
    }
  }

  function fetchSearchResults(query) {
    if (!query || query.trim().length < 2) {
      searchResults = [];
      isSearching = false;
      render();
      return;
    }
    isSearching = true;
    render(); // mostra "Buscando…" imediatamente
    fetch("/api/search?q=" + encodeURIComponent(query.trim()) + "&limit=10", {
      credentials: "same-origin"
    })
      .then(function (r) {
        if (r.status === 401 || r.redirected) return [];
        if (!r.ok) return [];
        return r.json();
      })
      .then(function (data) {
        searchResults = Array.isArray(data) ? data : [];
        isSearching = false;
        lastSearchQuery = query;
        render();
      })
      .catch(function () {
        searchResults = [];
        isSearching = false;
        render();
      });
  }

  // ---------- Renderização ----------
  function render() {
    if (!resultsEl || !emptyEl) return;
    resultsEl.innerHTML = "";

    // allRenderItems: reconstruído a cada render para que executeAt e a
    // navegação por setas sempre reflitam o estado atual.
    allRenderItems = [];

    const query = inputEl ? inputEl.value.trim() : "";
    const hasFtsActivity = query.length >= 2;

    // ---- Grupo "Resultados" (FTS5) ----
    if (hasFtsActivity) {
      if (isSearching) {
        // Cabeçalho do grupo
        const groupLi = document.createElement("li");
        groupLi.className = "palette__group";
        groupLi.textContent = "Resultados";
        resultsEl.appendChild(groupLi);

        // Item de estado "Buscando…" (não navegável — sem data-index)
        const busyLi = document.createElement("li");
        busyLi.className = "palette__item";
        busyLi.setAttribute("aria-disabled", "true");
        const busySpan = document.createElement("span");
        busySpan.className = "palette__item-label";
        busySpan.textContent = "Buscando…";
        busyLi.appendChild(busySpan);
        resultsEl.appendChild(busyLi);

      } else if (searchResults.length > 0) {
        const groupLi = document.createElement("li");
        groupLi.className = "palette__group";
        groupLi.textContent = "Resultados";
        resultsEl.appendChild(groupLi);

        searchResults.forEach(function (result) {
          const pseudoAction = {
            id: "fts." + result.type + "." + result.id,
            label: result.label,
            hint: hintForType(result.type),
            handler: handlerForResult(result)
          };
          allRenderItems.push(pseudoAction);

          const idx = allRenderItems.length - 1;
          const li = document.createElement("li");
          li.className = "palette__item";
          li.setAttribute("role", "option");
          li.setAttribute("data-action-id", pseudoAction.id);
          li.setAttribute("data-index", String(idx));
          if (idx === state.activeIndex) {
            li.setAttribute("data-active", "true");
          }

          const labelSpan = document.createElement("span");
          labelSpan.className = "palette__item-label";
          labelSpan.textContent = result.label;
          li.appendChild(labelSpan);

          const hintSpan = document.createElement("span");
          hintSpan.className = "palette__item-hint";
          hintSpan.textContent = pseudoAction.hint;
          li.appendChild(hintSpan);

          li.addEventListener("click", function () {
            executeAt(parseInt(li.getAttribute("data-index"), 10));
          });
          li.addEventListener("mouseenter", function () {
            state.activeIndex = parseInt(li.getAttribute("data-index"), 10);
            updateActiveHighlight();
          });

          resultsEl.appendChild(li);
        });
      }
    }

    // ---- Grupos de ações filtradas ----
    const ftsOffset = allRenderItems.length; // índices das ações começam aqui

    if (state.filtered.length === 0) {
      if (allRenderItems.length === 0 && !isSearching) {
        emptyEl.hidden = false;
      } else {
        emptyEl.hidden = true;
      }
      // Garante activeIndex válido
      if (state.activeIndex >= allRenderItems.length && allRenderItems.length > 0) {
        state.activeIndex = 0;
      }
      return;
    }
    emptyEl.hidden = true;

    // Agrupar preservando ordem de aparição dos grupos no registro filtrado.
    const groupsOrder = [];
    const grouped = {};
    state.filtered.forEach(function (a) {
      if (!grouped[a.group]) {
        grouped[a.group] = [];
        groupsOrder.push(a.group);
      }
      grouped[a.group].push(a);
    });

    groupsOrder.forEach(function (groupName) {
      const groupLi = document.createElement("li");
      groupLi.className = "palette__group";
      groupLi.textContent = groupName;
      resultsEl.appendChild(groupLi);

      grouped[groupName].forEach(function (action) {
        allRenderItems.push(action);
        const idx = allRenderItems.length - 1;

        const li = document.createElement("li");
        li.className = "palette__item";
        li.setAttribute("role", "option");
        li.setAttribute("data-action-id", action.id);
        li.setAttribute("data-index", String(idx));
        if (idx === state.activeIndex) {
          li.setAttribute("data-active", "true");
        }

        const labelSpan = document.createElement("span");
        labelSpan.className = "palette__item-label";
        labelSpan.textContent = action.label;
        li.appendChild(labelSpan);

        if (action.hint) {
          const hintSpan = document.createElement("span");
          hintSpan.className = "palette__item-hint";
          hintSpan.textContent = action.hint;
          li.appendChild(hintSpan);
        }

        li.addEventListener("click", function () {
          executeAt(parseInt(li.getAttribute("data-index"), 10));
        });
        li.addEventListener("mouseenter", function () {
          state.activeIndex = parseInt(li.getAttribute("data-index"), 10);
          updateActiveHighlight();
        });

        resultsEl.appendChild(li);
      });
    });

    // Garante activeIndex dentro dos limites após rebuild de allRenderItems.
    if (state.activeIndex < 0 || state.activeIndex >= allRenderItems.length) {
      state.activeIndex = allRenderItems.length > 0 ? 0 : -1;
    }

    void ftsOffset; // referência usada implicitamente via allRenderItems
  }

  function updateActiveHighlight() {
    if (!resultsEl) return;
    const items = resultsEl.querySelectorAll(".palette__item");
    items.forEach(function (it) {
      const idxAttr = it.getAttribute("data-index");
      if (idxAttr === null) return; // item não navegável (ex.: "Buscando…")
      const idx = parseInt(idxAttr, 10);
      if (idx === state.activeIndex) {
        it.setAttribute("data-active", "true");
        it.scrollIntoView({ block: "nearest" });
      } else {
        it.removeAttribute("data-active");
      }
    });
  }

  // ---------- Abertura / fechamento ----------
  function open() {
    if (!modalEl) return;
    // Reseta estado de busca FTS5
    searchResults = [];
    isSearching = false;
    lastSearchQuery = "";
    clearTimeout(searchDebounceTimer);

    state.isOpen = true;
    inputEl.value = "";
    recomputeFiltered("");
    state.activeIndex = 0;
    render();
    modalEl.setAttribute("data-open", "true");
    // Foco após o frame para garantir que o display: flex já foi aplicado.
    requestAnimationFrame(function () { inputEl.focus(); });
  }

  function close() {
    if (!modalEl) return;
    clearTimeout(searchDebounceTimer);
    state.isOpen = false;
    modalEl.setAttribute("data-open", "false");
  }

  function isOpen() {
    return state.isOpen;
  }

  // ---------- Execução ----------
  function executeAt(index) {
    if (index < 0 || index >= allRenderItems.length) return;
    const item = allRenderItems[index];
    close();
    try {
      item.handler();
    } catch (e) {
      console.error("[palette] erro ao executar", item.id, e);
    }
  }

  // ---------- Eventos do palette ----------
  function handleKeyDown(e) {
    if (!state.isOpen) return;

    if (e.key === "Escape") {
      e.preventDefault();
      close();
      return;
    }

    const total = allRenderItems.length;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (total === 0) return;
      state.activeIndex = (state.activeIndex + 1) % total;
      updateActiveHighlight();
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (total === 0) return;
      state.activeIndex = (state.activeIndex - 1 + total) % total;
      updateActiveHighlight();
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      executeAt(state.activeIndex);
      return;
    }
  }

  function handleInput() {
    recomputeFiltered(inputEl.value);
    render();

    // Debounce busca FTS5
    clearTimeout(searchDebounceTimer);
    const currentQuery = inputEl.value;
    searchDebounceTimer = setTimeout(function () {
      fetchSearchResults(currentQuery);
    }, 250);
  }

  function handleBackdropClick(e) {
    // Clique fora da .palette fecha; clique dentro não.
    if (e.target === modalEl) {
      close();
    }
  }

  // ---------- Inicialização ----------
  function setup() {
    modalEl = document.getElementById("command-palette");
    if (!modalEl) return;
    inputEl = modalEl.querySelector(".palette__input");
    resultsEl = modalEl.querySelector(".palette__results");
    emptyEl = modalEl.querySelector(".palette__empty");

    inputEl.addEventListener("input", handleInput);
    inputEl.addEventListener("keydown", handleKeyDown);
    modalEl.addEventListener("click", handleBackdropClick);

    registerDefaultActions();
  }

  // ---------- Ações default da Sprint 0.5 ----------
  function registerDefaultActions() {
    // --- Ações de UI ---
    register({
      id: "theme.dark",
      label: "Tema: escuro",
      group: "Ações",
      keywords: ["tema", "escuro", "dark", "crt"],
      hint: null,
      handler: function () { window.CIRCE.theme.set("dark"); }
    });
    register({
      id: "theme.light",
      label: "Tema: claro",
      group: "Ações",
      keywords: ["tema", "claro", "light", "papel"],
      hint: null,
      handler: function () { window.CIRCE.theme.set("light"); }
    });
    register({
      id: "theme.toggle",
      label: "Tema: alternar",
      group: "Ações",
      keywords: ["tema", "alternar", "toggle"],
      hint: null,
      handler: function () { window.CIRCE.theme.toggle(); }
    });

    // Accents — gerados dinamicamente a partir do registro de paletas.
    if (window.CIRCE && window.CIRCE.accent && typeof window.CIRCE.accent.list === "function") {
      window.CIRCE.accent.list().forEach(function (entry) {
        register({
          id: "accent." + entry.id,
          label: "Accent: " + entry.label,
          group: "Ações",
          keywords: ["accent", "destaque", "cor", entry.id, entry.label],
          hint: null,
          handler: (function (accentId) {
            return function () { window.CIRCE.accent.set(accentId); };
          })(entry.id)
        });
      });
    }

    register({
      id: "shortcuts.show",
      label: "Mostrar atalhos disponíveis",
      group: "Ações",
      keywords: ["atalhos", "shortcuts", "ajuda", "help"],
      hint: "Ctrl+/",
      handler: function () {
        const m = document.getElementById("shortcuts-modal");
        if (m) m.setAttribute("data-open", "true");
      }
    });

    // --- Páginas ---
    [
      { id: "cases", label: "Ir para Casos", path: "/cases" },
      { id: "persons", label: "Ir para Pessoas", path: "/persons" },
      { id: "organizations", label: "Ir para Organizações", path: "/organizations" },
      { id: "documents", label: "Ir para Documentos", path: "/documents" },
      { id: "reports", label: "Ir para Relatórios", path: "/reports" }
    ].forEach(function (page) {
      register({
        id: "nav." + page.id,
        label: page.label,
        group: "Páginas",
        keywords: ["ir", "navegar", "abrir", page.id, page.label],
        hint: null,
        handler: (function (path) {
          return function () { window.location.href = path; };
        })(page.path)
      });
    });

    // --- Workspaces (vazio na 0.5) ---
    // Marcador para ADR-010 — quando a ADR for promovida nas sprints 03–05,
    // este grupo será populado dinamicamente a partir dos casos abertos.
  }

  // ---------- API pública ----------
  window.CIRCE = window.CIRCE || {};
  window.CIRCE.palette = {
    open: open,
    close: close,
    isOpen: isOpen,
    register: register
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
