/* ============================================================
   CIRCE Intel Desk — organizations.js
   Tela funcional de Organizações (RF-004) — Sprint 01-B, B4.
   Padrão: IIFE, "use strict", namespace window.CIRCE.
   ============================================================ */

(function () {
  "use strict";

  var API_BASE = "/api/organizations";

  var state = {
    orgs: [],
    sortBy: "name",
    descending: false,
    includeArchived: false,
    mode: "create",
    editingId: null,
    editingOriginal: null
  };

  var tbodyEl, countEl, emptyEl, titleLabelEl, newBtnEl, showArchivedEl;
  var modalEl, modalTitleEl, modalSubtitleEl;
  var formNameEl, formSiglasEl, formTypeEl, formAlcunhasEl;
  var formAreaEl, formSourceEl, formReliabilityEl, formNotesEl;
  var nameErrorEl, saveBtnEl, cancelEls;
  var archiveModalEl, archiveNameEl, archiveConfirmBtnEl, archiveCancelEls;
  var archiveTargetId = null;

  var ORG_TYPE_LABELS = {
    "faccao_prisional": "Facção prisional",
    "milicia": "Milícia",
    "orcrim_trafico": "ORCRIM tráfico",
    "orcrim_patrimonial": "ORCRIM patrimonial",
    "outra": "Outra"
  };

  function handleAuthLapse(response) {
    var isHtml = response.redirected ||
      (response.headers.get("content-type") || "").indexOf("text/html") >= 0;
    if (response.status === 401 || isHtml) {
      window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
      return true;
    }
    return false;
  }

  function toast(type, title, msg) {
    if (window.CIRCE && window.CIRCE.toast) {
      window.CIRCE.toast[type](title, msg);
    }
  }

  // ---------- Listar ----------
  function loadOrgs(onLoaded) {
    var url = API_BASE
      + "?include_archived=" + (state.includeArchived ? "true" : "false")
      + "&sort_by=" + encodeURIComponent(state.sortBy)
      + "&descending=" + (state.descending ? "true" : "false");

    fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (data === null) return;
        state.orgs = Array.isArray(data) ? data : [];
        renderTable();
        if (typeof onLoaded === "function") onLoaded();
      })
      .catch(function (err) {
        console.error("[orgs] erro ao carregar", err);
        toast("error", "Erro", "Não foi possível carregar a lista de organizações.");
      });
  }

  function updateTitleLabel() {
    if (!titleLabelEl) return;
    titleLabelEl.textContent = state.includeArchived
      ? "─── TODAS AS ORGANIZAÇÕES ───"
      : "─── ORGANIZAÇÕES ATIVAS ───";
  }

  // ---------- Renderizar ----------
  function renderTable(highlightId) {
    if (!tbodyEl) return;
    tbodyEl.innerHTML = "";

    var pad = function(n) { return (n < 10 ? "0" : "") + n; };
    if (countEl) countEl.textContent = pad(state.orgs.length) + " REGISTRO" + (state.orgs.length === 1 ? "" : "S");

    if (state.orgs.length === 0) {
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;

    state.orgs.forEach(function (o) {
      tbodyEl.appendChild(buildRow(o, highlightId != null && o.id === highlightId));
    });
  }

  function buildRow(o, highlight) {
    var tr = document.createElement("tr");
    tr.setAttribute("data-org-id", String(o.id));
    if (highlight) tr.setAttribute("data-selected", "true");

    var tdName = document.createElement("td");
    tdName.style.padding = "var(--space-2) var(--space-3)";
    tdName.textContent = o.name;
    tr.appendChild(tdName);

    var tdType = document.createElement("td");
    tdType.style.cssText = "padding:var(--space-2) var(--space-3);font-family:var(--font-mono);font-size:var(--font-size-xs);color:var(--text-secondary);";
    tdType.textContent = o.org_type ? (ORG_TYPE_LABELS[o.org_type] || o.org_type) : "—";
    tr.appendChild(tdType);

    var tdSiglas = document.createElement("td");
    tdSiglas.style.cssText = "padding:var(--space-2) var(--space-3);font-family:var(--font-mono);font-size:var(--font-size-xs);color:var(--text-secondary);";
    tdSiglas.textContent = o.siglas || "—";
    tr.appendChild(tdSiglas);

    var tdStatus = document.createElement("td");
    tdStatus.style.padding = "var(--space-2) var(--space-3)";
    var badgeClass = o.status === "active" ? "badge badge--ativo" : "badge badge--arquivado";
    var badgeText = o.status === "active" ? "[ATIVO]" : "[ARQUIVADO]";
    tdStatus.innerHTML = '<span class="' + badgeClass + '">' + badgeText + "</span>";
    tr.appendChild(tdStatus);

    var tdAction = document.createElement("td");
    tdAction.style.padding = "var(--space-2) var(--space-3)";

    var openBtn = document.createElement("button");
    openBtn.className = "btn btn--text";
    openBtn.type = "button";
    openBtn.textContent = "Abrir";
    openBtn.addEventListener("click", function () {
      window.location.href = "/organizations/" + o.id;
    });
    tdAction.appendChild(openBtn);

    var editBtn = document.createElement("button");
    editBtn.className = "btn btn--text";
    editBtn.type = "button";
    editBtn.textContent = "Editar";
    editBtn.setAttribute("data-action", "edit");
    tdAction.appendChild(editBtn);

    if (o.status !== "archived") {
      var archiveBtn = document.createElement("button");
      archiveBtn.className = "btn btn--text";
      archiveBtn.type = "button";
      archiveBtn.textContent = "Arquivar";
      archiveBtn.setAttribute("data-action", "archive");
      tdAction.appendChild(archiveBtn);
    }

    tr.appendChild(tdAction);
    return tr;
  }

  function findOrg(id) {
    for (var i = 0; i < state.orgs.length; i++) {
      if (state.orgs[i].id === id) return state.orgs[i];
    }
    return null;
  }

  // ---------- Ordenação ----------
  function setupSortHeaders() {
    var headers = document.querySelectorAll("[data-sort-key]");
    headers.forEach(function (th) {
      th.addEventListener("click", function () {
        var key = th.getAttribute("data-sort-key");
        if (state.sortBy === key) {
          state.descending = !state.descending;
        } else {
          state.sortBy = key;
          state.descending = false;
        }
        updateSortIndicators();
        loadOrgs();
      });
    });
    updateSortIndicators();
  }

  function updateSortIndicators() {
    document.querySelectorAll("[data-sort-key]").forEach(function (th) {
      var ind = th.querySelector(".sort-indicator");
      if (!ind) return;
      ind.textContent = th.getAttribute("data-sort-key") === state.sortBy
        ? (state.descending ? "↓" : "↑") : "";
    });
  }

  // ---------- Modal criar/editar ----------
  function fillForm(o) {
    if (formNameEl) formNameEl.value = o ? (o.name || "") : "";
    if (formSiglasEl) formSiglasEl.value = o ? (o.siglas || "") : "";
    if (formTypeEl) formTypeEl.value = o ? (o.org_type || "") : "";
    if (formAlcunhasEl) formAlcunhasEl.value = o ? (o.alcunhas || "") : "";
    if (formAreaEl) formAreaEl.value = o ? (o.area_atuacao || "") : "";
    if (formSourceEl) formSourceEl.value = o ? (o.source || "") : "";
    if (formReliabilityEl) formReliabilityEl.value = o ? (o.reliability_level || "pending") : "pending";
    if (formNotesEl) formNotesEl.value = o ? (o.notes || "") : "";
  }

  function openModalCreate() {
    if (!modalEl) return;
    state.mode = "create";
    state.editingId = null;
    state.editingOriginal = null;
    if (modalTitleEl) modalTitleEl.textContent = "NOVA ORGANIZAÇÃO";
    if (modalSubtitleEl) modalSubtitleEl.textContent = "RF-004";
    if (saveBtnEl) saveBtnEl.textContent = "SALVAR ORGANIZAÇÃO";
    fillForm(null);
    clearNameError();
    validateName();
    modalEl.setAttribute("data-open", "true");
    requestAnimationFrame(function () { if (formNameEl) formNameEl.focus(); });
  }

  function openModalEdit(o) {
    if (!modalEl || !o) return;
    state.mode = "edit";
    state.editingId = o.id;
    state.editingOriginal = o;
    if (modalTitleEl) modalTitleEl.textContent = "EDITAR ORGANIZAÇÃO";
    if (modalSubtitleEl) modalSubtitleEl.textContent = "RF-004";
    if (saveBtnEl) saveBtnEl.textContent = "SALVAR ALTERAÇÕES";
    fillForm(o);
    clearNameError();
    validateName();
    modalEl.setAttribute("data-open", "true");
    requestAnimationFrame(function () { if (formNameEl) { formNameEl.focus(); formNameEl.select(); } });
  }

  function closeModal() {
    if (modalEl) modalEl.setAttribute("data-open", "false");
  }

  function clearNameError() {
    if (formNameEl) formNameEl.classList.remove("input--error");
    if (nameErrorEl) { nameErrorEl.textContent = ""; nameErrorEl.hidden = true; }
  }

  function showNameError(msg) {
    if (formNameEl) formNameEl.classList.add("input--error");
    if (nameErrorEl) { nameErrorEl.textContent = msg; nameErrorEl.hidden = false; }
  }

  function validateName() {
    var valid = formNameEl && formNameEl.value.trim().length > 0;
    if (saveBtnEl) saveBtnEl.disabled = !valid;
    return valid;
  }

  function readForm() {
    return {
      name: formNameEl ? formNameEl.value.trim() : "",
      siglas: formSiglasEl ? formSiglasEl.value.trim() : "",
      org_type: formTypeEl ? formTypeEl.value : "",
      alcunhas: formAlcunhasEl ? formAlcunhasEl.value.trim() : "",
      area_atuacao: formAreaEl ? formAreaEl.value.trim() : "",
      source: formSourceEl ? formSourceEl.value.trim() : "",
      reliability_level: formReliabilityEl ? formReliabilityEl.value : "pending",
      notes: formNotesEl ? formNotesEl.value.trim() : ""
    };
  }

  function submitOrg() {
    if (!validateName()) {
      showNameError("O nome da organização é obrigatório.");
      if (formNameEl) formNameEl.focus();
      return;
    }
    clearNameError();
    if (state.mode === "edit") { submitEdit(); } else { submitCreate(); }
  }

  function submitCreate() {
    if (saveBtnEl) saveBtnEl.disabled = true;
    var f = readForm();
    var payload = { name: f.name, reliability_level: f.reliability_level };
    if (f.siglas) payload.siglas = f.siglas;
    if (f.org_type) payload.org_type = f.org_type;
    if (f.alcunhas) payload.alcunhas = f.alcunhas;
    if (f.area_atuacao) payload.area_atuacao = f.area_atuacao;
    if (f.source) payload.source = f.source;
    if (f.notes) payload.notes = f.notes;

    fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (created) {
        if (!created) return;
        closeModal();
        state.orgs.unshift(created);
        renderTable(created.id);
        toast("success", "Organização cadastrada", created.name);
      })
      .catch(function (err) {
        if (saveBtnEl) saveBtnEl.disabled = false;
        console.error("[orgs] erro ao criar", err);
        toast("error", "Erro", "Não foi possível cadastrar a organização.");
      });
  }

  function submitEdit() {
    var id = state.editingId;
    var orig = state.editingOriginal;
    if (id == null || !orig) return;

    var f = readForm();
    var fields = ["name", "siglas", "org_type", "alcunhas", "area_atuacao", "source", "reliability_level", "notes"];
    var payload = {};
    fields.forEach(function (k) {
      var origVal = orig[k] == null ? "" : String(orig[k]);
      if (f[k] !== origVal) {
        payload[k] = (f[k] === "" && k !== "name" && k !== "reliability_level") ? null : f[k];
      }
    });

    if (Object.keys(payload).length === 0) {
      closeModal();
      toast("info", "Sem alterações", "Nenhum campo foi modificado.");
      return;
    }

    if (saveBtnEl) saveBtnEl.disabled = true;

    fetch(API_BASE + "/" + id, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (updated) {
        if (!updated) return;
        closeModal();
        for (var i = 0; i < state.orgs.length; i++) {
          if (state.orgs[i].id === updated.id) { state.orgs[i] = updated; break; }
        }
        renderTable(updated.id);
        toast("success", "Organização atualizada", updated.name);
      })
      .catch(function (err) {
        if (saveBtnEl) saveBtnEl.disabled = false;
        console.error("[orgs] erro ao editar", err);
        toast("error", "Erro", "Não foi possível salvar as alterações.");
      });
  }

  // ---------- Arquivar ----------
  function openArchiveModal(o) {
    if (!archiveModalEl || !o) return;
    archiveTargetId = o.id;
    if (archiveNameEl) archiveNameEl.textContent = o.name;
    archiveModalEl.setAttribute("data-open", "true");
    requestAnimationFrame(function () { if (archiveConfirmBtnEl) archiveConfirmBtnEl.focus(); });
  }

  function closeArchiveModal() {
    if (archiveModalEl) archiveModalEl.setAttribute("data-open", "false");
    archiveTargetId = null;
  }

  function confirmArchive() {
    var id = archiveTargetId;
    if (id == null) { closeArchiveModal(); return; }
    if (archiveConfirmBtnEl) archiveConfirmBtnEl.disabled = true;

    fetch(API_BASE + "/" + id, {
      method: "DELETE",
      credentials: "same-origin"
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return;
        if (!r.ok) throw new Error("HTTP " + r.status);
        loadOrgs();
        toast("success", "Organização arquivada", "");
      })
      .catch(function (err) {
        console.error("[orgs] erro ao arquivar", err);
        toast("error", "Erro", "Não foi possível arquivar a organização.");
      })
      .finally(function () {
        if (archiveConfirmBtnEl) archiveConfirmBtnEl.disabled = false;
        closeArchiveModal();
      });
  }

  // ---------- Delegação de cliques na tabela ----------
  function onTbodyClick(e) {
    var btn = e.target.closest ? e.target.closest("button[data-action]") : null;
    if (!btn) return;
    var tr = btn.closest("tr[data-org-id]");
    if (!tr) return;
    var id = parseInt(tr.getAttribute("data-org-id"), 10);
    if (isNaN(id)) return;
    var o = findOrg(id);
    if (!o) return;
    var action = btn.getAttribute("data-action");
    if (action === "edit") { openModalEdit(o); }
    else if (action === "archive") { openArchiveModal(o); }
  }

  // ---------- Palette ----------
  function registerPaletteAction() {
    if (window.CIRCE && window.CIRCE.palette && typeof window.CIRCE.palette.register === "function") {
      window.CIRCE.palette.register({
        id: "orgs.new",
        label: "Nova organização",
        group: "Ações",
        keywords: ["nova", "organização", "org", "faccao", "milicia", "orcrim"],
        hint: "Ctrl+Alt+O",
        handler: function () { openModalCreate(); }
      });
    }
  }

  // ---------- Init ----------
  function setup() {
    tbodyEl = document.getElementById("orgs-tbody");
    if (!tbodyEl) return;

    countEl = document.getElementById("orgs-count");
    emptyEl = document.getElementById("orgs-empty");
    titleLabelEl = document.getElementById("orgs-title-label");
    newBtnEl = document.getElementById("orgs-new-btn");
    showArchivedEl = document.getElementById("orgs-show-archived");

    modalEl = document.getElementById("org-modal");
    if (modalEl) {
      modalTitleEl = modalEl.querySelector("#org-modal-title");
      modalSubtitleEl = modalEl.querySelector("#org-modal-subtitle");
      formNameEl = modalEl.querySelector("#org-form-name");
      formSiglasEl = modalEl.querySelector("#org-form-siglas");
      formTypeEl = modalEl.querySelector("#org-form-type");
      formAlcunhasEl = modalEl.querySelector("#org-form-alcunhas");
      formAreaEl = modalEl.querySelector("#org-form-area");
      formSourceEl = modalEl.querySelector("#org-form-source");
      formReliabilityEl = modalEl.querySelector("#org-form-reliability");
      formNotesEl = modalEl.querySelector("#org-form-notes");
      nameErrorEl = modalEl.querySelector("#org-form-name-error");
      saveBtnEl = modalEl.querySelector("#org-form-save");
      cancelEls = modalEl.querySelectorAll("[data-modal-close]");
    }

    archiveModalEl = document.getElementById("org-archive-modal");
    if (archiveModalEl) {
      archiveNameEl = archiveModalEl.querySelector("#org-archive-name");
      archiveConfirmBtnEl = archiveModalEl.querySelector("#org-archive-confirm");
      archiveCancelEls = archiveModalEl.querySelectorAll("[data-archive-cancel]");
    }

    if (newBtnEl) newBtnEl.addEventListener("click", openModalCreate);

    if (showArchivedEl) {
      showArchivedEl.addEventListener("change", function () {
        state.includeArchived = !!showArchivedEl.checked;
        updateTitleLabel();
        loadOrgs();
      });
    }

    if (formNameEl) {
      formNameEl.addEventListener("input", function () {
        clearNameError();
        validateName();
      });
    }

    if (saveBtnEl) saveBtnEl.addEventListener("click", submitOrg);

    if (cancelEls) cancelEls.forEach(function (el) { el.addEventListener("click", closeModal); });
    if (modalEl) modalEl.addEventListener("click", function (e) { if (e.target === modalEl) closeModal(); });

    if (archiveConfirmBtnEl) archiveConfirmBtnEl.addEventListener("click", confirmArchive);
    if (archiveCancelEls) archiveCancelEls.forEach(function (el) { el.addEventListener("click", closeArchiveModal); });
    if (archiveModalEl) archiveModalEl.addEventListener("click", function (e) { if (e.target === archiveModalEl) closeArchiveModal(); });

    if (tbodyEl) tbodyEl.addEventListener("click", onTbodyClick);

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (archiveModalEl && archiveModalEl.getAttribute("data-open") === "true") {
          e.preventDefault(); closeArchiveModal(); return;
        }
        if (modalEl && modalEl.getAttribute("data-open") === "true") {
          e.preventDefault(); closeModal(); return;
        }
      }
      if (e.altKey && !e.metaKey && (e.key === "o" || e.key === "O")) {
        var paletteOpen = window.CIRCE && window.CIRCE.palette
          && typeof window.CIRCE.palette.isOpen === "function"
          && window.CIRCE.palette.isOpen();
        if (!paletteOpen) { e.preventDefault(); openModalCreate(); }
      }
    });

    updateTitleLabel();
    setupSortHeaders();
    registerPaletteAction();
    loadOrgs();
  }

  window.CIRCE = window.CIRCE || {};
  window.CIRCE.orgs = { reload: loadOrgs, openNew: openModalCreate };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();