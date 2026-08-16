/* incident_reports_in_case.js — RF-009, Sprint 03-4 */
/* CA-009.4: vinculo documento-BO adicionado (Sprint 04, sub-passo 04-6) */
(function () {
  "use strict";

  var API_IR       = "/api/incident_reports";
  var API_CASES_IR = "/api/cases";
  var API_DOCS     = "/api/documents";
  var caseId = null;

  /* Cache de documentos do caso (carregado uma vez, usado no select de vincular) */
  var caseDocuments = [];

  /* Elementos de layout */
  var sectionEl, loadingEl, emptyEl, tableEl, tbodyEl, addBtnEl;

  /* Modal de cadastro */
  var backdropEl, cancelBtnEl, confirmarBtnEl;
  var boNumberEl, boDateEl, issuingUnitEl, criminalTypeEl, proceduralStatusEl, summaryEl, notesEl;

  /* -------------------------------------------------------------------------
   * Boot
   * ---------------------------------------------------------------------- */

  function init() {
    var match = window.location.pathname.match(/\/cases\/(\d+)/);
    if (!match) return;
    caseId = match[1];

    sectionEl      = document.getElementById("ir-section");
    loadingEl      = document.getElementById("ir-loading");
    emptyEl        = document.getElementById("ir-empty");
    tableEl        = document.getElementById("ir-table");
    tbodyEl        = document.getElementById("ir-tbody");
    addBtnEl       = document.getElementById("ir-add-btn");
    backdropEl     = document.getElementById("modal-ir-backdrop");
    cancelBtnEl    = document.getElementById("modal-ir-cancel");
    confirmarBtnEl = document.getElementById("modal-ir-confirmar");
    boNumberEl          = document.getElementById("ir-bo-number");
    boDateEl            = document.getElementById("ir-bo-date");
    issuingUnitEl       = document.getElementById("ir-issuing-unit");
    criminalTypeEl      = document.getElementById("ir-criminal-type");
    proceduralStatusEl  = document.getElementById("ir-procedural-status");
    summaryEl           = document.getElementById("ir-summary");
    notesEl             = document.getElementById("ir-notes");

    if (addBtnEl)       addBtnEl.addEventListener("click", openModal);
    if (cancelBtnEl)    cancelBtnEl.addEventListener("click", closeModal);
    if (confirmarBtnEl) confirmarBtnEl.addEventListener("click", submitCadastro);
    if (backdropEl) {
      backdropEl.addEventListener("click", function (e) {
        if (e.target === backdropEl) closeModal();
      });
    }

    /* Carrega documentos e BOs em paralelo */
    loadDocuments();
    loadReports();
  }

  /* -------------------------------------------------------------------------
   * Documentos do caso — cache para o select de vínculo
   * ---------------------------------------------------------------------- */

  function loadDocuments() {
    fetch(API_DOCS + "/" + caseId, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (docs) {
        caseDocuments = Array.isArray(docs) ? docs : [];
      })
      .catch(function () { caseDocuments = []; });
  }

  /* -------------------------------------------------------------------------
   * Listagem de BOs
   * ---------------------------------------------------------------------- */

  function loadReports() {
    if (loadingEl) loadingEl.hidden = false;
    if (emptyEl)   emptyEl.hidden   = true;
    if (tableEl)   tableEl.hidden   = true;

    fetch(API_CASES_IR + "/" + caseId + "/incident_reports", { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (loadingEl) loadingEl.hidden = true;
        renderRows(data);
      })
      .catch(function () {
        if (loadingEl) loadingEl.hidden = true;
        if (emptyEl) {
          emptyEl.hidden      = false;
          emptyEl.textContent = "Erro ao carregar BOs.";
        }
      });
  }

  /* -------------------------------------------------------------------------
   * Renderização das linhas
   * ---------------------------------------------------------------------- */

  function renderRows(reports) {
    if (!tbodyEl) return;
    tbodyEl.innerHTML = "";

    if (!reports || reports.length === 0) {
      if (emptyEl) emptyEl.hidden = false;
      if (tableEl) tableEl.hidden = true;
      return;
    }

    if (emptyEl) emptyEl.hidden = true;
    if (tableEl) tableEl.hidden = false;

    reports.forEach(function (ir) {
      var tr = document.createElement("tr");
      tr.style.cssText = "border-bottom: 1px solid var(--border-subtle); font-size: var(--text-sm);";

      /* Numero BO */
      var tdNum = document.createElement("td");
      tdNum.style.cssText = "padding: var(--space-2) var(--space-3) var(--space-2) 0;";
      tdNum.className = "mono";
      tdNum.textContent = ir.bo_number || "-";
      tr.appendChild(tdNum);

      /* Data */
      var tdData = document.createElement("td");
      tdData.style.cssText = "padding: var(--space-2) var(--space-3);";
      tdData.className = "mono text-secondary";
      tdData.textContent = ir.date ? ir.date.slice(0, 10) : "-";
      tr.appendChild(tdData);

      /* Unidade */
      var tdUnit = document.createElement("td");
      tdUnit.style.cssText = "padding: var(--space-2) var(--space-3);";
      tdUnit.className = "mono text-secondary";
      tdUnit.textContent = ir.issuing_unit || "-";
      tr.appendChild(tdUnit);

      /* Tipificacao */
      var tdTipo = document.createElement("td");
      tdTipo.style.cssText = "padding: var(--space-2) var(--space-3);";
      tdTipo.className = "mono text-secondary";
      tdTipo.textContent = ir.criminal_type || "-";
      tr.appendChild(tdTipo);

      /* Resumo */
      var tdRes = document.createElement("td");
      tdRes.style.cssText = "padding: var(--space-2) var(--space-3); max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;";
      tdRes.className = "text-secondary";
      tdRes.title = ir.summary || "";
      tdRes.textContent = ir.summary || "-";
      tr.appendChild(tdRes);

      /* Documento (CA-009.4) */
      var tdDoc = document.createElement("td");
      tdDoc.style.cssText = "padding: var(--space-2) var(--space-3);";
      tdDoc.id = "ir-doc-cell-" + ir.id;
      renderDocCell(tdDoc, ir);
      tr.appendChild(tdDoc);

      /* Acoes */
      var tdAcoes = document.createElement("td");
      tdAcoes.style.cssText = "padding: var(--space-2) 0 var(--space-2) var(--space-3); white-space: nowrap;";
      var btnArq = document.createElement("button");
      btnArq.type      = "button";
      btnArq.className = "btn btn--text";
      btnArq.style.fontSize = "var(--text-sm)";
      btnArq.textContent = "[arquivar]";
      (function (irId, rowEl) {
        btnArq.addEventListener("click", function () { archiveBO(irId, rowEl); });
      }(ir.id, tr));
      tdAcoes.appendChild(btnArq);
      tr.appendChild(tdAcoes);

      tbodyEl.appendChild(tr);
    });
  }

  /* -------------------------------------------------------------------------
   * Célula de documento — estado vinculado ou botão vincular
   * ---------------------------------------------------------------------- */

  function renderDocCell(tdDoc, ir) {
    tdDoc.innerHTML = "";

    if (ir.document_id) {
      /* Documento vinculado: mostra nome + botão desvincular */
      var doc = findDocById(ir.document_id);

      var nameSpan = document.createElement("span");
      nameSpan.className  = "mono text-secondary";
      nameSpan.style.cssText = "font-size: var(--text-sm); max-width: 160px; display: inline-block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle;";
      nameSpan.title       = doc ? doc.original_filename : ("documento #" + ir.document_id);
      nameSpan.textContent = doc ? truncateFilename(doc.original_filename, 22) : ("#" + ir.document_id);

      var btnDesv = document.createElement("button");
      btnDesv.type      = "button";
      btnDesv.className = "btn btn--text";
      btnDesv.style.cssText = "font-size: var(--text-sm); margin-left: var(--space-2); color: var(--text-tertiary);";
      btnDesv.title     = "Desvincular documento";
      btnDesv.textContent = "[×]";
      (function (irId, cell, irObj) {
        btnDesv.addEventListener("click", function () { unlinkDoc(irId, cell, irObj); });
      }(ir.id, tdDoc, ir));

      tdDoc.appendChild(nameSpan);
      tdDoc.appendChild(btnDesv);
    } else {
      /* Sem documento vinculado: botão vincular */
      var btnVinc = document.createElement("button");
      btnVinc.type      = "button";
      btnVinc.className = "btn btn--text";
      btnVinc.style.cssText = "font-size: var(--text-sm); color: var(--text-tertiary);";
      btnVinc.textContent = "[vincular doc]";
      (function (irId, cell, irObj) {
        btnVinc.addEventListener("click", function () { showLinkSelect(irId, cell, irObj); });
      }(ir.id, tdDoc, ir));
      tdDoc.appendChild(btnVinc);
    }
  }

  function findDocById(docId) {
    for (var i = 0; i < caseDocuments.length; i++) {
      if (caseDocuments[i].id === docId) return caseDocuments[i];
    }
    return null;
  }

  function truncateFilename(name, maxLen) {
    if (!name) return "-";
    if (name.length <= maxLen) return name;
    var dot = name.lastIndexOf(".");
    if (dot > 0) return name.slice(0, maxLen - 4) + "…" + name.slice(dot);
    return name.slice(0, maxLen) + "…";
  }

  /* -------------------------------------------------------------------------
   * Select inline para escolher o documento a vincular
   * ---------------------------------------------------------------------- */

  function showLinkSelect(irId, tdDoc, irObj) {
    tdDoc.innerHTML = "";

    /* Sem documentos no caso */
    if (caseDocuments.length === 0) {
      var msg = document.createElement("span");
      msg.className    = "mono text-tertiary";
      msg.style.fontSize = "var(--text-sm)";
      msg.textContent  = "sem docs no caso";

      var btnCx = document.createElement("button");
      btnCx.type      = "button";
      btnCx.className = "btn btn--text";
      btnCx.style.cssText = "font-size: var(--text-sm); margin-left: var(--space-2);";
      btnCx.textContent = "[×]";
      btnCx.addEventListener("click", function () { renderDocCell(tdDoc, irObj); });

      tdDoc.appendChild(msg);
      tdDoc.appendChild(btnCx);
      return;
    }

    var sel = document.createElement("select");
    sel.className  = "input mono";
    sel.style.cssText = "font-size: var(--text-sm); padding: 2px 4px; height: auto; max-width: 180px;";

    var optDef = document.createElement("option");
    optDef.value       = "";
    optDef.textContent = "-- selecione --";
    sel.appendChild(optDef);

    caseDocuments.forEach(function (doc) {
      var opt = document.createElement("option");
      opt.value       = String(doc.id);
      opt.textContent = truncateFilename(doc.original_filename, 28);
      opt.title       = doc.original_filename;
      sel.appendChild(opt);
    });

    var btnOk = document.createElement("button");
    btnOk.type      = "button";
    btnOk.className = "btn btn--primary";
    btnOk.style.cssText = "font-size: var(--text-sm); padding: 2px 10px; margin-left: var(--space-2);";
    btnOk.textContent = "OK";

    var btnCancel = document.createElement("button");
    btnCancel.type      = "button";
    btnCancel.className = "btn btn--text";
    btnCancel.style.cssText = "font-size: var(--text-sm); margin-left: 4px;";
    btnCancel.textContent = "[×]";

    btnOk.addEventListener("click", function () {
      if (!sel.value) {
        window.CIRCE.toast.warning("Selecione um documento.", "");
        return;
      }
      linkDoc(irId, parseInt(sel.value, 10), tdDoc, irObj);
    });

    btnCancel.addEventListener("click", function () {
      renderDocCell(tdDoc, irObj);
    });

    tdDoc.appendChild(sel);
    tdDoc.appendChild(btnOk);
    tdDoc.appendChild(btnCancel);
    sel.focus();
  }

  /* -------------------------------------------------------------------------
   * PATCH — vincular / desvincular
   * ---------------------------------------------------------------------- */

  function linkDoc(irId, docId, tdDoc, irObj) {
    fetch(API_IR + "/" + irId, {
      method:      "PATCH",
      credentials: "same-origin",
      headers:     { "Content-Type": "application/json" },
      body:        JSON.stringify({ document_id: docId }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (updated) {
        irObj.document_id = updated.document_id;
        renderDocCell(tdDoc, irObj);
        window.CIRCE.toast.success("Documento vinculado.", "");
      })
      .catch(function () {
        window.CIRCE.toast.error("Erro ao vincular documento.", "");
        renderDocCell(tdDoc, irObj);
      });
  }

  function unlinkDoc(irId, tdDoc, irObj) {
    fetch(API_IR + "/" + irId, {
      method:      "PATCH",
      credentials: "same-origin",
      headers:     { "Content-Type": "application/json" },
      body:        JSON.stringify({ document_id: null }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function () {
        irObj.document_id = null;
        renderDocCell(tdDoc, irObj);
        window.CIRCE.toast.success("Documento desvinculado.", "");
      })
      .catch(function () {
        window.CIRCE.toast.error("Erro ao desvincular documento.", "");
      });
  }

  /* -------------------------------------------------------------------------
   * Arquivar BO
   * ---------------------------------------------------------------------- */

  function archiveBO(irId, rowEl) {
    fetch(API_IR + "/" + irId, { method: "DELETE", credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 204) {
          rowEl.remove();
          var remaining = tbodyEl ? tbodyEl.querySelectorAll("tr").length : 0;
          if (remaining === 0) {
            if (tableEl) tableEl.hidden = true;
            if (emptyEl) emptyEl.hidden = false;
          }
          window.CIRCE.toast.success("BO arquivado.", "");
        } else {
          throw new Error("HTTP " + r.status);
        }
      })
      .catch(function () {
        window.CIRCE.toast.error("Erro ao arquivar BO.", "");
      });
  }

  /* -------------------------------------------------------------------------
   * Modal de cadastro de BO
   * ---------------------------------------------------------------------- */

  function openModal() {
    if (backdropEl) backdropEl.dataset.open = "true";
    if (boNumberEl) boNumberEl.focus();
  }

  function closeModal() {
    if (backdropEl) backdropEl.dataset.open = "false";
    resetForm();
  }

  function resetForm() {
    if (boNumberEl)         boNumberEl.value         = "";
    if (boDateEl)           boDateEl.value           = "";
    if (issuingUnitEl)      issuingUnitEl.value      = "";
    if (criminalTypeEl)     criminalTypeEl.value     = "";
    if (proceduralStatusEl) proceduralStatusEl.value = "";
    if (summaryEl)          summaryEl.value          = "";
    if (notesEl)            notesEl.value            = "";
  }

  function submitCadastro() {
    var boNumber = boNumberEl ? boNumberEl.value.trim() : "";
    if (!boNumber) {
      window.CIRCE.toast.warning("Numero do BO e obrigatorio.", "");
      if (boNumberEl) boNumberEl.focus();
      return;
    }

    var payload = {
      bo_number: boNumber,
      case_id:   parseInt(caseId, 10),
    };
    if (boDateEl            && boDateEl.value)            payload.bo_date           = boDateEl.value;
    if (issuingUnitEl       && issuingUnitEl.value)       payload.issuing_unit      = issuingUnitEl.value.trim();
    if (criminalTypeEl      && criminalTypeEl.value)      payload.criminal_type     = criminalTypeEl.value.trim();
    if (proceduralStatusEl  && proceduralStatusEl.value)  payload.procedural_status = proceduralStatusEl.value.trim();
    if (summaryEl           && summaryEl.value)           payload.summary           = summaryEl.value.trim();
    if (notesEl             && notesEl.value)             payload.notes             = notesEl.value.trim();

    if (confirmarBtnEl) {
      confirmarBtnEl.disabled    = true;
      confirmarBtnEl.textContent = "Cadastrando...";
    }

    fetch(API_IR, {
      method:      "POST",
      credentials: "same-origin",
      headers:     { "Content-Type": "application/json" },
      body:        JSON.stringify(payload),
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (e) { throw e; });
        return r.json();
      })
      .then(function () {
        closeModal();
        loadReports();
        window.CIRCE.toast.success("BO cadastrado com sucesso.", "");
      })
      .catch(function (err) {
        var msg = (err && err.detail) ? err.detail : "Erro ao cadastrar BO.";
        window.CIRCE.toast.error(msg, "");
      })
      .finally(function () {
        if (confirmarBtnEl) {
          confirmarBtnEl.disabled    = false;
          confirmarBtnEl.textContent = "Cadastrar";
        }
      });
  }

  /* -------------------------------------------------------------------------
   * Inicializacao
   * ---------------------------------------------------------------------- */

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
}());
