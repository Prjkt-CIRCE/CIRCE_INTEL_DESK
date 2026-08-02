/* ============================================================
   CIRCE Intel Desk — org_detail.js
   Tela de detalhe de Organização (RF-004) — Sprint 01-B, B5.
   SPA-leve: busca GET /api/organizations/{id} e popula slots.
   ============================================================ */

(function () {
  "use strict";

  var API_BASE = "/api/organizations";

  var loadingEl, notFoundEl, contentEl, archivedNoteEl, editBtnEl;
  var linksLoadingEl, linksEmptyEl, linksTableWrapEl, linksTbodyEl;
  var modalBackdropEl, modalCloseEl;
  var btnVincularEl;
  var orgId = null;

  var ORG_TYPE_LABELS = {
    "faccao_prisional": "Facção prisional",
    "milicia": "Milícia",
    "orcrim_trafico": "ORCRIM tráfico",
    "orcrim_patrimonial": "ORCRIM patrimonial",
    "outra": "Outra"
  };

  var RELIABILITY_LABELS = {
    "pending":  "Pendente",
    "baixo":    "Baixo",
    "medio":    "Médio",
    "alto":     "Alto",
    "validado": "Validado"
  };

  function handleAuthLapse(r) {
    var isHtml = r.redirected || (r.headers.get("content-type") || "").indexOf("text/html") >= 0;
    if (r.status === 401 || isHtml) {
      window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
      return true;
    }
    return false;
  }

  function toast(type, title, msg) {
    if (window.CIRCE && window.CIRCE.toast) window.CIRCE.toast[type](title, msg);
  }

  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  var MESES = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"];
  function formatDateTime(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
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

    if (editBtnEl) {
      editBtnEl.onclick = function () {
        window.location.href = "/organizations?edit=" + o.id;
      };
    }

    showContent();
    linksShowEmpty(); // placeholder até B6
  }

  function linksShowLoading() { if (linksLoadingEl) linksLoadingEl.hidden = false; if (linksEmptyEl) linksEmptyEl.hidden = true; if (linksTableWrapEl) linksTableWrapEl.hidden = true; }
  function linksShowEmpty()   { if (linksLoadingEl) linksLoadingEl.hidden = true; if (linksEmptyEl) linksEmptyEl.hidden = false; if (linksTableWrapEl) linksTableWrapEl.hidden = true; }

  function loadOrg() {
    showLoading();
    fetch(API_BASE + "/" + orgId, { credentials: "same-origin" })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (r.status === 404) { showNotFound(); return null; }
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (data === null) return;
        renderOrg(data);
      })
      .catch(function (err) {
        console.error("[org_detail] erro", err);
        showNotFound();
      });
  }

  function parseOrgIdFromPath() {
    var m = window.location.pathname.match(/\/organizations\/(\d+)\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  function setup() {
    loadingEl = document.getElementById("org-detail-loading");
    contentEl = document.getElementById("org-detail-content");
    if (!loadingEl || !contentEl) return;

    notFoundEl     = document.getElementById("org-detail-notfound");
    archivedNoteEl = document.getElementById("org-detail-archived-note");
    editBtnEl      = document.getElementById("org-detail-edit");
    linksLoadingEl = document.getElementById("links-loading");
    linksEmptyEl   = document.getElementById("links-empty");
    linksTableWrapEl = document.getElementById("links-table-wrap");
    linksTbodyEl   = document.getElementById("links-tbody");
    btnVincularEl  = document.getElementById("btn-vincular-pessoa");
    modalBackdropEl = document.getElementById("modal-vincular-backdrop");
    modalCloseEl   = document.getElementById("modal-vincular-close");

    if (modalCloseEl) modalCloseEl.addEventListener("click", function () {
      if (modalBackdropEl) modalBackdropEl.setAttribute("data-open", "false");
    });
    if (btnVincularEl) btnVincularEl.addEventListener("click", function () {
      if (modalBackdropEl) modalBackdropEl.setAttribute("data-open", "true");
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (modalBackdropEl && modalBackdropEl.getAttribute("data-open") === "true") {
          modalBackdropEl.setAttribute("data-open", "false");
        } else {
          window.location.href = "/organizations";
        }
      }
    });

    orgId = parseOrgIdFromPath();
    if (!orgId || isNaN(orgId)) { showNotFound(); return; }
    loadOrg();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();