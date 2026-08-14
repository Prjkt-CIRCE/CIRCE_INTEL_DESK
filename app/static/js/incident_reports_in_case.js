/* incident_reports_in_case.js - RF-009, Sprint 03 sub-passo 03-4 */
/* Lista BOs vinculados ao caso, cadastro via modal, arquivamento. */
(function () {
  "use strict";

  var API_IR   = "/api/incident_reports";
  var API_CASES_IR = "/api/cases";

  var caseId = null;
  var sectionEl, loadingEl, emptyEl, tableEl, tbodyEl, addBtnEl;
  var backdropEl, cancelBtnEl, confirmarBtnEl;
  var boNumberInputEl, boDateInputEl, issuingUnitInputEl;
  var summaryInputEl, criminalTypeInputEl, proceduralStatusInputEl, notesInputEl;

  var ROLE_LABELS = {
    vitima:      "Vitima",
    autor:       "Autor",
    comunicante: "Comunicante",
    testemunha:  "Testemunha",
    outro:       "Outro"
  };

  function handleAuthLapse(r) {
    if (r.status === 401 || r.redirected) {
      window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
      return true;
    }
    return false;
  }

  function toast(msg, tipo) {
    if (window.CIRCE && window.CIRCE.toast) {
      if (tipo === "success") window.CIRCE.toast.success(msg, "");
      else if (tipo === "error") window.CIRCE.toast.error(msg, "");
      else if (tipo === "warning") window.CIRCE.toast.warning(msg, "");
      else window.CIRCE.toast.info(msg, "");
    }
  }

  function escapeHtml(s) {
    if (!s) return "";
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function formatDate(iso) {
    if (!iso) return "--";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear();
  }

  function archiveBO(irId, rowEl) {
    if (!confirm("Arquivar este BO? A acao e irreversivel pela UI.")) return;

    fetch(API_IR + "/" + irId, {
      method: "DELETE",
      credentials: "same-origin"
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (r.status === 204) {
          rowEl.remove();
          // Verifica se tbody ficou vazio
          if (tbodyEl && tbodyEl.children.length === 0) {
            if (tableEl) tableEl.hidden = true;
            if (emptyEl) emptyEl.hidden = false;
          }
          toast("BO arquivado.", "success");
          return null;
        }
        throw new Error("HTTP " + r.status);
      })
      .catch(function () {
        toast("Erro ao arquivar BO.", "error");
      });
  }

  function renderRows(reports) {
    if (!tbodyEl) return;
    if (!reports || reports.length === 0) {
      if (emptyEl) emptyEl.hidden = false;
      if (tableEl) tableEl.hidden = true;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;
    if (tableEl) tableEl.hidden = false;

    tbodyEl.innerHTML = "";
    reports.forEach(function (ir) {
      var tr = document.createElement("tr");
      tr.dataset.irId = ir.id;
      tr.style.cssText = "border-bottom: 1px solid var(--border-subtle); font-size: var(--text-sm);";

      var summaryText = ir.summary
        ? (ir.summary.length > 60 ? ir.summary.substring(0, 60) + "..." : ir.summary)
        : "--";

      tr.innerHTML =
        '<td style="padding: var(--space-2) var(--space-3) var(--space-2) 0;" class="mono">' +
          escapeHtml(ir.bo_number) +
        '</td>' +
        '<td style="padding: var(--space-2) var(--space-3);" class="mono text-secondary">' +
          escapeHtml(formatDate(ir.bo_date)) +
        '</td>' +
        '<td style="padding: var(--space-2) var(--space-3);" class="text-secondary">' +
          escapeHtml(ir.issuing_unit || "--") +
        '</td>' +
        '<td style="padding: var(--space-2) var(--space-3);" class="text-secondary">' +
          escapeHtml(ir.criminal_type || "--") +
        '</td>' +
        '<td style="padding: var(--space-2) var(--space-3);" class="text-secondary">' +
          escapeHtml(summaryText) +
        '</td>' +
        '<td style="padding: var(--space-2) 0 var(--space-2) var(--space-3);">' +
          '<button type="button" class="btn btn--text ir-archive-btn" ' +
          'style="font-size: var(--text-sm); color: var(--text-tertiary);" ' +
          'data-ir-id="' + ir.id + '">Arquivar</button>' +
        '</td>';

      var archiveBtn = tr.querySelector(".ir-archive-btn");
      if (archiveBtn) {
        archiveBtn.addEventListener("click", function () {
          archiveBO(ir.id, tr);
        });
      }

      tbodyEl.appendChild(tr);
    });
  }

  function loadReports() {
    if (loadingEl) loadingEl.hidden = false;
    if (emptyEl)   emptyEl.hidden   = true;
    if (tableEl)   tableEl.hidden   = true;

    fetch(API_CASES_IR + "/" + caseId + "/incident_reports", {
      credentials: "same-origin"
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (loadingEl) loadingEl.hidden = true;
        if (data === null) return;
        renderRows(data);
      })
      .catch(function () {
        if (loadingEl) loadingEl.hidden = true;
        toast("Erro ao carregar BOs.", "error");
      });
  }

  function openModal() {
    if (boNumberInputEl)        boNumberInputEl.value        = "";
    if (boDateInputEl)          boDateInputEl.value          = "";
    if (issuingUnitInputEl)     issuingUnitInputEl.value     = "";
    if (summaryInputEl)         summaryInputEl.value         = "";
    if (criminalTypeInputEl)    criminalTypeInputEl.value    = "";
    if (proceduralStatusInputEl) proceduralStatusInputEl.value = "";
    if (notesInputEl)           notesInputEl.value           = "";
    if (backdropEl) backdropEl.dataset.open = "true";
    if (boNumberInputEl) boNumberInputEl.focus();
  }

  function closeModal() {
    if (backdropEl) backdropEl.dataset.open = "false";
  }

  function submitCadastro() {
    var boNumber = boNumberInputEl ? boNumberInputEl.value.trim() : "";
    if (!boNumber) {
      toast("Numero do BO e obrigatorio.", "warning");
      if (boNumberInputEl) boNumberInputEl.focus();
      return;
    }

    var payload = {
      bo_number: boNumber,
      case_id:   caseId
    };

    if (boDateInputEl && boDateInputEl.value)              payload.bo_date           = boDateInputEl.value;
    if (issuingUnitInputEl && issuingUnitInputEl.value.trim()) payload.issuing_unit  = issuingUnitInputEl.value.trim();
    if (summaryInputEl && summaryInputEl.value.trim())     payload.summary           = summaryInputEl.value.trim();
    if (criminalTypeInputEl && criminalTypeInputEl.value.trim()) payload.criminal_type = criminalTypeInputEl.value.trim();
    if (proceduralStatusInputEl && proceduralStatusInputEl.value.trim()) payload.procedural_status = proceduralStatusInputEl.value.trim();
    if (notesInputEl && notesInputEl.value.trim())         payload.notes             = notesInputEl.value.trim();

    if (confirmarBtnEl) confirmarBtnEl.disabled = true;

    fetch(API_IR, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) {
          return r.json().then(function (json) {
            var msg = json && json.detail ? String(json.detail) : String(r.status);
            throw new Error(msg);
          });
        }
        return r.json();
      })
      .then(function (data) {
        if (data === null) return;
        closeModal();
        toast("BO cadastrado.", "success");
        loadReports();
      })
      .catch(function (err) {
        toast("Erro ao cadastrar BO: " + err.message, "error");
      })
      .finally(function () {
        if (confirmarBtnEl) confirmarBtnEl.disabled = false;
      });
  }

  function setup() {
    sectionEl = document.getElementById("ir-section");
    if (!sectionEl) return;

    var parts = window.location.pathname.split("/").filter(Boolean);
    var rawId = parts[parts.length - 1];
    caseId = parseInt(rawId, 10);
    if (isNaN(caseId)) return;

    loadingEl      = document.getElementById("ir-loading");
    emptyEl        = document.getElementById("ir-empty");
    tableEl        = document.getElementById("ir-table");
    tbodyEl        = document.getElementById("ir-tbody");
    addBtnEl       = document.getElementById("ir-add-btn");
    backdropEl     = document.getElementById("modal-ir-backdrop");
    cancelBtnEl    = document.getElementById("modal-ir-cancel");
    confirmarBtnEl = document.getElementById("modal-ir-confirmar");

    boNumberInputEl         = document.getElementById("ir-bo-number");
    boDateInputEl           = document.getElementById("ir-bo-date");
    issuingUnitInputEl      = document.getElementById("ir-issuing-unit");
    summaryInputEl          = document.getElementById("ir-summary");
    criminalTypeInputEl     = document.getElementById("ir-criminal-type");
    proceduralStatusInputEl = document.getElementById("ir-procedural-status");
    notesInputEl            = document.getElementById("ir-notes");

    if (addBtnEl)       addBtnEl.addEventListener("click", openModal);
    if (cancelBtnEl)    cancelBtnEl.addEventListener("click", closeModal);
    if (confirmarBtnEl) confirmarBtnEl.addEventListener("click", submitCadastro);
    if (backdropEl) {
      backdropEl.addEventListener("click", function (e) {
        if (e.target === backdropEl) closeModal();
      });
    }

    loadReports();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
