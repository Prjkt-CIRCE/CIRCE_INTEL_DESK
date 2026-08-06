/* ============================================================
   CIRCE Intel Desk - case_detail.js
   RF-001 (detalhe do caso) - Sprint 01, Bloco 8.6.
   RF-003 (vinculos pessoa-caso) - Sprint 01, Bloco 10.5.
   AT-03.6: toggle de compartilhamento na Platea (platea_status).
   AT-03.7: toggle [NAO COMPARTILHAR] por item (person_link / document).
   Fix: label do botao Excluir/Liberar atualizado dentro do .then().
   ============================================================ */

(function () {
  "use strict";

  var API_CASES   = "/api/cases";
  var API_LINKS   = "/api/links/person-case";
  var API_PERSONS = "/api/persons";

  var ROLE_LABELS = {
    suspeito:     "Suspeito",
    investigado:  "Investigado",
    vitima:       "Vitima",
    testemunha:   "Testemunha",
    envolvido:    "Envolvido",
    interlocutor: "Interlocutor",
    outro:        "Outro"
  };

  var RELIABILITY_LABELS = {
    pending:   "Pendente",
    low:       "Baixo",
    medium:    "Medio",
    high:      "Alto",
    validated: "Validado"
  };

  var loadingEl      = null;
  var notFoundEl     = null;
  var contentEl      = null;
  var archivedNoteEl = null;
  var editBtnEl      = null;

  var linksLoadingEl   = null;
  var linksEmptyEl     = null;
  var linksTableWrapEl = null;
  var linksTbodyEl     = null;
  var btnVincularEl    = null;

  var modalBackdropEl     = null;
  var modalCloseEl        = null;
  var modalCancelEl       = null;
  var modalConfirmarEl    = null;
  var vpPersonSelect      = null;
  var vpPersonHint        = null;
  var vpRoleSelect        = null;
  var vpSourceInput       = null;
  var vpReliabilitySelect = null;
  var vpNotesInput        = null;

  var plateaCheckboxEl = null;
  var plateaSavingEl   = null;

  var caseId = null;
  var currentPlateaStatus = "none";

  var MESES = ["JAN","FEV","MAR","ABR","MAI","JUN",
               "JUL","AGO","SET","OUT","NOV","DEZ"];

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  function formatDateTime(iso) {
    if (!iso) return "-";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  function formatDateOnly(value) {
    if (!value) return "-";
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

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function statusBadgeHtml(status) {
    var map = {
      "active":   { cls: "badge--ativo",     txt: "[ATIVO]" },
      "archived": { cls: "badge--arquivado", txt: "[ARQUIVADO]" }
    };
    var entry = map[status] || { cls: "badge--arquivado", txt: "[" + String(status).toUpperCase() + "]" };
    return '<span class="badge ' + entry.cls + '">' + entry.txt + "</span>";
  }

  function plateaStatusBadgeHtml(plateaStatus) {
    var map = {
      "none":         { cls: "badge--arquivado", txt: "[NAO COMPARTILHADO]" },
      "shared":       { cls: "badge--ativo",     txt: "[PLATEA: SINCRONIZADO]" },
      "pending_sync": { cls: "badge--pendente",  txt: "[PLATEA: PENDENTE]" },
      "error":        { cls: "badge--erro",      txt: "[PLATEA: ERRO]" }
    };
    var entry = map[plateaStatus] || { cls: "badge--arquivado", txt: "[" + String(plateaStatus).toUpperCase() + "]" };
    return '<span class="badge ' + entry.cls + '">' + entry.txt + "</span>";
  }

  function plateaExcludeBadgeHtml(excluded) {
    if (excluded) {
      return '<span class="badge badge--arquivado" style="font-size:0.7rem;">[NAO COMPARTILHAR]</span>';
    }
    return '<span class="badge" style="font-size:0.7rem; opacity:0.4;">[COMPARTILHAR]</span>';
  }

  function renderPlateaStatus(plateaStatus) {
    currentPlateaStatus = plateaStatus || "none";
    if (plateaCheckboxEl) {
      plateaCheckboxEl.checked = (currentPlateaStatus === "shared" || currentPlateaStatus === "pending_sync");
    }
    var badgeSlot = contentEl ? contentEl.querySelector('[data-field="platea_status_badge"]') : null;
    if (badgeSlot) badgeSlot.innerHTML = plateaStatusBadgeHtml(currentPlateaStatus);
  }

  function togglePlatea() {
    if (!plateaCheckboxEl) return;
    var novoStatus = plateaCheckboxEl.checked ? "shared" : "none";
    if (plateaSavingEl) plateaSavingEl.hidden = false;
    if (plateaCheckboxEl) plateaCheckboxEl.disabled = true;

    fetch(API_CASES + "/" + encodeURIComponent(caseId), {
      method: "PATCH",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ platea_status: novoStatus })
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        renderPlateaStatus(data.platea_status);
        var msg = data.platea_status === "shared"
          ? "Caso compartilhado na Platea."
          : "Caso removido da Platea.";
        toast("success", "Platea", msg);
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao atualizar platea_status", err);
        renderPlateaStatus(currentPlateaStatus);
        toast("error", "Erro", "Nao foi possivel atualizar o status da Platea.");
      })
      .finally(function () {
        if (plateaSavingEl) plateaSavingEl.hidden = true;
        if (plateaCheckboxEl) plateaCheckboxEl.disabled = false;
      });
  }

  // ================================================================
  // AT-03.7: toggle [NAO COMPARTILHAR] por item
  // ================================================================

  function toggleItemPlateaExclude(itemType, itemId, currentExcluded, badgeCellEl, btnEl) {
    var novoExclude = !currentExcluded;
    if (btnEl) btnEl.disabled = true;

    fetch(
      API_CASES + "/" + encodeURIComponent(caseId) +
      "/items/" + encodeURIComponent(itemType) +
      "/" + encodeURIComponent(itemId) +
      "/platea_exclude",
      {
        method: "PATCH",
        headers: { "Accept": "application/json", "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ exclude: novoExclude })
      }
    )
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        if (badgeCellEl) badgeCellEl.innerHTML = plateaExcludeBadgeHtml(data.platea_exclude);
        if (btnEl) {
          btnEl.dataset.excluded = data.platea_exclude ? "1" : "0";
          btnEl.textContent      = data.platea_exclude ? "Liberar" : "Excluir";
          btnEl.title            = data.platea_exclude
            ? "Clique para permitir compartilhamento"
            : "Clique para excluir da Platea";
        }
        var msg = data.platea_exclude
          ? "Item marcado como [NAO COMPARTILHAR]."
          : "Item removido de [NAO COMPARTILHAR].";
        toast("success", "Platea", msg);
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao atualizar platea_exclude", err);
        toast("error", "Erro", "Nao foi possivel atualizar o item.");
      })
      .finally(function () {
        if (btnEl) btnEl.disabled = false;
      });
  }

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

  function toast(type, title, msg) {
    if (window.CIRCE && window.CIRCE.toast && window.CIRCE.toast[type]) {
      window.CIRCE.toast[type](title, msg);
    }
  }

  function setField(field, value) {
    if (!contentEl) return;
    var el = contentEl.querySelector('[data-field="' + field + '"]');
    if (!el) return;
    var txt = (value === null || value === undefined || value === "") ? "-" : String(value);
    el.textContent = txt;
  }

  function showLoading() {
    if (loadingEl) loadingEl.hidden = false;
    if (notFoundEl) notFoundEl.hidden = true;
    if (contentEl)  contentEl.hidden = true;
  }

  function showNotFound() {
    if (loadingEl) loadingEl.hidden = true;
    if (notFoundEl) notFoundEl.hidden = false;
    if (contentEl)  contentEl.hidden = true;
  }

  function showContent() {
    if (loadingEl) loadingEl.hidden = true;
    if (notFoundEl) notFoundEl.hidden = true;
    if (contentEl)  contentEl.hidden = false;
  }

  function renderCase(c) {
    setField("case_code", c.case_code);
    setField("name", c.name);

    var badgeSlot = contentEl ? contentEl.querySelector('[data-field="status_badge"]') : null;
    if (badgeSlot) badgeSlot.innerHTML = statusBadgeHtml(c.status);

    setField("unit", c.unit);
    setField("responsible", c.responsible);
    setField("created_at", formatDateTime(c.created_at));
    setField("description", c.description);
    setField("procedure_number", c.procedure_number);
    setField("fact_date", formatDateOnly(c.fact_date));
    setField("tags", c.tags);
    setField("notes", c.notes);
    setField("created_at_full", formatDateTime(c.created_at));
    setField("created_by", c.created_by);
    setField("updated_at", formatDateTime(c.updated_at));
    setField("updated_by", c.updated_by);

    renderPlateaStatus(c.platea_status);

    if (archivedNoteEl) archivedNoteEl.hidden = (c.status !== "archived");

    if (editBtnEl) {
      editBtnEl.onclick = function () {
        window.location.href = "/cases?edit=" + encodeURIComponent(c.id);
      };
    }

    showContent();
  }

  function loadCase() {
    showLoading();
    fetch(API_CASES + "/" + encodeURIComponent(caseId), {
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
        renderCase(data);
        loadLinks();
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao carregar caso", err);
        showNotFound();
        toast("error", "Erro", "Nao foi possivel carregar o caso.");
      });
  }

  // ================================================================
  // VINCULOS - RF-003 + AT-03.7
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

    if (!links || links.length === 0) {
      linksShowEmpty();
      return;
    }

    linksTbodyEl.innerHTML = "";

    links.forEach(function (lk) {
      var roleLabel        = ROLE_LABELS[lk.role_in_case] || lk.role_in_case || "-";
      var reliabilityLabel = RELIABILITY_LABELS[lk.reliability_level] || lk.reliability_level || "-";
      var personName       = lk.person_name || ("id " + lk.person_id);
      var source           = lk.source || "-";
      var linkId           = lk.id;
      var excluded         = lk.platea_exclude || false;

      var tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border, #2C2E38)";
      tr.dataset.linkId = String(linkId);

      tr.innerHTML =
        '<td style="padding: var(--space-2) var(--space-3) var(--space-2) 0; font-weight: 500;">' +
          escapeHtml(personName) +
        "</td>" +
        '<td class="mono" style="padding: var(--space-2) var(--space-3);">' +
          escapeHtml(roleLabel) +
        "</td>" +
        '<td class="mono text-secondary" style="padding: var(--space-2) var(--space-3);">' +
          escapeHtml(reliabilityLabel) +
        "</td>" +
        '<td class="text-secondary" style="padding: var(--space-2) var(--space-3); font-size: 0.8rem; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="' + escapeHtml(source) + '">' +
          escapeHtml(source) +
        "</td>";

      // Celula Platea com badge + botao
      var tdPlatea = document.createElement("td");
      tdPlatea.style.cssText = "padding: var(--space-2) var(--space-3); white-space: nowrap;";
      tdPlatea.innerHTML = plateaExcludeBadgeHtml(excluded);

      var btnPlatea = document.createElement("button");
      btnPlatea.type = "button";
      btnPlatea.className = "btn btn--text";
      btnPlatea.style.cssText = "font-size: 0.75rem; color: var(--text-tertiary); margin-left: var(--space-2);";
      btnPlatea.dataset.excluded = excluded ? "1" : "0";
      btnPlatea.textContent = excluded ? "Liberar" : "Excluir";
      btnPlatea.title = excluded
        ? "Clique para permitir compartilhamento"
        : "Clique para excluir da Platea";

      btnPlatea.addEventListener("click", function () {
        var isExcluded = btnPlatea.dataset.excluded === "1";
        toggleItemPlateaExclude("person_link", linkId, isExcluded, tdPlatea, btnPlatea);
      });

      tdPlatea.appendChild(btnPlatea);
      tr.appendChild(tdPlatea);

      var tdAcoes = document.createElement("td");
      tdAcoes.style.cssText = "padding: var(--space-2) 0 var(--space-2) var(--space-3); white-space: nowrap;";
      var btnRemover = document.createElement("button");
      btnRemover.type = "button";
      btnRemover.className = "btn btn--text";
      btnRemover.style.cssText = "font-size: 0.8rem; color: var(--text-tertiary);";
      btnRemover.textContent = "Remover";
      btnRemover.addEventListener("click", function () {
        removeLink(linkId, tr);
      });
      tdAcoes.appendChild(btnRemover);
      tr.appendChild(tdAcoes);

      linksTbodyEl.appendChild(tr);
    });

    linksShowTable();
  }

  function loadLinks() {
    linksShowLoading();
    fetch(API_LINKS + "?case_id=" + encodeURIComponent(caseId), {
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
        console.error("[case_detail] erro ao carregar vinculos", err);
        linksShowEmpty();
        toast("error", "Erro", "Nao foi possivel carregar os vinculos.");
      });
  }

  function removeLink(linkId, rowEl) {
    if (!confirm("Remover este vinculo? A acao sera registrada no log de auditoria.")) return;

    fetch(API_LINKS + "/" + encodeURIComponent(linkId), {
      method: "DELETE",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 404) {
          toast("error", "Erro", "Vinculo nao encontrado.");
          return null;
        }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        if (rowEl && rowEl.parentNode) rowEl.parentNode.removeChild(rowEl);
        if (linksTbodyEl && linksTbodyEl.rows.length === 0) linksShowEmpty();
        toast("success", "Vinculo removido", "O vinculo foi removido com sucesso.");
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao remover vinculo", err);
        toast("error", "Erro", "Nao foi possivel remover o vinculo.");
      });
  }

  // ================================================================
  // MODAL - Vincular pessoa
  // ================================================================

  function modalOpen() {
    if (!modalBackdropEl) return;
    modalBackdropEl.setAttribute("data-open", "true");
    loadPersonsIntoSelect();
    if (vpPersonSelect)      vpPersonSelect.value = "";
    if (vpRoleSelect)        vpRoleSelect.value = "";
    if (vpSourceInput)       vpSourceInput.value = "";
    if (vpReliabilitySelect) vpReliabilitySelect.value = "pending";
    if (vpNotesInput)        vpNotesInput.value = "";
  }

  function modalClose() {
    if (!modalBackdropEl) return;
    modalBackdropEl.setAttribute("data-open", "false");
  }

  function loadPersonsIntoSelect() {
    if (!vpPersonSelect) return;
    if (vpPersonHint) {
      vpPersonHint.hidden = false;
      vpPersonHint.textContent = "Carregando pessoas...";
    }
    vpPersonSelect.innerHTML = '<option value="">- selecione -</option>';

    fetch(API_PERSONS + "?include_archived=false&sort_by=full_name&descending=false", {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (persons) {
        if (persons === null) return;
        if (vpPersonHint) vpPersonHint.hidden = true;
        if (persons.length === 0) {
          var opt = document.createElement("option");
          opt.value = ""; opt.disabled = true;
          opt.textContent = "Nenhuma pessoa cadastrada";
          vpPersonSelect.appendChild(opt);
          return;
        }
        persons.forEach(function (p) {
          var opt = document.createElement("option");
          opt.value = String(p.id);
          opt.textContent = p.full_name + (p.cpf ? " - " + formatCpf(p.cpf) : "");
          vpPersonSelect.appendChild(opt);
        });
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao carregar pessoas para select", err);
        if (vpPersonHint) {
          vpPersonHint.hidden = false;
          vpPersonHint.textContent = "Erro ao carregar pessoas.";
        }
      });
  }

  function formatCpf(cpf) {
    if (!cpf) return "";
    var d = String(cpf).replace(/\D/g, "");
    if (d.length !== 11) return cpf;
    return d.slice(0,3) + "." + d.slice(3,6) + "." + d.slice(6,9) + "-" + d.slice(9,11);
  }

  function submitVincular() {
    var personId    = vpPersonSelect      ? vpPersonSelect.value      : "";
    var roleInCase  = vpRoleSelect        ? vpRoleSelect.value        : "";
    var source      = vpSourceInput       ? vpSourceInput.value.trim(): "";
    var reliability = vpReliabilitySelect ? vpReliabilitySelect.value : "pending";
    var notes       = vpNotesInput        ? vpNotesInput.value.trim() : "";

    if (!personId)   { toast("error", "Campo obrigatorio", "Selecione uma pessoa."); return; }
    if (!roleInCase) { toast("error", "Campo obrigatorio", "Selecione o tipo de participacao."); return; }
    if (!source)     { toast("error", "Campo obrigatorio", "Informe a fonte da informacao."); return; }

    if (modalConfirmarEl) modalConfirmarEl.disabled = true;

    var body = {
      case_id:           caseId,
      person_id:         parseInt(personId, 10),
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
              : "Ja existe um vinculo ativo com este papel para esta pessoa neste caso.";
            toast("error", "Vinculo duplicado", msg);
            return null;
          });
        }
        if (response.status === 404) { toast("error", "Erro", "Caso ou pessoa nao encontrados."); return null; }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        modalClose();
        toast("success", "Vinculo criado", "Pessoa vinculada ao caso com sucesso.");
        loadLinks();
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao criar vinculo", err);
        toast("error", "Erro", "Nao foi possivel criar o vinculo.");
      })
      .finally(function () {
        if (modalConfirmarEl) modalConfirmarEl.disabled = false;
      });
  }

  function parseCaseIdFromPath() {
    var m = window.location.pathname.match(/\/cases\/(\d+)\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  function setup() {
    contentEl = document.getElementById("case-detail-content");
    loadingEl = document.getElementById("case-detail-loading");
    if (!contentEl || !loadingEl) return;

    notFoundEl     = document.getElementById("case-detail-notfound");
    archivedNoteEl = document.getElementById("case-detail-archived-note");
    editBtnEl      = document.getElementById("case-detail-edit");

    linksLoadingEl   = document.getElementById("links-loading");
    linksEmptyEl     = document.getElementById("links-empty");
    linksTableWrapEl = document.getElementById("links-table-wrap");
    linksTbodyEl     = document.getElementById("links-tbody");
    btnVincularEl    = document.getElementById("btn-vincular-pessoa");

    modalBackdropEl     = document.getElementById("modal-vincular-backdrop");
    modalCloseEl        = document.getElementById("modal-vincular-close");
    modalCancelEl       = document.getElementById("modal-vincular-cancel");
    modalConfirmarEl    = document.getElementById("modal-vincular-confirmar");
    vpPersonSelect      = document.getElementById("vp-person-select");
    vpPersonHint        = document.getElementById("vp-person-hint");
    vpRoleSelect        = document.getElementById("vp-role-select");
    vpSourceInput       = document.getElementById("vp-source-input");
    vpReliabilitySelect = document.getElementById("vp-reliability-select");
    vpNotesInput        = document.getElementById("vp-notes-input");

    plateaCheckboxEl = document.getElementById("platea-checkbox");
    plateaSavingEl   = document.getElementById("platea-saving");

    caseId = parseCaseIdFromPath();
    if (caseId === null || isNaN(caseId)) { showNotFound(); return; }

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (modalBackdropEl && modalBackdropEl.getAttribute("data-open") === "true") {
          modalClose();
        } else {
          e.preventDefault();
          window.location.href = "/cases";
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
    if (plateaCheckboxEl) plateaCheckboxEl.addEventListener("change", togglePlatea);

    loadCase();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();