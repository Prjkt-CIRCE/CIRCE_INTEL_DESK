/* ============================================================
   CIRCE Intel Desk — workspaces.js
   Gestão de workspaces (slots 1-9) com persistência localStorage.

   ADR-010, D-02-9-01.
   API pública: window.CIRCE.workspaces — desenhada para futura
   migração para banco sem quebrar chamadores.

   Sprint 02-9.
   ============================================================ */

(function () {
  "use strict";

  var STORAGE_KEY      = "circe_workspaces_v1";
  var ACTIVE_SLOT_KEY  = "circe_ws_active_slot";
  var MAX_SLOTS        = 9;

  // ---------- Utilitários ----------

  function handleAuthLapse(r) {
    if (r.status === 401 || r.redirected) {
      window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
      return true;
    }
    return false;
  }

  function toast(msg, tipo) {
    if (window.CIRCE && window.CIRCE.toast) {
      if (tipo === "success")      window.CIRCE.toast.success(msg, "");
      else if (tipo === "error")   window.CIRCE.toast.error(msg, "");
      else if (tipo === "warning") window.CIRCE.toast.warning(msg, "");
      else                         window.CIRCE.toast.info(msg, "");
    }
  }

  // ---------- Persistência ----------

  function loadFromStorage() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function saveToStorage(workspaces) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(workspaces));
    } catch (e) {
      // silent
    }
  }

  function getWorkspaces() {
    return loadFromStorage();
  }

  function getActiveSlot() {
    try {
      var raw = localStorage.getItem(ACTIVE_SLOT_KEY);
      var n = parseInt(raw, 10);
      if (n >= 1 && n <= MAX_SLOTS) return n;
    } catch (e) {
      // fall through
    }
    return 1;
  }

  function setActiveSlot(slot) {
    try {
      localStorage.setItem(ACTIVE_SLOT_KEY, String(slot));
    } catch (e) {
      // silent
    }
    updateStatusBar();
    renderWorkspaceBar();
  }

  function getWorkspaceBySlot(slot) {
    var workspaces = loadFromStorage();
    for (var i = 0; i < workspaces.length; i++) {
      if (workspaces[i].slot === slot) return workspaces[i];
    }
    return null;
  }

  // ---------- Funções públicas ----------

  function openCase(caseId, caseCode, caseName) {
    var workspaces = loadFromStorage();

    // Verifica se já existe workspace com esse caseId
    for (var i = 0; i < workspaces.length; i++) {
      if (workspaces[i].caseId === caseId) {
        setActiveSlot(workspaces[i].slot);
        window.location.href = "/cases/" + caseId;
        return;
      }
    }

    // Encontra primeiro slot livre
    var occupiedSlots = {};
    for (var j = 0; j < workspaces.length; j++) {
      occupiedSlots[workspaces[j].slot] = true;
    }
    var freeSlot = null;
    for (var s = 1; s <= MAX_SLOTS; s++) {
      if (!occupiedSlots[s]) { freeSlot = s; break; }
    }

    if (freeSlot === null) {
      toast("Máximo de 9 workspaces atingido.", "warning");
      return;
    }

    var ws = {
      id: "ws_" + freeSlot,
      slot: freeSlot,
      caseId: caseId,
      caseCode: caseCode,
      caseName: caseName,
      createdAt: new Date().toISOString()
    };
    workspaces.push(ws);
    saveToStorage(workspaces);
    setActiveSlot(freeSlot);
    window.location.href = "/cases/" + caseId;
  }

  function closeWorkspace(slot) {
    var workspaces = loadFromStorage();
    var filtered = [];
    for (var i = 0; i < workspaces.length; i++) {
      if (workspaces[i].slot !== slot) filtered.push(workspaces[i]);
    }
    saveToStorage(filtered);

    var active = getActiveSlot();
    if (active === slot) {
      // Ativa próximo slot ocupado, ou slot 1 se nenhum
      var nextSlot = 1;
      if (filtered.length > 0) nextSlot = filtered[0].slot;
      try { localStorage.setItem(ACTIVE_SLOT_KEY, String(nextSlot)); } catch (e) {}
    }

    renderWorkspaceBar();
    updateStatusBar();
    window.location.href = "/cases";
  }

  function getActiveCase() {
    var slot = getActiveSlot();
    var ws = getWorkspaceBySlot(slot);
    if (!ws) return null;
    return { caseId: ws.caseId, caseCode: ws.caseCode, caseName: ws.caseName };
  }

  // ---------- Renderização ----------

  function renderWorkspaceBar() {
    var bar = document.getElementById("workspace-bar");
    if (!bar) return;

    var workspaces = loadFromStorage();
    if (workspaces.length === 0) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;
    bar.innerHTML = "";

    var activeSlot = getActiveSlot();

    workspaces.forEach(function (ws) {
      var slotEl = document.createElement("div");
      slotEl.className = "ws-bar__slot" +
        (ws.slot === activeSlot ? " ws-bar__slot--active" : "");
      slotEl.title = ws.caseName + " (Ctrl+" + ws.slot + ")";

      var labelEl = document.createElement("span");
      labelEl.className = "ws-bar__slot-label";
      labelEl.textContent = ws.slot + ": " + ws.caseCode;

      var closeBtn = document.createElement("button");
      closeBtn.className = "ws-bar__slot-close";
      closeBtn.setAttribute("aria-label", "Fechar workspace " + ws.slot);
      closeBtn.textContent = "×";
      closeBtn.addEventListener("click", (function (slot) {
        return function (e) {
          e.stopPropagation();
          closeWorkspace(slot);
        };
      })(ws.slot));

      slotEl.appendChild(labelEl);
      slotEl.appendChild(closeBtn);

      slotEl.addEventListener("click", (function (slot, caseId) {
        return function () {
          setActiveSlot(slot);
          window.location.href = "/cases/" + caseId;
        };
      })(ws.slot, ws.caseId));

      bar.appendChild(slotEl);
    });
  }

  function updateStatusBar() {
    var el = document.querySelector("[data-status-workspace]");
    if (!el) return;
    var ws = getWorkspaceBySlot(getActiveSlot());
    el.textContent = ws ? ws.caseCode : "DEFAULT";
  }

  // ---------- Palette actions ----------

  function registerPaletteActions() {
    if (!window.CIRCE || !window.CIRCE.palette) return;

    var workspaces = loadFromStorage();
    workspaces.forEach(function (ws) {
      window.CIRCE.palette.register({
        id: "ws.goto." + ws.slot,
        label: "Workspace " + ws.slot + ": " + ws.caseName,
        group: "Workspaces",
        keywords: ["workspace", ws.caseCode, ws.caseName],
        hint: "Ctrl+" + ws.slot,
        handler: (function (slot, caseId) {
          return function () {
            setActiveSlot(slot);
            window.location.href = "/cases/" + caseId;
          };
        })(ws.slot, ws.caseId)
      });
    });

    window.CIRCE.palette.register({
      id: "ws.close.active",
      label: "Fechar workspace ativo",
      group: "Workspaces",
      keywords: ["fechar", "workspace", "close"],
      hint: null,
      handler: function () { closeWorkspace(getActiveSlot()); }
    });

    // Abre caso da URL atual no workspace
    window.CIRCE.palette.register({
      id: "ws.open.current",
      label: "Abrir caso atual no workspace",
      group: "Workspaces",
      keywords: ["workspace", "abrir", "caso", "pinnar"],
      hint: null,
      handler: function () {
        var parts = window.location.pathname.split("/");
        var caseId = null;
        // /cases/{id}
        for (var i = 0; i < parts.length; i++) {
          if (parts[i] === "cases" && parts[i + 1]) {
            var n = parseInt(parts[i + 1], 10);
            if (!isNaN(n)) { caseId = n; break; }
          }
        }
        if (!caseId) {
          toast("Nenhum caso aberto na página atual.", "warning");
          return;
        }
        fetch("/api/cases/" + caseId, { credentials: "same-origin" })
          .then(function (r) {
            if (handleAuthLapse(r)) return null;
            if (!r.ok) return null;
            return r.json();
          })
          .then(function (data) {
            if (!data) return;
            openCase(data.id, data.case_code, data.name);
          })
          .catch(function () {
            toast("Erro ao abrir caso no workspace.", "error");
          });
      }
    });
  }

  // ---------- Setup ----------

  function setup() {
    renderWorkspaceBar();
    updateStatusBar();

    // Sincronização passiva: se a URL é /cases/{id}, ativa o workspace
    // correspondente se existir
    var parts = window.location.pathname.split("/");
    for (var i = 0; i < parts.length; i++) {
      if (parts[i] === "cases" && parts[i + 1]) {
        var n = parseInt(parts[i + 1], 10);
        if (!isNaN(n)) {
          var workspaces = loadFromStorage();
          for (var j = 0; j < workspaces.length; j++) {
            if (workspaces[j].caseId === n) {
              try { localStorage.setItem(ACTIVE_SLOT_KEY, String(workspaces[j].slot)); } catch (e) {}
              updateStatusBar();
              renderWorkspaceBar();
              break;
            }
          }
          break;
        }
      }
    }

    // Atalhos Ctrl+1 a Ctrl+9
    document.addEventListener("keydown", function (e) {
      if (!e.ctrlKey) return;
      var digit = parseInt(e.key, 10);
      if (isNaN(digit) || digit < 1 || digit > 9) return;
      var ws = getWorkspaceBySlot(digit);
      if (!ws) return; // não previne default se slot vazio
      e.preventDefault();
      setActiveSlot(digit);
      window.location.href = "/cases/" + ws.caseId;
    });

    // Registra ações na palette (pode não estar disponível ainda)
    if (window.CIRCE && window.CIRCE.palette) {
      registerPaletteActions();
    } else {
      // Tenta após scripts defer
      window.addEventListener("load", registerPaletteActions);
    }
  }

  // ---------- API pública ----------

  window.CIRCE = window.CIRCE || {};
  window.CIRCE.workspaces = {
    openCase:           openCase,
    closeWorkspace:     closeWorkspace,
    getActiveCase:      getActiveCase,
    getWorkspaces:      getWorkspaces,
    renderWorkspaceBar: renderWorkspaceBar
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
