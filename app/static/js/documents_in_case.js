/* documents_in_case.js — RF-007, Sprint 01-B sub-passo 02-5 */
(function () {
  "use strict";

  var API_BASE = "/api/documents";

  var caseId = null;
  var sectionEl, loadingEl, emptyEl, tableEl, tbodyEl, importBtnEl;
  var backdropEl, cancelBtnEl, confirmarBtnEl;
  var fileInputEl, titleInputEl, notesInputEl;
  var dupWarningEl, dupMsgEl, forceDupCbEl;

  // ---------------------------------------------------------------------------
  // Utilitários
  // ---------------------------------------------------------------------------

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

  function formatBytes(bytes) {
    if (bytes === null || bytes === undefined) return "--";
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + " MB";
    if (bytes >= 1024)    return (bytes / 1024).toFixed(0) + " KB";
    return bytes + " B";
  }

  function formatDate(iso) {
    if (!iso) return "--";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear() +
           " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  // ---------------------------------------------------------------------------
  // Renderização
  // ---------------------------------------------------------------------------

  function verifyDoc(docId, cell) {
    cell.textContent = "…";
    fetch(API_BASE + "/detail/" + docId + "/verify", { credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; return r.json(); })
      .then(function (data) {
        if (data === null) return;
        if (data.ok) {
          cell.innerHTML = '<span style="color:var(--color-success,green)">✓ OK</span>';
        } else if (data.error === "file_missing") {
          cell.innerHTML = '<span style="color:var(--accent)">✗ AUSENTE</span>';
        } else if (data.error === "hash_mismatch") {
          cell.innerHTML = '<span style="color:var(--accent)">✗ ADULTERADO</span>';
        } else if (data.error === "not_found") {
          cell.innerHTML = '<span class="text-tertiary">—</span>';
        } else {
          cell.innerHTML = '<span class="text-tertiary">—</span>';
        }
      })
      .catch(function () { cell.textContent = "Erro"; });
  }

  function renderRows(docs) {
    if (!tbodyEl) return;
    if (!docs || docs.length === 0) {
      if (emptyEl) emptyEl.hidden = false;
      if (tableEl) tableEl.hidden = true;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;
    if (tableEl) tableEl.hidden = false;

    tbodyEl.innerHTML = "";
    docs.forEach(function (doc) {
      var tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-subtle)";
      tr.style.fontSize = "var(--text-sm)";

      var nomeHtml = doc.title
        ? '<strong>' + escapeHtml(doc.title) + '</strong><br><span class="text-tertiary mono" style="font-size:0.75rem;">' + escapeHtml(doc.original_filename) + '</span>'
        : escapeHtml(doc.original_filename);

      var badgeHtml = '<span class="badge badge--mono">' + escapeHtml((doc.file_format || "").toUpperCase()) + '</span>';

      var tdNome      = '<td style="padding:var(--space-2) var(--space-3);">' + nomeHtml + '</td>';
      var tdFormato   = '<td style="padding:var(--space-2) var(--space-3);">' + badgeHtml + '</td>';
      var tdTamanho   = '<td style="padding:var(--space-2) var(--space-3);" class="mono text-secondary">' + escapeHtml(formatBytes(doc.file_size)) + '</td>';
      var tdData      = '<td style="padding:var(--space-2) var(--space-3);" class="mono text-secondary">' + escapeHtml(formatDate(doc.imported_at)) + '</td>';
      var tdInteg     = '<td style="padding:var(--space-2) var(--space-3);" class="mono" data-integ="' + doc.id + '"><button type="button" class="btn btn--text" style="font-size:var(--text-sm);">VERIFICAR</button></td>';
      var tdAcoes     = '<td style="padding:var(--space-2) 0 var(--space-2) var(--space-3);"><!-- TODO: editar metadados (doc.id=' + doc.id + ') --></td>';

      tr.innerHTML = tdNome + tdFormato + tdTamanho + tdData + tdInteg + tdAcoes;

      var integCell = tr.querySelector('[data-integ="' + doc.id + '"]');
      if (integCell) {
        integCell.querySelector("button").addEventListener("click", function () {
          verifyDoc(doc.id, integCell);
        });
      }

      tbodyEl.appendChild(tr);
    });
  }

  // ---------------------------------------------------------------------------
  // Carga
  // ---------------------------------------------------------------------------

  function loadDocuments() {
    if (loadingEl) loadingEl.hidden = false;
    if (emptyEl)   emptyEl.hidden   = true;
    if (tableEl)   tableEl.hidden   = true;

    fetch(API_BASE + "/" + caseId, { credentials: "same-origin" })
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
        toast("Erro ao carregar documentos.", "error");
      });
  }

  // ---------------------------------------------------------------------------
  // Modal de importação
  // ---------------------------------------------------------------------------

  function openImportModal() {
    if (fileInputEl)   fileInputEl.value   = "";
    if (titleInputEl)  titleInputEl.value  = "";
    if (notesInputEl)  notesInputEl.value  = "";
    if (forceDupCbEl)  forceDupCbEl.checked = false;
    if (dupWarningEl)  dupWarningEl.hidden  = true;
    if (backdropEl)    backdropEl.dataset.open = "true";
  }

  function closeImportModal() {
    if (backdropEl) backdropEl.dataset.open = "false";
  }

  function submitImport() {
    if (!fileInputEl || !fileInputEl.files || fileInputEl.files.length === 0) {
      toast("Selecione um arquivo.", "warning");
      return;
    }

    var fd = new FormData();
    fd.append("file", fileInputEl.files[0]);
    if (titleInputEl && titleInputEl.value.trim()) fd.append("title", titleInputEl.value.trim());
    if (notesInputEl && notesInputEl.value.trim()) fd.append("notes", notesInputEl.value.trim());
    fd.append("force_duplicate", forceDupCbEl && forceDupCbEl.checked ? "true" : "false");

    if (confirmarBtnEl) confirmarBtnEl.disabled = true;

    fetch(API_BASE + "/" + caseId + "/import", {
      method: "POST",
      credentials: "same-origin",
      body: fd
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        return r.json().then(function (json) {
          return { status: r.status, ok: r.ok, json: json };
        });
      })
      .then(function (res) {
        if (res === null) return;
        if (res.status === 409) {
          var detail = res.json && res.json.detail ? res.json.detail : {};
          if (dupWarningEl) dupWarningEl.hidden = false;
          if (dupMsgEl) dupMsgEl.textContent = "Já existe: " + (detail.existing_document_name || "—");
          return;
        }
        if (!res.ok) {
          var msg = (res.json && res.json.detail) ? String(res.json.detail) : String(res.status);
          toast("Erro ao importar: " + msg, "error");
          return;
        }
        closeImportModal();
        toast("Documento importado.", "success");
        loadDocuments();
      })
      .catch(function () {
        toast("Erro ao importar documento.", "error");
      })
      .finally(function () {
        if (confirmarBtnEl) confirmarBtnEl.disabled = false;
      });
  }

  // ---------------------------------------------------------------------------
  // Setup
  // ---------------------------------------------------------------------------

  function setup() {
    sectionEl = document.getElementById("documents-section");
    if (!sectionEl) return;

    var parts = window.location.pathname.split("/").filter(Boolean);
    var rawId = parts[parts.length - 1];
    caseId = parseInt(rawId, 10);
    if (isNaN(caseId)) return;

    loadingEl     = document.getElementById("doc-loading");
    emptyEl       = document.getElementById("doc-empty");
    tableEl       = document.getElementById("doc-table");
    tbodyEl       = document.getElementById("doc-tbody");
    importBtnEl   = document.getElementById("doc-import-btn");
    backdropEl    = document.getElementById("modal-doc-import-backdrop");
    cancelBtnEl   = document.getElementById("modal-doc-cancel");
    confirmarBtnEl = document.getElementById("modal-doc-confirmar");
    fileInputEl   = document.getElementById("doc-file-input");
    titleInputEl  = document.getElementById("doc-title-input");
    notesInputEl  = document.getElementById("doc-notes-input");
    dupWarningEl  = document.getElementById("doc-duplicate-warning");
    dupMsgEl      = document.getElementById("doc-duplicate-msg");
    forceDupCbEl  = document.getElementById("doc-force-duplicate");

    if (importBtnEl)   importBtnEl.addEventListener("click", openImportModal);
    if (cancelBtnEl)   cancelBtnEl.addEventListener("click", closeImportModal);
    if (confirmarBtnEl) confirmarBtnEl.addEventListener("click", submitImport);
    if (backdropEl) {
      backdropEl.addEventListener("click", function (e) {
        if (e.target === backdropEl) closeImportModal();
      });
    }

    loadDocuments();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
