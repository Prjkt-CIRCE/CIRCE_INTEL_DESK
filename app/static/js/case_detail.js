/* ============================================================
   CIRCE Intel Desk — case_detail.js
   Tela de detalhe de um caso (RF-001) — Sprint 01, Bloco 8, Sub-passo 8.6.
   Vínculos pessoa-caso (RF-003) — Sprint 01, Bloco 10, Sub-passo 10.5.

   Decisões do operador no 8.6 (preservadas):
     - (a) Renderização SPA-leve: busca GET /api/cases/{id} e popula slots.
     - (b/D56) "Editar" navega para /cases?edit={id}.
     - (c) "Reativar" fora do escopo (D48).
     - (d) Voltar: link "< CASOS" + atalho Esc.

   Adições do 10.5 (RF-003):
     - loadLinks(): GET /api/links/person-case?case_id=N, renderiza tabela.
     - renderLinksTable(): popula #links-tbody; alterna empty/loading/table.
     - Modal #modal-vincular-pessoa: carrega <select> de pessoas ativas
       (D-B10-01: Opção A no MVP-0; migra para typeahead com RF-010).
     - submitVincular(): POST /api/links/person-case; trata 409 (CA-003.6).
     - removeLink(linkId): DELETE /api/links/person-case/{id} após confirm().
     - Rótulos legíveis para role_in_case e reliability_level.

   Nota de dívida (replicada do 8.6-b): formatDate e statusBadgeHtml
   ainda são replicados de cases.js. Extração para util compartilhado
   pendente — aguarda RF-010 ou 3º consumidor (D56 / §12 do ESTADO).
   ============================================================ */

