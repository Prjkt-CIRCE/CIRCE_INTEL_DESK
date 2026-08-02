/* ============================================================
   CIRCE Intel Desk — person_detail.js
   RF-002 detalhe · RF-003 vínculos caso · RF-005 vínculo faccional
   Sprint 01-B B6: seção VÍNCULO FACCIONAL adicionada.
   ============================================================ */
(function () {
  "use strict";

  var API_PERSONS = "/api/persons";
  var API_LINKS   = "/api/links/person-case";
  var API_CASES   = "/api/cases";
  var API_ORG_LINKS = "/api/links/person-org";
  var API_ORGS    = "/api/organizations";

  var ROLE_LABELS = {
    suspeito: "Suspeito", investigado: "Investigado", vitima: "Vítima",
    testemunha: "Testemunha", envolvido: "Envolvido",
    interlocutor: "Interlocutor", outro: "Outro"
  };

  var RELIABILITY_LABELS = {
    pending: "Pendente", low: "Baixo", medium: "Médio",
    high: "Alto", validated: "Validado"
  };

  var ORG_RELIABILITY_LABELS = {
    pending: "Pendente", baixo: "Baixo", medio: "Médio",
    alto: "Alto", validado: "Validado"
  };

  var LINK_TYPE_LABELS = {
    membro: "Membro", suspeito_membro: "Suspeito de membro",
    simpatizante: "Simpatizante", ex_membro: "Ex-membro",
    familiar: "Familiar", vitima: "Vítima", rival: "Rival"
  };

  // DOM refs — pessoa
  var loadingEl, notFoundEl, contentEl, archivedNoteEl, editBtnEl;

  // DOM refs — vínculos caso
  var linksLoadingEl, linksEmptyEl, linksTableWrapEl, linksTbodyEl, btnVincularEl;
  var modalBackdropEl, modalCloseEl, modalCancelEl, modalConfirmarEl;
  var vcCaseSelect, vcCaseHint, vcRoleSelect, vcSourceInput, vcReliabilitySelect, vcNotesInput;

  // DOM refs — vínculos org (RF-005)
  var orgLinksLoadingEl, orgLinksEmptyEl, orgLinksTableWrapEl, orgLinksTbodyEl, btnVincularOrgEl;
  var orgModalBackdropEl, orgModalCancelEl, orgModalConfirmarEl;
  var voOrgSelect, voOrgHint, voLinkType, voPosition, voSource, voReliability;

  var personId = null;

  var MESES = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"];
  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function formatDateTime(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear() + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }
  function formatDateOnly(value) {
    if (!value) return "—";
    var s = String(value);
    var dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(s);
    var d = new Date(s);
    if (isNaN(d.getTime())) return s;
    if (dateOnly) return pad2(d.getUTCDate()) + "." + MESES[d.getUTCMonth()] + "." + d.getUTCFullYear();
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear() + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }
  function formatCpfDisplay(cpf) {
    if (!cpf) return "—";
    if (/^\d{11}$/.test(cpf)) return cpf.slice(0,3) + "." + cpf.slice(3,6) + "." + cpf.slice(6,9) + "-" + cpf.slice(9);
    return cpf;
  }
  function formatAliasesDisplay(aliases) {
    if (!aliases) return "—";
    var parts = aliases.split(";").map(function(s) { return s.trim(); }).filter(Boolean);
    return parts.length ? parts.join(" · ") : "—";
  }
  function statusBadgeHtml(status) {
    var map = { "active": { cls: "badge--ativo", txt: "[ATIVO]" }, "archived": { cls: "badge--arquivado", txt: "[ARQUIVADO]" } };
    var entry = map[status] || { cls: "badge--arquivado", txt: "[" + String(status).toUpperCase() + "]" };
    return '<span class="badge ' + entry.cls + '">' + entry.txt + "</span>";
  }
  function handleAuthLapse(response) {
    var isHtml = response.redirected || (response.headers.get("content-type") || "").indexOf("text/html") >= 0;
    if (response.status === 401 || isHtml) { window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname); return true; }
    return false;
  }
  function toast(type, title, msg) {
    if (window.CIRCE && window.CIRCE.toast && window.CIRCE.toast[type]) window.CIRCE.toast[type](title, msg);
  }
  function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
  }
  function setField(field, value) {
    if (!contentEl) return;
    var el = contentEl.querySelector('[data-field="' + field + '"]');
    if (!el) return;
    el.textContent = (value === null || value === undefined || value === "") ? "—" : String(value);
  }
  function showLoading()  { if (loadingEl) loadingEl.hidden = false; if (notFoundEl) notFoundEl.hidden = true; if (contentEl) contentEl.hidden = true; }
  function showNotFound() { if (loadingEl) loadingEl.hidden = true; if (notFoundEl) notFoundEl.hidden = false; if (contentEl) contentEl.hidden = true; }
  function showContent()  { if (loadingEl) loadingEl.hidden = true; if (notFoundEl) notFoundEl.hidden = true; if (contentEl) contentEl.hidden = false; }

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
    var reliabilityMap = { "pending": "Pendente", "low": "Baixo", "medium": "Médio", "high": "Alto", "validated": "Validado" };
    setField("reliability_level", reliabilityMap[p.reliability_level] || p.reliability_level || "—");
    setField("notes", p.notes);
    setField("created_at_full", formatDateTime(p.created_at));
    setField("created_by", p.created_by);
    setField("updated_at", formatDateTime(p.updated_at));
    setField("updated_by", p.updated_by);
    if (archivedNoteEl) archivedNoteEl.hidden = (p.status !== "archived");
    if (editBtnEl) editBtnEl.onclick = function () { window.location.href = "/persons?edit=" + encodeURIComponent(p.id); };
    showContent();
  }

  function loadPerson() {
    showLoading();
    fetch(API_PERSONS + "/" + encodeURIComponent(personId), { credentials: "same-origin" })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (r.status === 404) { showNotFound(); return null; }
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        renderPerson(data);
        loadOrgLinks();
        loadLinks();
      })
      .catch(function () { showNotFound(); });
  }

  // ================================================================
  // VÍNCULO FACCIONAL — RF-005
  // ================================================================

  function orgLinksShowLoading() { if (orgLinksLoadingEl) orgLinksLoadingEl.hidden = false; if (orgLinksEmptyEl) orgLinksEmptyEl.hidden = true; if (orgLinksTableWrapEl) orgLinksTableWrapEl.hidden = true; }
  function orgLinksShowEmpty()   { if (orgLinksLoadingEl) orgLinksLoadingEl.hidden = true; if (orgLinksEmptyEl) orgLinksEmptyEl.hidden = false; if (orgLinksTableWrapEl) orgLinksTableWrapEl.hidden = true; }
  function orgLinksShowTable()   { if (orgLinksLoadingEl) orgLinksLoadingEl.hidden = true; if (orgLinksEmptyEl) orgLinksEmptyEl.hidden = true; if (orgLinksTableWrapEl) orgLinksTableWrapEl.hidden = false; }

  function loadOrgLinks() {
    orgLinksShowLoading();
    fetch(API_ORG_LINKS + "?person_id=" + encodeURIComponent(personId), { credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) { if (data === null) return; renderOrgLinksTable(data); })
      .catch(function () { orgLinksShowEmpty(); });
  }

  function renderOrgLinksTable(links) {
    if (!orgLinksTbodyEl) return;
    if (!links || links.length === 0) { orgLinksShowEmpty(); return; }
    orgLinksTbodyEl.innerHTML = "";
    links.forEach(function (lk) {
      var tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-subtle)";
      tr.dataset.linkId = String(lk.id);
      tr.innerHTML =
        '<td style="padding: var(--space-2) var(--space-3) var(--space-2) 0; font-weight:500;">' + escapeHtml(lk.org_name || "id " + lk.org_id) + "</td>" +
        '<td class="mono" style="padding: var(--space-2) var(--space-3); font-size:0.8rem;">' + escapeHtml(LINK_TYPE_LABELS[lk.link_type] || lk.link_type) + "</td>" +
        '<td class="mono" style="padding: var(--space-2) var(--space-3); font-size:0.8rem; color:var(--text-secondary);">' + escapeHtml(lk.position || "—") + "</td>" +
        '<td class="mono" style="padding: var(--space-2) var(--space-3); font-size:0.8rem; color:var(--text-secondary);">' + escapeHtml(ORG_RELIABILITY_LABELS[lk.reliability_level] || lk.reliability_level) + "</td>" +
        '<td style="padding: var(--space-2) 0 var(--space-2) var(--space-3);"><button type="button" class="btn btn--text" style="font-size:0.8rem;color:var(--text-tertiary);" data-remove-org-link="' + lk.id + '">Remover</button></td>';
      tr.querySelector("[data-remove-org-link]").addEventListener("click", function () { removeOrgLink(lk.id, tr); });
      orgLinksTbodyEl.appendChild(tr);
    });
    orgLinksShowTable();
  }

  function removeOrgLink(linkId, rowEl) {
    if (!confirm("Remover este vínculo faccional? A ação será registrada no log de auditoria.")) return;
    fetch(API_ORG_LINKS + "/" + encodeURIComponent(linkId), { method: "DELETE", credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) {
        if (!data) return;
        if (rowEl && rowEl.parentNode) rowEl.parentNode.removeChild(rowEl);
        if (orgLinksTbodyEl && orgLinksTbodyEl.rows.length === 0) orgLinksShowEmpty();
        toast("success", "Vínculo removido", "");
      })
      .catch(function () { toast("error", "Erro", "Não foi possível remover o vínculo."); });
  }

  function orgModalOpen() {
    if (!orgModalBackdropEl) return;
    loadOrgsIntoSelect();
    if (voLinkType) voLinkType.value = "";
    if (voPosition) voPosition.value = "";
    if (voSource) voSource.value = "";
    if (voReliability) voReliability.value = "pending";
    orgModalBackdropEl.setAttribute("data-open", "true");
  }

  function orgModalClose() { if (orgModalBackdropEl) orgModalBackdropEl.setAttribute("data-open", "false"); }

  function loadOrgsIntoSelect() {
    if (!voOrgSelect) return;
    if (voOrgHint) { voOrgHint.hidden = false; voOrgHint.textContent = "Carregando organizações…"; }
    voOrgSelect.innerHTML = '<option value="">— selecione —</option>';
    fetch(API_ORGS + "?include_archived=false&sort_by=name&descending=false", { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (orgs) {
        if (voOrgHint) voOrgHint.hidden = true;
        orgs.forEach(function (o) {
          var opt = document.createElement("option");
          opt.value = String(o.id);
          opt.textContent = o.name + (o.siglas ? " (" + o.siglas + ")" : "");
          voOrgSelect.appendChild(opt);
        });
      })
      .catch(function () { if (voOrgHint) { voOrgHint.hidden = false; voOrgHint.textContent = "Erro ao carregar organizações."; } });
  }

  function submitVincularOrg() {
    var orgId      = voOrgSelect    ? voOrgSelect.value    : "";
    var linkType   = voLinkType     ? voLinkType.value     : "";
    var position   = voPosition     ? voPosition.value.trim() : "";
    var source     = voSource       ? voSource.value.trim()   : "";
    var reliability = voReliability ? voReliability.value     : "pending";

    if (!orgId)    { toast("error", "Campo obrigatório", "Selecione uma organização."); return; }
    if (!linkType) { toast("error", "Campo obrigatório", "Selecione o tipo de vínculo."); return; }
    if (!source)   { toast("error", "Campo obrigatório", "Informe a fonte da informação."); return; }

    if (orgModalConfirmarEl) orgModalConfirmarEl.disabled = true;

    var body = { person_id: personId, org_id: parseInt(orgId, 10), link_type: linkType, source: source, reliability_level: reliability };
    if (position) body.position = position;

    fetch(API_ORG_LINKS, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (r.status === 409) { return r.json().then(function (e) { toast("error", "Vínculo duplicado", (e && e.detail && e.detail.message) || "Vínculo já existe."); return null; }); }
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        orgModalClose();
        toast("success", "Vínculo criado", "Pessoa vinculada à organização com sucesso.");
        loadOrgLinks();
      })
      .catch(function () { toast("error", "Erro", "Não foi possível criar o vínculo."); })
      .finally(function () { if (orgModalConfirmarEl) orgModalConfirmarEl.disabled = false; });
  }

  // ================================================================
  // VÍNCULOS CASO — RF-003
  // ================================================================

  function linksShowLoading() { if (linksLoadingEl) linksLoadingEl.hidden = false; if (linksEmptyEl) linksEmptyEl.hidden = true; if (linksTableWrapEl) linksTableWrapEl.hidden = true; }
  function linksShowEmpty()   { if (linksLoadingEl) linksLoadingEl.hidden = true; if (linksEmptyEl) linksEmptyEl.hidden = false; if (linksTableWrapEl) linksTableWrapEl.hidden = true; }
  function linksShowTable()   { if (linksLoadingEl) linksLoadingEl.hidden = true; if (linksEmptyEl) linksEmptyEl.hidden = true; if (linksTableWrapEl) linksTableWrapEl.hidden = false; }

  function renderLinksTable(links) {
    if (!linksTbodyEl) return;
    if (!links || links.length === 0) { linksShowEmpty(); return; }
    var rows = links.map(function (lk) {
      var roleLabel = ROLE_LABELS[lk.role_in_case] || lk.role_in_case || "—";
      var relLabel  = RELIABILITY_LABELS[lk.reliability_level] || lk.reliability_level || "—";
      var caseLabel = lk.case_code ? lk.case_code + (lk.case_name ? " — " + lk.case_name : "") : ("id " + lk.case_id);
      var tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-subtle)";
      tr.dataset.linkId = String(lk.id);
      tr.innerHTML =
        '<td class="mono" style="padding: var(--space-2) var(--space-3) var(--space-2) 0; font-weight:500;">' + escapeHtml(caseLabel) + "</td>" +
        '<td class="mono" style="padding: var(--space-2) var(--space-3);">' + escapeHtml(roleLabel) + "</td>" +
        '<td class="mono text-secondary" style="padding: var(--space-2) var(--space-3);">' + escapeHtml(relLabel) + "</td>" +
        '<td class="text-secondary" style="padding: var(--space-2) var(--space-3); font-size: 0.8rem; max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="' + escapeHtml(lk.source || "") + '">' + escapeHtml(lk.source || "—") + "</td>" +
        '<td style="padding: var(--space-2) 0 var(--space-2) var(--space-3); white-space:nowrap;"><button type="button" class="btn btn--text" style="font-size:0.8rem;color:var(--text-tertiary);" data-remove-link="' + lk.id + '">Remover</button></td>';
      tr.querySelector("[data-remove-link]").addEventListener("click", function () { removeLink(lk.id, tr); });
      return tr;
    });
    linksTbodyEl.innerHTML = "";
    rows.forEach(function (tr) { linksTbodyEl.appendChild(tr); });
    linksShowTable();
  }

  function loadLinks() {
    linksShowLoading();
    fetch(API_LINKS + "?person_id=" + encodeURIComponent(personId), { credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) { if (data === null) return; renderLinksTable(data); })
      .catch(function () { linksShowEmpty(); });
  }

  function removeLink(linkId, rowEl) {
    if (!confirm("Remover este vínculo? A ação será registrada no log de auditoria.")) return;
    fetch(API_LINKS + "/" + encodeURIComponent(linkId), { method: "DELETE", credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (r.status === 404) { toast("error", "Erro", "Vínculo não encontrado."); return null; } if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) {
        if (!data) return;
        if (rowEl && rowEl.parentNode) rowEl.parentNode.removeChild(rowEl);
        if (linksTbodyEl && linksTbodyEl.rows.length === 0) linksShowEmpty();
        toast("success", "Vínculo removido", "O vínculo foi removido com sucesso.");
      })
      .catch(function () { toast("error", "Erro", "Não foi possível remover o vínculo."); });
  }

  function modalOpen() {
    if (!modalBackdropEl) return;
    if (vcCaseSelect) vcCaseSelect.value = "";
    if (vcRoleSelect) vcRoleSelect.value = "";
    if (vcSourceInput) vcSourceInput.value = "";
    if (vcReliabilitySelect) vcReliabilitySelect.value = "pending";
    if (vcNotesInput) vcNotesInput.value = "";
    loadCasesIntoSelect();
    modalBackdropEl.setAttribute("data-open", "true");
  }

  function modalClose() { if (modalBackdropEl) modalBackdropEl.setAttribute("data-open", "false"); }

  function loadCasesIntoSelect() {
    if (!vcCaseSelect) return;
    if (vcCaseHint) { vcCaseHint.hidden = false; vcCaseHint.textContent = "Carregando casos…"; }
    vcCaseSelect.innerHTML = '<option value="">— selecione —</option>';
    fetch(API_CASES + "?include_archived=false&sort_by=case_code&descending=false", { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (cases) {
        if (vcCaseHint) vcCaseHint.hidden = true;
        cases.forEach(function (c) {
          var opt = document.createElement("option");
          opt.value = String(c.id);
          opt.textContent = c.case_code + " — " + c.name;
          vcCaseSelect.appendChild(opt);
        });
      })
      .catch(function () { if (vcCaseHint) { vcCaseHint.hidden = false; vcCaseHint.textContent = "Erro ao carregar casos."; } });
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
    var body = { case_id: parseInt(caseId, 10), person_id: personId, role_in_case: roleInCase, source: source, reliability_level: reliability, notes: notes || null };
    fetch(API_LINKS, {
      method: "POST",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (r.status === 409) { return r.json().then(function (e) { toast("error", "Vínculo duplicado", (e && e.detail && e.detail.message) || "Já existe vínculo ativo."); return null; }); }
        if (r.status === 404) { toast("error", "Erro", "Caso ou pessoa não encontrados."); return null; }
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        modalClose();
        toast("success", "Vínculo criado", "Pessoa vinculada ao caso com sucesso.");
        loadLinks();
      })
      .catch(function () { toast("error", "Erro", "Não foi possível criar o vínculo."); })
      .finally(function () { if (modalConfirmarEl) modalConfirmarEl.disabled = false; });
  }

  function parsePersonIdFromPath() {
    var m = window.location.pathname.match(/\/persons\/(\d+)\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  function setup() {
    contentEl = document.getElementById("person-detail-content");
    loadingEl = document.getElementById("person-detail-loading");
    if (!contentEl || !loadingEl) return;

    notFoundEl     = document.getElementById("person-detail-notfound");
    archivedNoteEl = document.getElementById("person-detail-archived-note");
    editBtnEl      = document.getElementById("person-detail-edit");

    // Vínculos caso
    linksLoadingEl   = document.getElementById("person-links-loading");
    linksEmptyEl     = document.getElementById("person-links-empty");
    linksTableWrapEl = document.getElementById("person-links-table-wrap");
    linksTbodyEl     = document.getElementById("person-links-tbody");
    btnVincularEl    = document.getElementById("btn-vincular-caso");
    modalBackdropEl  = document.getElementById("modal-vincular-caso-backdrop");
    modalCancelEl    = document.getElementById("modal-vincular-caso-cancel");
    modalConfirmarEl = document.getElementById("modal-vincular-caso-confirmar");
    vcCaseSelect        = document.getElementById("vc-case-select");
    vcCaseHint          = document.getElementById("vc-case-hint");
    vcRoleSelect        = document.getElementById("vc-role-select");
    vcSourceInput       = document.getElementById("vc-source-input");
    vcReliabilitySelect = document.getElementById("vc-reliability-select");
    vcNotesInput        = document.getElementById("vc-notes-input");

    // Vínculos org
    orgLinksLoadingEl   = document.getElementById("org-links-loading");
    orgLinksEmptyEl     = document.getElementById("org-links-empty");
    orgLinksTableWrapEl = document.getElementById("org-links-table-wrap");
    orgLinksTbodyEl     = document.getElementById("org-links-tbody");
    btnVincularOrgEl    = document.getElementById("btn-vincular-org");
    orgModalBackdropEl  = document.getElementById("modal-vincular-org-backdrop");
    orgModalCancelEl    = document.getElementById("modal-vincular-org-cancel");
    orgModalConfirmarEl = document.getElementById("modal-vincular-org-confirmar");
    voOrgSelect    = document.getElementById("vo-org-select");
    voOrgHint      = document.getElementById("vo-org-hint");
    voLinkType     = document.getElementById("vo-link-type");
    voPosition     = document.getElementById("vo-position");
    voSource       = document.getElementById("vo-source");
    voReliability  = document.getElementById("vo-reliability");

    personId = parsePersonIdFromPath();
    if (!personId || isNaN(personId)) { showNotFound(); return; }

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (orgModalBackdropEl && orgModalBackdropEl.getAttribute("data-open") === "true") { orgModalClose(); return; }
        if (modalBackdropEl && modalBackdropEl.getAttribute("data-open") === "true") { modalClose(); return; }
        window.location.href = "/persons";
      }
    });

    if (btnVincularEl)    btnVincularEl.addEventListener("click", modalOpen);
    if (modalCancelEl)    modalCancelEl.addEventListener("click", modalClose);
    if (modalConfirmarEl) modalConfirmarEl.addEventListener("click", submitVincular);
    if (modalBackdropEl)  modalBackdropEl.addEventListener("click", function (e) { if (e.target === modalBackdropEl) modalClose(); });

    if (btnVincularOrgEl)    btnVincularOrgEl.addEventListener("click", orgModalOpen);
    if (orgModalCancelEl)    orgModalCancelEl.addEventListener("click", orgModalClose);
    if (orgModalConfirmarEl) orgModalConfirmarEl.addEventListener("click", submitVincularOrg);
    if (orgModalBackdropEl)  orgModalBackdropEl.addEventListener("click", function (e) { if (e.target === orgModalBackdropEl) orgModalClose(); });

    loadPerson();
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", setup); } else { setup(); }
})();