/* ============================================================
   CIRCE Intel Desk — person_detail.js
   Tela de detalhe de uma pessoa (RF-002) — Sprint 01, Bloco 9, Sub-passo 9.6.
   Vínculos pessoa-caso (RF-003) — Sprint 01, Bloco 10, Sub-passo 10.6.

   Decisões do operador no 9.6 (preservadas):
     - (a) Renderização SPA-leve: busca GET /api/persons/{id} e popula slots.
     - (b/D58) "Editar" navega para /persons?edit={id}.
     - (c) Reativar arquivada: fora do escopo (D48).
     - (d) Voltar: link "< PESSOAS" + atalho Esc.

   Adições do 10.6 (RF-003) — espelho do case_detail.js (10.5):
     - loadLinks(): GET /api/links/person-case?person_id=N, renderiza tabela.
     - renderLinksTable(): popula #person-links-tbody.
     - Modal #modal-vincular-caso-backdrop: carrega <select> de casos ativos
       (D-B10-01: Opção A no MVP-0).
     - submitVincular(): POST /api/links/person-case; trata 409 (CA-003.6).
     - removeLink(linkId): DELETE /api/links/person-case/{id} após confirm().
   ============================================================ */

(function () {
  "use strict";

  var API_PERSONS = "/api/persons";
  var API_LINKS   = "/api/links/person-case";
  var API_CASES   = "/api/cases";

  // ---------- Rótulos legíveis ----------
  var ROLE_LABELS = {
    suspeito:     "Suspeito",
    investigado:  "Investigado",
    vitima:       "Vítima",
    testemunha:   "Testemunha",
    envolvido:    "Envolvido",
    interlocutor: "Interlocutor",
    outro:        "Outro"
  };

  var RELIABILITY_LABELS = {
    pending:   "Pendente",
    low:       "Baixo",
    medium:    "Médio",
    high:      "Alto",
    validated: "Validado"
  };

  // ---------- DOM refs — pessoa ----------
  var loadingEl      = null;
  var notFoundEl     = null;
  var contentEl      = null;
  var archivedNoteEl = null;
  var editBtnEl      = null;

  // ---------- DOM refs — vínculos ----------
  var linksLoadingEl   = null;
  var linksEmptyEl     = null;
  var linksTableWrapEl = null;
  var linksTbodyEl     = null;
  var btnVincularEl    = null;

  // ---------- DOM refs — modal ----------
  var modalBackdropEl     = null;
  var modalCloseEl        = null;
  var modalCancelEl       = null;
  var modalConfirmarEl    = null;
  var vcCaseSelect        = null;
  var vcCaseHint          = null;
  var vcRoleSelect        = null;
  var vcSourceInput       = null;
  var vcReliabilitySelect = null;
  var vcNotesInput        = null;

  var personId = null;

  // ---------- Utilitários de data (replicados de persons.js — nota de dívida) ----------
  var MESES = ["JAN","FEV","MAR","ABR","MAI","JUN",
               "JUL","AGO","SET","OUT","NOV","DEZ"];

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  function formatDateTime(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  function formatDateOnly(value) {
    if (!value) return "—";
    var s = String(value);
    var dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(s);
    var d = new Date(s);
    if (isNaN(d.getTime())) return s;
    if (dateOnly) {
      return pad2(d.getUTCDate()) + "." + MESES[d.getUTCMonth()] + "." + d.getUTCFullYear();
    }
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  function formatCpfDisplay(cpf) {
    if (!cpf) return "—";
    if (/^\d{11}$/.test(cpf)) {
      return cpf.slice(0,3) + "." + cpf.slice(3,6) + "." + cpf.slice(6,9) + "-" + cpf.slice(9);
    }
    return cpf;
  }

  function formatAliasesDisplay(aliases) {
    if (!aliases) return "—";
    var parts = aliases.split(";").map(function(s) { return s.trim(); }).filter(Boolean);
    return parts.length ? parts.join(" · ") : "—";
  }

  function statusBadgeHtml(status) {
    var map = {
      "active":   { cls: "badge--ativo",     txt: "[ATIVO]" },
      "archived": { cls: "badge--arquivado", txt: "[ARQUIVADO]" }
    };
    var entry = map[status] || { cls: "badge--arquivado", txt: "[" + String(status).toUpperCase() + "]" };
    return '<span class="badge ' + entry.cls + '">' + entry.txt + "</span>";
  }

  // ---------- Guarda de sessão expirada (D54) ----------
  function handleAuthLapse(response) {
    var isHtmlRedirect =
      response.redirected ||
      (response.headers.get("content-type") || "").indexOf("text/html") >= 0;
    if (response.status === 401 || isHtmlRedirect) {
      var next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = "/login?next=" + next;
      return true;
    }
    return false;
  }

  // ---------- Helper de toast (D53) ----------
  function toast(type, title, msg) {
    if (window.CIRCE && window.CIRCE.toast && window.CIRCE.toast[type]) {
      window.CIRCE.toast[type](title, msg);
    }
  }

  // ---------- Escape HTML ----------
  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ---------- Slots de campo da pessoa ----------
  function setField(field, value) {
    if (!contentEl) return;
    var el = contentEl.querySelector('[data-field="' + field + '"]');
    if (!el) return;
    var txt = (value === null || value === undefined || value === "") ? "—" : String(value);
    el.textContent = txt;
  }

  // ---------- Estados da tela principal ----------
  function showLoading() {
    if (loadingEl)  loadingEl.hidden  = false;
    if (notFoundEl) notFoundEl.hidden = true;
    if (contentEl)  contentEl.hidden  = true;
  }

  function showNotFound() {
    if (loadingEl)  loadingEl.hidden  = true;
    if (notFoundEl) notFoundEl.hidden = false;
    if (contentEl)  contentEl.hidden  = true;
  }

  function showContent() {
    if (loadingEl)  loadingEl.hidden  = true;
    if (notFoundEl) notFoundEl.hidden = true;
    if (contentEl)  contentEl.hidden  = false;
  }

  // ---------- Renderizar pessoa ----------
  function renderPerson(p) {
    setField("full_name", p.full_name);

    var badgeSlot = contentEl ? contentEl.querySelector('[data-field="status_badge"]') : null;
    if (badgeSlot) badgeSlot.innerHTML = statusBadgeHtml(p.status);

    setField("aliases_display", formatAliasesDisplay(p.aliases));
    setField("created_at", formatDateTime(p.created_at));
    setField("full_name_detail", p.full_name);
    setField("aliases_detail", formatAliasesDisplay(p.aliases));
    setField("cpf_display", formatCpfDisplay(p.cpf));
    setField("rg", p.rg);
    setField("birth_date", formatDateOnly(p.birth_date));
    setField("mother_name", p.mother_name);
    setField("father_name", p.father_name);
    setField("source", p.source);

    var reliabilityMap = {
      "pending": "Pendente", "low": "Baixo", "medium": "Médio",
      "high": "Alto", "validated": "Validado"
    };
    setField("reliability_level", reliabilityMap[p.reliability_level] || p.reliability_level || "—");

    setField("notes", p.notes);
    setField("created_at_full", formatDateTime(p.created_at));
    setField("created_by", p.created_by);
    setField("updated_at", formatDateTime(p.updated_at));
    setField("updated_by", p.updated_by);

    if (archivedNoteEl) archivedNoteEl.hidden = (p.status !== "archived");

    if (editBtnEl) {
      editBtnEl.onclick = function () {
        window.location.href = "/persons?edit=" + encodeURIComponent(p.id);
      };
    }

    showContent();
  }

  // ---------- Carregar pessoa ----------
  function loadPerson() {
    showLoading();
    fetch(API_PERSONS + "/" + encodeURIComponent(personId), {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 404) { showNotFound(); return null; }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        renderPerson(data);
        loadLinks();
      })
      .catch(function (err) {
        console.error("[person_detail] erro ao carregar pessoa", err);
        showNotFound();
        toast("error", "Erro", "Não foi possível carregar a pessoa.");
      });
  }

  // ================================================================
  // VÍNCULOS — RF-003, Bloco 10.6
  // ================================================================

  function linksShowLoading() {
    if (linksLoadingEl)   linksLoadingEl.hidden   = false;
    if (linksEmptyEl)     linksEmptyEl.hidden      = true;
    if (linksTableWrapEl) linksTableWrapEl.hidden  = true;
  }

  function linksShowEmpty() {
    if (linksLoadingEl)   linksLoadingEl.hidden   = true;
    if (linksEmptyEl)     linksEmptyEl.hidden      = false;
    if (linksTableWrapEl) linksTableWrapEl.hidden  = true;
  }

  function linksShowTable() {
    if (linksLoadingEl)   linksLoadingEl.hidden   = true;
    if (linksEmptyEl)     linksEmptyEl.hidden      = true;
    if (linksTableWrapEl) linksTableWrapEl.hidden  = false;
  }

  function renderLinksTable(links) {
    if (!linksTbodyEl) return;
    if (!links || links.length === 0) { linksShowEmpty(); return; }

    var rows = links.map(function (lk) {
      var roleLabel        = ROLE_LABELS[lk.role_in_case] || lk.role_in_case || "—";
      var reliabilityLabel = RELIABILITY_LABELS[lk.reliability_level] || lk.reliability_level || "—";
      var caseLabel        = lk.case_code
        ? lk.case_code + (lk.case_name ? " — " + lk.case_name : "")
        : ("id " + lk.case_id);
      var source           = lk.source || "—";
      var linkId           = lk.id;

      var tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border, #2C2E38)";
      tr.dataset.linkId = String(linkId);

      tr.innerHTML =
        '<td class="mono" style="padding: var(--space-2) var(--space-3) var(--space-2) 0; font-weight: 500;">' +
          escapeHtml(caseLabel) +
        "</td>" +
        '<td class="mono" style="padding: var(--space-2) var(--space-3);">' +
          escapeHtml(roleLabel) +
        "</td>" +
        '<td class="mono text-secondary" style="padding: var(--space-2) var(--space-3);">' +
          escapeHtml(reliabilityLabel) +
        "</td>" +
        '<td class="text-secondary" style="padding: var(--space-2) var(--space-3); font-size: 0.8rem; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="' + escapeHtml(source) + '">' +
          escapeHtml(source) +
        "</td>" +
        '<td style="padding: var(--space-2) 0 var(--space-2) var(--space-3); white-space: nowrap;">' +
          '<button type="button" class="btn btn--text" style="font-size: 0.8rem; color: var(--text-tertiary);" data-remove-link="' + linkId + '">Remover</button>' +
        "</td>";

      tr.querySelector('[data-remove-link]').addEventListener("click", function () {
        removeLink(linkId, tr);
      });

      return tr;
    });

    linksTbodyEl.innerHTML = "";
    rows.forEach(function (tr) { linksTbodyEl.appendChild(tr); });
    linksShowTable();
  }

  function loadLinks() {
    linksShowLoading();
    fetch(API_LINKS + "?person_id=" + encodeURIComponent(personId), {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        renderLinksTable(data);
      })
      .catch(function (err) {
        console.error("[person_detail] erro ao carregar vínculos", err);
        linksShowEmpty();
        toast("error", "Erro", "Não foi possível carregar os vínculos.");
      });
  }

  function removeLink(linkId, rowEl) {
    if (!confirm("Remover este vínculo? A ação será registrada no log de auditoria.")) return;

    fetch(API_LINKS + "/" + encodeURIComponent(linkId), {
      method: "DELETE",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 404) { toast("error", "Erro", "Vínculo não encontrado."); return null; }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        if (rowEl && rowEl.parentNode) rowEl.parentNode.removeChild(rowEl);
        if (linksTbodyEl && linksTbodyEl.rows.length === 0) linksShowEmpty();
        toast("success", "Vínculo removido", "O vínculo foi removido com sucesso.");
      })
      .catch(function (err) {
        console.error("[person_detail] erro ao remover vínculo", err);
        toast("error", "Erro", "Não foi possível remover o vínculo.");
      });
  }

  // ================================================================
  // MODAL — Vincular a caso (D-B10-01: <select> no MVP-0)
  // ================================================================

  function modalOpen() {
    if (!modalBackdropEl) return;
    if (vcCaseSelect)        vcCaseSelect.value = "";
    if (vcRoleSelect)        vcRoleSelect.value = "";
    if (vcSourceInput)       vcSourceInput.value = "";
    if (vcReliabilitySelect) vcReliabilitySelect.value = "pending";
    if (vcNotesInput)        vcNotesInput.value = "";
    loadCasesIntoSelect();
    modalBackdropEl.setAttribute("data-open", "true");
    requestAnimationFrame(function () { if (vcCaseSelect) vcCaseSelect.focus(); });
  }

  function modalClose() {
    if (!modalBackdropEl) return;
    modalBackdropEl.setAttribute("data-open", "false");
  }

  function loadCasesIntoSelect() {
    if (!vcCaseSelect) return;
    if (vcCaseHint) { vcCaseHint.hidden = false; vcCaseHint.textContent = "Carregando casos…"; }
    vcCaseSelect.innerHTML = '<option value="">— selecione —</option>';

    fetch(API_CASES + "?include_archived=false&sort_by=case_code&descending=false", {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (cases) {
        if (cases === null) return;
        if (vcCaseHint) vcCaseHint.hidden = true;

        if (cases.length === 0) {
          var opt = document.createElement("option");
          opt.value = ""; opt.disabled = true;
          opt.textContent = "Nenhum caso cadastrado";
          vcCaseSelect.appendChild(opt);
          return;
        }

        cases.forEach(function (c) {
          var opt = document.createElement("option");
          opt.value = String(c.id);
          opt.textContent = c.case_code + " — " + c.name;
          vcCaseSelect.appendChild(opt);
        });
      })
      .catch(function (err) {
        console.error("[person_detail] erro ao carregar casos para select", err);
        if (vcCaseHint) { vcCaseHint.hidden = false; vcCaseHint.textContent = "Erro ao carregar casos."; }
      });
  }

  function submitVincular() {
    var caseId      = vcCaseSelect        ? vcCaseSelect.value           : "";
    var roleInCase  = vcRoleSelect        ? vcRoleSelect.value           : "";
    var source      = vcSourceInput       ? vcSourceInput.value.trim()   : "";
    var reliability = vcReliabilitySelect ? vcReliabilitySelect.value    : "pending";
    var notes       = vcNotesInput        ? vcNotesInput.value.trim()    : "";

    if (!caseId)     { toast("error", "Campo obrigatório", "Selecione um caso."); return; }
    if (!roleInCase) { toast("error", "Campo obrigatório", "Selecione o tipo de participação."); return; }
    if (!source)     { toast("error", "Campo obrigatório", "Informe a fonte da informação."); return; }

    if (modalConfirmarEl) modalConfirmarEl.disabled = true;

    var body = {
      case_id:           parseInt(caseId, 10),
      person_id:         personId,
      role_in_case:      roleInCase,
      source:            source,
      reliability_level: reliability,
      notes:             notes || null
    };

    fetch(API_LINKS, {
      method: "POST",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 409) {
          return response.json().then(function (err) {
            var msg = (err && err.detail && err.detail.message)
              ? err.detail.message
              : "Já existe um vínculo ativo com este papel para esta pessoa neste caso.";
            toast("error", "Vínculo duplicado", msg);
            return null;
          });
        }
        if (response.status === 404) { toast("error", "Erro", "Caso ou pessoa não encontrados."); return null; }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        modalClose();
        toast("success", "Vínculo criado", "Pessoa vinculada ao caso com sucesso.");
        loadLinks();
      })
      .catch(function (err) {
        console.error("[person_detail] erro ao criar vínculo", err);
        toast("error", "Erro", "Não foi possível criar o vínculo.");
      })
      .finally(function () {
        if (modalConfirmarEl) modalConfirmarEl.disabled = false;
      });
  }

  // ---------- Extrai id numérico da URL /persons/{id} ----------
  function parsePersonIdFromPath() {
    var m = window.location.pathname.match(/\/persons\/(\d+)\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  // ---------- Inicialização ----------
  function setup() {
    contentEl = document.getElementById("person-detail-content");
    loadingEl = document.getElementById("person-detail-loading");
    if (!contentEl || !loadingEl) return;

    notFoundEl     = document.getElementById("person-detail-notfound");
    archivedNoteEl = document.getElementById("person-detail-archived-note");
    editBtnEl      = document.getElementById("person-detail-edit");

    // Refs de vínculos
    linksLoadingEl   = document.getElementById("person-links-loading");
    linksEmptyEl     = document.getElementById("person-links-empty");
    linksTableWrapEl = document.getElementById("person-links-table-wrap");
    linksTbodyEl     = document.getElementById("person-links-tbody");
    btnVincularEl    = document.getElementById("btn-vincular-caso");

    // Refs do modal
    modalBackdropEl     = document.getElementById("modal-vincular-caso-backdrop");
    modalCloseEl        = document.getElementById("modal-vincular-caso-close");
    modalCancelEl       = document.getElementById("modal-vincular-caso-cancel");
    modalConfirmarEl    = document.getElementById("modal-vincular-caso-confirmar");
    vcCaseSelect        = document.getElementById("vc-case-select");
    vcCaseHint          = document.getElementById("vc-case-hint");
    vcRoleSelect        = document.getElementById("vc-role-select");
    vcSourceInput       = document.getElementById("vc-source-input");
    vcReliabilitySelect = document.getElementById("vc-reliability-select");
    vcNotesInput        = document.getElementById("vc-notes-input");

    personId = parsePersonIdFromPath();
    if (personId === null || isNaN(personId)) { showNotFound(); return; }

    // Esc: fecha modal se aberto; senão volta para lista
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (modalBackdropEl && modalBackdropEl.getAttribute("data-open") === "true") {
          modalClose();
        } else {
          e.preventDefault();
          window.location.href = "/persons";
        }
      }
    });

    if (btnVincularEl)   btnVincularEl.addEventListener("click", modalOpen);
    if (modalCloseEl)    modalCloseEl.addEventListener("click", modalClose);
    if (modalCancelEl)   modalCancelEl.addEventListener("click", modalClose);
    if (modalBackdropEl) {
      modalBackdropEl.addEventListener("click", function (e) {
        if (e.target === modalBackdropEl) modalClose();
      });
    }
    if (modalConfirmarEl) modalConfirmarEl.addEventListener("click", submitVincular);

    loadPerson();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
