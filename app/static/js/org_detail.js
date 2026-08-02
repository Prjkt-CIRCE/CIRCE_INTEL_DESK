/* org_detail.js - Sprint 01-B */
(function () {
  "use strict";

  var API_ORG    = "/api/organizations";
  var API_LINKS  = "/api/links/person-org";
  var API_PERSONS = "/api/persons";
  var ORG_ORG_API = "/api/links/org-org";

  var LINK_TYPE_LABELS = {
    "membro": "Membro", "suspeito_membro": "Suspeito de membro",
    "simpatizante": "Simpatizante", "ex_membro": "Ex-membro",
    "familiar": "Familiar", "vitima": "Vitima", "rival": "Rival"
  };

  var RELIABILITY_LABELS = {
    "pending": "Pendente", "baixo": "Baixo", "medio": "Medio",
    "alto": "Alto", "validado": "Validado"
  };

  var ORG_TYPE_LABELS = {
    "faccao_prisional": "Faccao prisional", "milicia": "Milicia",
    "orcrim_trafico": "ORCRIM trafico", "orcrim_patrimonial": "ORCRIM patrimonial",
    "outra": "Outra"
  };

  var RELATION_LABELS = {
    "rivalidade": "Rivalidade", "alianca": "Alianca",
    "dissidencia": "Dissidencia", "fusao": "Fusao", "outra": "Outra"
  };

  var loadingEl, notFoundEl, contentEl, archivedNoteEl, editBtnEl;
  var linksLoadingEl, linksEmptyEl, linksTableWrapEl, linksTbodyEl, btnVincularEl;
  var modalBackdropEl, modalCancelEl, modalConfirmarEl;
  var vpPersonSelect, vpPersonHint, vpLinkType, vpPosition, vpSource, vpReliability;
  var ooLinksLoadingEl, ooLinksEmptyEl, ooLinksTableWrapEl, ooLinksTbodyEl, btnVincularOrgOrgEl;
  var ooModalEl, ooModalCancelEl, ooModalConfirmarEl;
  var ooOrgSelect, ooOrgHint, ooRelationType, ooSource, ooReliability;
  var orgId = null;

  function handleAuthLapse(r) {
    var isHtml = r.redirected || (r.headers.get("content-type") || "").indexOf("text/html") >= 0;
    if (r.status === 401 || isHtml) { window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname); return true; }
    return false;
  }

  function toast(type, title, msg) {
    if (window.CIRCE && window.CIRCE.toast) window.CIRCE.toast[type](title, msg);
  }

  function escapeHtml(s) {
    if (!s) return "";
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }

  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  var MESES = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"];
  function formatDateTime(iso) {
    if (!iso) return "--";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear() + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  function setField(field, value) {
    if (!contentEl) return;
    var el = contentEl.querySelector('[data-field="' + field + '"]');
    if (!el) return;
    el.textContent = (value === null || value === undefined || value === "") ? "--" : String(value);
  }

  function showLoading()  { if (loadingEl) loadingEl.hidden = false; if (notFoundEl) notFoundEl.hidden = true; if (contentEl) contentEl.hidden = true; }
  function showNotFound() { if (loadingEl) loadingEl.hidden = true; if (notFoundEl) notFoundEl.hidden = false; if (contentEl) contentEl.hidden = true; }
  function showContent()  { if (loadingEl) loadingEl.hidden = true; if (notFoundEl) notFoundEl.hidden = true; if (contentEl) contentEl.hidden = false; }

  function linksShowLoading() { if (linksLoadingEl) linksLoadingEl.hidden = false; if (linksEmptyEl) linksEmptyEl.hidden = true; if (linksTableWrapEl) linksTableWrapEl.hidden = true; }
  function linksShowEmpty()   { if (linksLoadingEl) linksLoadingEl.hidden = true; if (linksEmptyEl) linksEmptyEl.hidden = false; if (linksTableWrapEl) linksTableWrapEl.hidden = true; }
  function linksShowTable()   { if (linksLoadingEl) linksLoadingEl.hidden = true; if (linksEmptyEl) linksEmptyEl.hidden = true; if (linksTableWrapEl) linksTableWrapEl.hidden = false; }

  function ooShowLoading() { if (ooLinksLoadingEl) ooLinksLoadingEl.hidden = false; if (ooLinksEmptyEl) ooLinksEmptyEl.hidden = true; if (ooLinksTableWrapEl) ooLinksTableWrapEl.hidden = true; }
  function ooShowEmpty()   { if (ooLinksLoadingEl) ooLinksLoadingEl.hidden = true; if (ooLinksEmptyEl) ooLinksEmptyEl.hidden = false; if (ooLinksTableWrapEl) ooLinksTableWrapEl.hidden = true; }
  function ooShowTable()   { if (ooLinksLoadingEl) ooLinksLoadingEl.hidden = true; if (ooLinksEmptyEl) ooLinksEmptyEl.hidden = true; if (ooLinksTableWrapEl) ooLinksTableWrapEl.hidden = false; }

  function renderOrg(o) {
    setField("name", o.name);
    setField("siglas", o.siglas);
    setField("alcunhas", o.alcunhas);
    setField("org_type", o.org_type ? (ORG_TYPE_LABELS[o.org_type] || o.org_type) : null);
    setField("area_atuacao", o.area_atuacao);
    setField("source", o.source);
    setField("reliability_level", RELIABILITY_LABELS[o.reliability_level] || o.reliability_level);
    setField("notes", o.notes);
    setField("created_at", formatDateTime(o.created_at));
    setField("updated_at", formatDateTime(o.updated_at));
    var badgeSlot = contentEl.querySelector('[data-field="status_badge"]');
    if (badgeSlot) {
      var cls = o.status === "active" ? "badge badge--ativo" : "badge badge--arquivado";
      var txt = o.status === "active" ? "[ATIVO]" : "[ARQUIVADO]";
      badgeSlot.innerHTML = '<span class="' + cls + '">' + txt + "</span>";
    }
    if (archivedNoteEl) archivedNoteEl.hidden = (o.status !== "archived");
    if (editBtnEl) editBtnEl.onclick = function () { window.location.href = "/organizations?edit=" + o.id; };
    showContent();
    loadLinks();
    loadOrgOrgLinks();
  }

  function loadOrg() {
    showLoading();
    fetch(API_ORG + "/" + orgId, { credentials: "same-origin" })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (r.status === 404) { showNotFound(); return null; }
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) { if (data) renderOrg(data); })
      .catch(function () { showNotFound(); });
  }

  // --- Membros vinculados ---
  function loadLinks() {
    linksShowLoading();
    fetch(API_LINKS + "?org_id=" + orgId, { credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) { if (data === null) return; renderLinksTable(data); })
      .catch(function () { linksShowEmpty(); });
  }

  function renderLinksTable(links) {
    if (!linksTbodyEl) return;
    if (!links || links.length === 0) { linksShowEmpty(); return; }
    linksTbodyEl.innerHTML = "";
    links.forEach(function (lk) {
      var tr = document.createElement("tr");
      tr.style.borderBottom = "var(--border-width-base) solid var(--border-subtle)";
      tr.innerHTML =
        '<td style="padding:var(--space-2) var(--space-3);font-weight:500;">' + escapeHtml(lk.person_name || "id " + lk.person_id) + "</td>" +
        '<td style="padding:var(--space-2) var(--space-3);font-family:var(--font-mono);font-size:var(--font-size-xs);color:var(--text-secondary);">' + escapeHtml(LINK_TYPE_LABELS[lk.link_type] || lk.link_type) + "</td>" +
        '<td style="padding:var(--space-2) var(--space-3);font-family:var(--font-mono);font-size:var(--font-size-xs);color:var(--text-secondary);">' + escapeHtml(lk.position || "--") + "</td>" +
        '<td style="padding:var(--space-2) var(--space-3);font-family:var(--font-mono);font-size:var(--font-size-xs);color:var(--text-secondary);">' + escapeHtml(RELIABILITY_LABELS[lk.reliability_level] || lk.reliability_level) + "</td>" +
        '<td style="padding:var(--space-2) var(--space-3);"><button type="button" class="btn btn--text" style="font-size:var(--font-size-xs);color:var(--text-tertiary);" data-remove-link="' + lk.id + '">Remover</button></td>';
      tr.querySelector("[data-remove-link]").addEventListener("click", function () { removeLink(lk.id, tr); });
      linksTbodyEl.appendChild(tr);
    });
    linksShowTable();
  }

  function removeLink(linkId, rowEl) {
    if (!confirm("Remover este vinculo?")) return;
    fetch(API_LINKS + "/" + linkId, { method: "DELETE", credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) {
        if (!data) return;
        if (rowEl && rowEl.parentNode) rowEl.parentNode.removeChild(rowEl);
        if (linksTbodyEl && linksTbodyEl.rows.length === 0) linksShowEmpty();
        toast("success", "Vinculo removido", "");
      })
      .catch(function () { toast("error", "Erro", "Nao foi possivel remover."); });
  }

  function modalOpen() {
    if (!modalBackdropEl) return;
    loadPersonsIntoSelect();
    if (vpLinkType) vpLinkType.value = "";
    if (vpPosition) vpPosition.value = "";
    if (vpSource) vpSource.value = "";
    if (vpReliability) vpReliability.value = "pending";
    modalBackdropEl.setAttribute("data-open", "true");
  }

  function modalClose() { if (modalBackdropEl) modalBackdropEl.setAttribute("data-open", "false"); }

  function loadPersonsIntoSelect() {
    if (!vpPersonSelect) return;
    if (vpPersonHint) { vpPersonHint.hidden = false; vpPersonHint.textContent = "Carregando..."; }
    vpPersonSelect.innerHTML = '<option value="">- selecione -</option>';
    fetch(API_PERSONS + "?include_archived=false&sort_by=full_name", { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (persons) {
        if (vpPersonHint) vpPersonHint.hidden = true;
        persons.forEach(function (p) {
          var opt = document.createElement("option");
          opt.value = String(p.id);
          opt.textContent = p.full_name;
          vpPersonSelect.appendChild(opt);
        });
      })
      .catch(function () { if (vpPersonHint) { vpPersonHint.hidden = false; vpPersonHint.textContent = "Erro."; } });
  }

  function submitVincular() {
    var personId    = vpPersonSelect ? vpPersonSelect.value : "";
    var linkType    = vpLinkType     ? vpLinkType.value     : "";
    var position    = vpPosition     ? vpPosition.value.trim() : "";
    var source      = vpSource       ? vpSource.value.trim()   : "";
    var reliability = vpReliability  ? vpReliability.value     : "pending";
    if (!personId)  { toast("error", "Obrigatorio", "Selecione uma pessoa."); return; }
    if (!linkType)  { toast("error", "Obrigatorio", "Selecione o tipo de vinculo."); return; }
    if (!source)    { toast("error", "Obrigatorio", "Informe a fonte."); return; }
    if (modalConfirmarEl) modalConfirmarEl.disabled = true;
    var body = { person_id: parseInt(personId, 10), org_id: orgId, link_type: linkType, source: source, reliability_level: reliability };
    if (position) body.position = position;
    fetch(API_LINKS, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (r.status === 409) { return r.json().then(function (e) { toast("error", "Duplicado", (e && e.detail && e.detail.message) || "Vinculo ja existe."); return null; }); }
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        modalClose();
        toast("success", "Vinculo criado", "");
        loadLinks();
      })
      .catch(function () { toast("error", "Erro", "Nao foi possivel criar."); })
      .finally(function () { if (modalConfirmarEl) modalConfirmarEl.disabled = false; });
  }

  // --- Relacoes org-org ---
  function loadOrgOrgLinks() {
    ooShowLoading();
    fetch(ORG_ORG_API + "?org_id=" + orgId, { credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) { if (data === null) return; renderOrgOrgTable(data); })
      .catch(function () { ooShowEmpty(); });
  }

  function renderOrgOrgTable(links) {
    if (!ooLinksTbodyEl) return;
    if (!links || links.length === 0) { ooShowEmpty(); return; }
    ooLinksTbodyEl.innerHTML = "";
    links.forEach(function (lk) {
      var otherName = lk.org_a_id === orgId ? (lk.org_b_name || "id " + lk.org_b_id) : (lk.org_a_name || "id " + lk.org_a_id);
      var tr = document.createElement("tr");
      tr.style.borderBottom = "var(--border-width-base) solid var(--border-subtle)";
      tr.innerHTML =
        '<td style="padding:var(--space-2) var(--space-3);font-weight:500;">' + escapeHtml(otherName) + "</td>" +
        '<td style="padding:var(--space-2) var(--space-3);font-family:var(--font-mono);font-size:var(--font-size-xs);color:var(--text-secondary);">' + escapeHtml(RELATION_LABELS[lk.relation_type] || lk.relation_type) + "</td>" +
        '<td style="padding:var(--space-2) var(--space-3);font-family:var(--font-mono);font-size:var(--font-size-xs);color:var(--text-secondary);">' + escapeHtml(RELIABILITY_LABELS[lk.reliability_level] || lk.reliability_level) + "</td>" +
        '<td style="padding:var(--space-2) var(--space-3);"><button type="button" class="btn btn--text" style="font-size:var(--font-size-xs);color:var(--text-tertiary);" data-remove-oo="' + lk.id + '">Remover</button></td>';
      tr.querySelector("[data-remove-oo]").addEventListener("click", function () { removeOrgOrgLink(lk.id, tr); });
      ooLinksTbodyEl.appendChild(tr);
    });
    ooShowTable();
  }

  function removeOrgOrgLink(linkId, rowEl) {
    if (!confirm("Remover esta relacao?")) return;
    fetch(ORG_ORG_API + "/" + linkId, { method: "DELETE", credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) {
        if (!data) return;
        if (rowEl && rowEl.parentNode) rowEl.parentNode.removeChild(rowEl);
        if (ooLinksTbodyEl && ooLinksTbodyEl.rows.length === 0) ooShowEmpty();
        toast("success", "Relacao removida", "");
      })
      .catch(function () { toast("error", "Erro", "Nao foi possivel remover."); });
  }

  function ooModalOpen() {
    if (!ooModalEl) return;
    loadOtherOrgsIntoSelect();
    if (ooRelationType) ooRelationType.value = "";
    if (ooSource) ooSource.value = "";
    if (ooReliability) ooReliability.value = "pending";
    ooModalEl.setAttribute("data-open", "true");
  }

  function ooModalClose() { if (ooModalEl) ooModalEl.setAttribute("data-open", "false"); }

  function loadOtherOrgsIntoSelect() {
    if (!ooOrgSelect) return;
    if (ooOrgHint) { ooOrgHint.hidden = false; ooOrgHint.textContent = "Carregando..."; }
    ooOrgSelect.innerHTML = '<option value="">- selecione -</option>';
    fetch(API_ORG + "?include_archived=false&sort_by=name", { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (orgs) {
        if (ooOrgHint) ooOrgHint.hidden = true;
        orgs.forEach(function (o) {
          if (o.id === orgId) return;
          var opt = document.createElement("option");
          opt.value = String(o.id);
          opt.textContent = o.name + (o.siglas ? " (" + o.siglas + ")" : "");
          ooOrgSelect.appendChild(opt);
        });
      })
      .catch(function () { if (ooOrgHint) { ooOrgHint.hidden = false; ooOrgHint.textContent = "Erro."; } });
  }

  function submitOrgOrgLink() {
    var otherOrgId   = ooOrgSelect    ? ooOrgSelect.value    : "";
    var relationType = ooRelationType ? ooRelationType.value  : "";
    var source       = ooSource       ? ooSource.value.trim() : "";
    var reliability  = ooReliability  ? ooReliability.value   : "pending";
    if (!otherOrgId)   { toast("error", "Obrigatorio", "Selecione uma organizacao."); return; }
    if (!relationType) { toast("error", "Obrigatorio", "Selecione o tipo de relacao."); return; }
    if (!source)       { toast("error", "Obrigatorio", "Informe a fonte."); return; }
    if (ooModalConfirmarEl) ooModalConfirmarEl.disabled = true;
    var body = { org_a_id: orgId, org_b_id: parseInt(otherOrgId, 10), relation_type: relationType, source: source, reliability_level: reliability };
    fetch(ORG_ORG_API, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    })
      .then(function (r) { if (handleAuthLapse(r)) return null; if (!r.ok) throw new Error(); return r.json(); })
      .then(function (data) {
        if (!data) return;
        ooModalClose();
        toast("success", "Relacao registrada", "");
        loadOrgOrgLinks();
      })
      .catch(function () { toast("error", "Erro", "Nao foi possivel registrar."); })
      .finally(function () { if (ooModalConfirmarEl) ooModalConfirmarEl.disabled = false; });
  }

  function parseOrgIdFromPath() {
    var m = window.location.pathname.match(/\/organizations\/(\d+)\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  function setup() {
    loadingEl = document.getElementById("org-detail-loading");
    contentEl = document.getElementById("org-detail-content");
    if (!loadingEl || !contentEl) return;

    notFoundEl       = document.getElementById("org-detail-notfound");
    archivedNoteEl   = document.getElementById("org-detail-archived-note");
    editBtnEl        = document.getElementById("org-detail-edit");

    linksLoadingEl   = document.getElementById("links-loading");
    linksEmptyEl     = document.getElementById("links-empty");
    linksTableWrapEl = document.getElementById("links-table-wrap");
    linksTbodyEl     = document.getElementById("links-tbody");
    btnVincularEl    = document.getElementById("btn-vincular-pessoa");
    modalBackdropEl  = document.getElementById("modal-vincular-backdrop");
    modalCancelEl    = document.getElementById("modal-vincular-cancel");
    modalConfirmarEl = document.getElementById("modal-vincular-confirmar");
    vpPersonSelect   = document.getElementById("vp-person-select");
    vpPersonHint     = document.getElementById("vp-person-hint");
    vpLinkType       = document.getElementById("vp-link-type");
    vpPosition       = document.getElementById("vp-position");
    vpSource         = document.getElementById("vp-source");
    vpReliability    = document.getElementById("vp-reliability");

    ooLinksLoadingEl   = document.getElementById("org-org-links-loading");
    ooLinksEmptyEl     = document.getElementById("org-org-links-empty");
    ooLinksTableWrapEl = document.getElementById("org-org-links-table-wrap");
    ooLinksTbodyEl     = document.getElementById("org-org-links-tbody");
    btnVincularOrgOrgEl = document.getElementById("btn-vincular-org-org");
    ooModalEl          = document.getElementById("modal-org-org-backdrop");
    ooModalCancelEl    = document.getElementById("modal-org-org-cancel");
    ooModalConfirmarEl = document.getElementById("modal-org-org-confirmar");
    ooOrgSelect        = document.getElementById("oo-org-select");
    ooOrgHint          = document.getElementById("oo-org-hint");
    ooRelationType     = document.getElementById("oo-relation-type");
    ooSource           = document.getElementById("oo-source");
    ooReliability      = document.getElementById("oo-reliability");

    if (btnVincularEl)       btnVincularEl.addEventListener("click", modalOpen);
    if (modalCancelEl)       modalCancelEl.addEventListener("click", modalClose);
    if (modalConfirmarEl)    modalConfirmarEl.addEventListener("click", submitVincular);
    if (modalBackdropEl)     modalBackdropEl.addEventListener("click", function (e) { if (e.target === modalBackdropEl) modalClose(); });

    if (btnVincularOrgOrgEl) btnVincularOrgOrgEl.addEventListener("click", ooModalOpen);
    if (ooModalCancelEl)     ooModalCancelEl.addEventListener("click", ooModalClose);
    if (ooModalConfirmarEl)  ooModalConfirmarEl.addEventListener("click", submitOrgOrgLink);
    if (ooModalEl)           ooModalEl.addEventListener("click", function (e) { if (e.target === ooModalEl) ooModalClose(); });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (ooModalEl && ooModalEl.getAttribute("data-open") === "true") { ooModalClose(); return; }
        if (modalBackdropEl && modalBackdropEl.getAttribute("data-open") === "true") { modalClose(); return; }
        window.location.href = "/organizations";
      }
    });

    orgId = parseOrgIdFromPath();
    if (!orgId || isNaN(orgId)) { showNotFound(); return; }
    loadOrg();
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", setup); } else { setup(); }
})();