(function () {
  "use strict";

  var API_CASES  = "/api/cases";
  var API_LINKS  = "/api/links/person-case";
  var API_PERSONS = "/api/persons";

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

  // ---------- DOM refs — caso ----------
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
  // Padrão canônico da casa: modalBackdropEl[data-open="true/false"] controla visibilidade.
  // A caixa de conteúdo (.card) é filha do backdrop; não precisa de ref própria.
  var modalBackdropEl   = null;
  var modalCloseEl      = null;
  var modalCancelEl     = null;
  var modalConfirmarEl  = null;
  var vpPersonSelect    = null;
  var vpPersonHint      = null;
  var vpRoleSelect      = null;
  var vpSourceInput     = null;
  var vpReliabilitySelect = null;
  var vpNotesInput      = null;

  var caseId = null;

  // ---------- Utilitários de data (replicados de cases.js — ver nota de dívida) ----------
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

  // ---------- Badge de status (replicado de cases.js — ver nota de dívida) ----------
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

  // ---------- Slots de campo do caso ----------
  function setField(field, value) {
    if (!contentEl) return;
    var el = contentEl.querySelector('[data-field="' + field + '"]');
    if (!el) return;
    var txt = (value === null || value === undefined || value === "") ? "—" : String(value);
    el.textContent = txt;
  }

  // ---------- Estados da tela principal ----------
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

  // ---------- Renderizar caso ----------
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

    if (archivedNoteEl) archivedNoteEl.hidden = (c.status !== "archived");

    if (editBtnEl) {
      editBtnEl.onclick = function () {
        window.location.href = "/cases?edit=" + encodeURIComponent(c.id);
      };
    }

    showContent();
  }

  // ---------- Carregar caso ----------
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
        loadLinks(); // carrega vínculos após renderizar o caso
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao carregar caso", err);
        showNotFound();
        toast("error", "Erro", "Não foi possível carregar o caso.");
      });
  }

  // ================================================================
  // VÍNCULOS — RF-003, Bloco 10.5
  // ================================================================

  // ---------- Estados da seção de vínculos ----------
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

  // ---------- Renderizar tabela de vínculos ----------
  function renderLinksTable(links) {
    if (!linksTbodyEl) return;

    if (!links || links.length === 0) {
      linksShowEmpty();
      return;
    }

    // Constrói as linhas da tabela
    var rows = links.map(function (lk) {
      var roleLabel        = ROLE_LABELS[lk.role_in_case] || lk.role_in_case || "—";
      var reliabilityLabel = RELIABILITY_LABELS[lk.reliability_level] || lk.reliability_level || "—";
      var personName       = lk.person_name || ("id " + lk.person_id);
      var source           = lk.source || "—";
      var linkId           = lk.id;

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
        "</td>" +
        '<td style="padding: var(--space-2) 0 var(--space-2) var(--space-3); white-space: nowrap;">' +
          '<button type="button" class="btn btn--text" style="font-size: 0.8rem; color: var(--text-tertiary);" data-remove-link="' + linkId + '">Remover</button>' +
        "</td>";

      // Botão de remoção
      tr.querySelector('[data-remove-link]').addEventListener("click", function () {
        removeLink(linkId, tr);
      });

      return tr;
    });

    // Limpa e repopula tbody
    linksTbodyEl.innerHTML = "";
    rows.forEach(function (tr) { linksTbodyEl.appendChild(tr); });

    linksShowTable();
  }

  // ---------- Escape de HTML para evitar XSS nas células ----------
  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ---------- Carregar vínculos ----------
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
        console.error("[case_detail] erro ao carregar vínculos", err);
        linksShowEmpty(); // fallback: mostra vazio em vez de travar
        toast("error", "Erro", "Não foi possível carregar os vínculos.");
      });
  }

  // ---------- Remover vínculo (CA-003.7) ----------
  function removeLink(linkId, rowEl) {
    if (!confirm("Remover este vínculo? A ação será registrada no log de auditoria.")) return;

    fetch(API_LINKS + "/" + encodeURIComponent(linkId), {
      method: "DELETE",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 404) {
          toast("error", "Erro", "Vínculo não encontrado.");
          return null;
        }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        // Remove a linha da tabela; se ficar vazia, mostra estado vazio
        if (rowEl && rowEl.parentNode) rowEl.parentNode.removeChild(rowEl);
        if (linksTbodyEl && linksTbodyEl.rows.length === 0) linksShowEmpty();
        toast("success", "Vínculo removido", "O vínculo foi removido com sucesso.");
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao remover vínculo", err);
        toast("error", "Erro", "Não foi possível remover o vínculo.");
      });
  }

  // ================================================================
  // MODAL — Vincular pessoa (D-B10-01: <select> no MVP-0)
  // ================================================================

  function modalOpen() {
    if (!modalBackdropEl) return;
    modalBackdropEl.setAttribute("data-open", "true");
    // Carrega lista de pessoas ativas no <select> (D-B10-01)
    loadPersonsIntoSelect();
    // Reset dos campos
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

  // Carrega pessoas ativas no <select> do modal (GET /api/persons)
  function loadPersonsIntoSelect() {
    if (!vpPersonSelect) return;

    // Mostra hint de carregamento
    if (vpPersonHint) {
      vpPersonHint.hidden = false;
      vpPersonHint.textContent = "Carregando pessoas…";
    }

    // Limpa opções anteriores (mantém a placeholder)
    vpPersonSelect.innerHTML = '<option value="">— selecione —</option>';

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
          opt.value = "";
          opt.disabled = true;
          opt.textContent = "Nenhuma pessoa cadastrada";
          vpPersonSelect.appendChild(opt);
          return;
        }

        persons.forEach(function (p) {
          var opt = document.createElement("option");
          opt.value = String(p.id);
          opt.textContent = p.full_name + (p.cpf ? " — " + formatCpf(p.cpf) : "");
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

  // Formata CPF para exibição no <select> (000.000.000-00)
  function formatCpf(cpf) {
    if (!cpf) return "";
    var d = String(cpf).replace(/\D/g, "");
    if (d.length !== 11) return cpf;
    return d.slice(0,3) + "." + d.slice(3,6) + "." + d.slice(6,9) + "-" + d.slice(9,11);
  }

  // ---------- Submeter criação de vínculo ----------
  function submitVincular() {
    var personId     = vpPersonSelect    ? vpPersonSelect.value    : "";
    var roleInCase   = vpRoleSelect      ? vpRoleSelect.value      : "";
    var source       = vpSourceInput     ? vpSourceInput.value.trim() : "";
    var reliability  = vpReliabilitySelect ? vpReliabilitySelect.value : "pending";
    var notes        = vpNotesInput      ? vpNotesInput.value.trim() : "";

    // Validação inline (CA-003.3, CA-003.4, CA-003.5)
    if (!personId) {
      toast("error", "Campo obrigatório", "Selecione uma pessoa.");
      return;
    }
    if (!roleInCase) {
      toast("error", "Campo obrigatório", "Selecione o tipo de participação.");
      return;
    }
    if (!source) {
      toast("error", "Campo obrigatório", "Informe a fonte da informação.");
      return;
    }

    // Desabilita botão durante a requisição
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
      headers: {
        "Accept":       "application/json",
        "Content-Type": "application/json"
      },
      credentials: "same-origin",
      body: JSON.stringify(body)
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 409) {
          // CA-003.6: vínculo duplicado
          return response.json().then(function (err) {
            var msg = (err && err.detail && err.detail.message)
              ? err.detail.message
              : "Já existe um vínculo ativo com este papel para esta pessoa neste caso.";
            toast("error", "Vínculo duplicado", msg);
            return null;
          });
        }
        if (response.status === 404) {
          toast("error", "Erro", "Caso ou pessoa não encontrados.");
          return null;
        }
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        modalClose();
        toast("success", "Vínculo criado", "Pessoa vinculada ao caso com sucesso.");
        loadLinks(); // recarrega a tabela
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao criar vínculo", err);
        toast("error", "Erro", "Não foi possível criar o vínculo.");
      })
      .finally(function () {
        if (modalConfirmarEl) modalConfirmarEl.disabled = false;
      });
  }

  // ---------- Extrai id numérico da URL /cases/{id} ----------
  function parseCaseIdFromPath() {
    var m = window.location.pathname.match(/\/cases\/(\d+)\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  // ---------- Inicialização ----------
  function setup() {
    contentEl = document.getElementById("case-detail-content");
    loadingEl = document.getElementById("case-detail-loading");
    if (!contentEl || !loadingEl) return; // não é a tela de detalhe

    notFoundEl     = document.getElementById("case-detail-notfound");
    archivedNoteEl = document.getElementById("case-detail-archived-note");
    editBtnEl      = document.getElementById("case-detail-edit");

    // Refs de vínculos
    linksLoadingEl   = document.getElementById("links-loading");
    linksEmptyEl     = document.getElementById("links-empty");
    linksTableWrapEl = document.getElementById("links-table-wrap");
    linksTbodyEl     = document.getElementById("links-tbody");
    btnVincularEl    = document.getElementById("btn-vincular-pessoa");

    // Refs do modal (padrão canônico: backdrop é o container, modal é a caixa)
    modalBackdropEl      = document.getElementById("modal-vincular-backdrop");
    modalCloseEl         = document.getElementById("modal-vincular-close");
    modalCancelEl        = document.getElementById("modal-vincular-cancel");
    modalConfirmarEl     = document.getElementById("modal-vincular-confirmar");
    vpPersonSelect       = document.getElementById("vp-person-select");
    vpPersonHint         = document.getElementById("vp-person-hint");
    vpRoleSelect         = document.getElementById("vp-role-select");
    vpSourceInput        = document.getElementById("vp-source-input");
    vpReliabilitySelect  = document.getElementById("vp-reliability-select");
    vpNotesInput         = document.getElementById("vp-notes-input");

    caseId = parseCaseIdFromPath();
    if (caseId === null || isNaN(caseId)) { showNotFound(); return; }

    // Atalho Esc (decisão (d) do 8.6)
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (modalBackdropEl && modalBackdropEl.getAttribute("data-open") === "true") {
          // Se o modal estiver aberto, Esc fecha o modal (não volta para lista)
          modalClose();
        } else {
          e.preventDefault();
          window.location.href = "/cases";
        }
      }
    });

    // Botão "Vincular pessoa"
    if (btnVincularEl) btnVincularEl.addEventListener("click", modalOpen);

    // Fechar modal
    if (modalCloseEl)  modalCloseEl.addEventListener("click", modalClose);
    if (modalCancelEl) modalCancelEl.addEventListener("click", modalClose);
    // Clique no backdrop (fora da caixa .modal) fecha — clique dentro da caixa não fecha
    if (modalBackdropEl) {
      modalBackdropEl.addEventListener("click", function (e) {
        if (e.target === modalBackdropEl) modalClose();
      });
    }

    // Confirmar vínculo
    if (modalConfirmarEl) modalConfirmarEl.addEventListener("click", submitVincular);

    loadCase();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
