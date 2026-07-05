/* ============================================================
   CIRCE Intel Desk — person_detail.js
   Tela de detalhe de uma pessoa (RF-002) — Sprint 01, Bloco 9, Sub-passo 9.6.

   Decisões do operador no 9.6 (espelho do case_detail.js / Bloco 8.6):
     - (a) Renderização SPA-leve: a rota /persons/{id} serve só o
       esqueleto (detail.html); este script busca GET /api/persons/{id}
       e popula os slots [data-field]. Trata 3 estados: carregando,
       não-encontrado (404), conteúdo.
     - (b/D58) "Editar" NÃO abre modal aqui: navega para
       /persons?edit={id}; a lista (persons.js) abre o modal de
       edição já na pessoa certa. Espelho de D56 de Casos.
     - (c) Reativar pessoa arquivada: FORA do 9.6 (D48 por analogia).
       Em pessoa arquivada, apenas exibimos #person-detail-archived-note.
     - (d) Voltar: link "< PESSOAS" (href no HTML) + atalho Esc (aqui).

   Contrato da API (confirmado no 9.4, esquema validado no 9.6):
     GET /api/persons/{person_id:int} -> PersonResponse | 404.
     Campos: id, full_name, aliases, cpf, rg, birth_date,
     mother_name, father_name, notes, source, reliability_level,
     status, created_at, created_by, updated_at, updated_by.

   NOTA DE DÍVIDA (confirmada no 9.6, idêntica à do case_detail.js):
   formatDateTime, formatDateOnly, formatCpfDisplay, formatAliasesDisplay
   e statusBadgeHtml são REPLICADOS de persons.js / case_detail.js, não
   compartilhados. Extração para utils comum é pendência para quando
   RF-003 ou RF-005 pedir o mesmo padrão — aí a extração se paga.
   Replicar agora evita mexer em código fechado/validado.
   ============================================================ */

(function () {
  "use strict";

  var API_BASE = "/api/persons";

  // ---------- DOM refs ----------
  var loadingEl = null;
  var notFoundEl = null;
  var contentEl = null;
  var archivedNoteEl = null;
  var editBtnEl = null;
  var backLinkEl = null;

  // id da pessoa (extraído da URL /persons/{id}).
  var personId = null;

  // ---------- Utilitários de data (REPLICADOS de persons.js — ver nota de dívida) ----------
  var MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
               "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  // Carimbo completo DD.MMM.AAAA HH:MM — usado em created_at/updated_at.
  function formatDateTime(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  // birth_date é Optional[str] e representa uma DATA (não um carimbo
  // de sistema). Pode chegar como "YYYY-MM-DD" (sem hora) ou ISO
  // completo. Para não exibir um falso "00:00", mostramos só a parte
  // de data quando não há componente de hora detectável.
  // Mesma lógica de formatDateOnly do case_detail.js (fact_date).
  function formatDateOnly(value) {
    if (!value) return "—";
    var s = String(value);
    var dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(s);
    var d = new Date(s);
    if (isNaN(d.getTime())) return s;
    if (dateOnly) {
      // Data pura: usar componentes UTC para evitar recuo de 1 dia
      // (JS interpreta "YYYY-MM-DD" como meia-noite UTC).
      return pad2(d.getUTCDate()) + "." + MESES[d.getUTCMonth()] + "." + d.getUTCFullYear();
    }
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  // CA-002.2: CPF vem normalizado (só dígitos) da API.
  // Aplica máscara 000.000.000-00 SÓ para exibição.
  // REPLICADO de persons.js — ver nota de dívida.
  function formatCpfDisplay(cpf) {
    if (!cpf) return "—";
    if (/^\d{11}$/.test(cpf)) {
      return cpf.slice(0, 3) + "." + cpf.slice(3, 6) + "." + cpf.slice(6, 9) + "-" + cpf.slice(9);
    }
    return cpf; // não tem 11 dígitos: mostra cru
  }

  // CA-002.3: aliases ";"-separado → lista com " · " como separador.
  // REPLICADO de persons.js — ver nota de dívida.
  function formatAliasesDisplay(aliases) {
    if (!aliases) return "—";
    var parts = aliases.split(";").map(function (s) { return s.trim(); }).filter(Boolean);
    return parts.length ? parts.join(" · ") : "—";
  }

  // ---------- Badge de status (REPLICADO de persons.js — ver nota de dívida) ----------
  function statusBadgeHtml(status) {
    var map = {
      "active":   { cls: "badge--ativo",     txt: "[ATIVO]" },
      "archived": { cls: "badge--arquivado", txt: "[ARQUIVADO]" }
    };
    var entry = map[status] || { cls: "badge--arquivado", txt: "[" + String(status).toUpperCase() + "]" };
    return '<span class="badge ' + entry.cls + '">' + entry.txt + "</span>";
  }

  // ---------- Guarda de sessão expirada (D54 — idêntico ao case_detail.js) ----------
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

  // ---------- Helpers de preenchimento ----------
  function setField(field, value) {
    if (!contentEl) return;
    var el = contentEl.querySelector('[data-field="' + field + '"]');
    if (!el) return;
    var txt = (value === null || value === undefined || value === "")
      ? "—" : String(value);
    el.textContent = txt;
  }

  // ---------- Troca de estado da tela ----------
  function showLoading() {
    if (loadingEl) loadingEl.hidden = false;
    if (notFoundEl) notFoundEl.hidden = true;
    if (contentEl) contentEl.hidden = true;
  }

  function showNotFound() {
    if (loadingEl) loadingEl.hidden = true;
    if (notFoundEl) notFoundEl.hidden = false;
    if (contentEl) contentEl.hidden = true;
  }

  function showContent() {
    if (loadingEl) loadingEl.hidden = true;
    if (notFoundEl) notFoundEl.hidden = true;
    if (contentEl) contentEl.hidden = false;
  }

  // ---------- Popular a tela com a pessoa ----------
  function renderPerson(p) {
    // Header: nome + badge de status.
    setField("full_name", p.full_name);

    var badgeSlot = contentEl ? contentEl.querySelector('[data-field="status_badge"]') : null;
    if (badgeSlot) badgeSlot.innerHTML = statusBadgeHtml(p.status);

    // Strip de metadados no header.
    setField("aliases_display", formatAliasesDisplay(p.aliases));
    setField("created_at", formatDateTime(p.created_at));

    // ─── DADOS PESSOAIS ───
    // full_name_detail replica o nome na seção — evita depender
    // só do header que pode estar fora do contentEl em alguns layouts.
    setField("full_name_detail", p.full_name);
    setField("aliases_detail", formatAliasesDisplay(p.aliases));
    setField("cpf_display", formatCpfDisplay(p.cpf));
    setField("rg", p.rg);
    setField("birth_date", formatDateOnly(p.birth_date));
    setField("mother_name", p.mother_name);
    setField("father_name", p.father_name);

    // ─── FONTE ───
    setField("source", p.source);
    var reliabilityMap = {
      "pending":  "Pendente",
      "low":      "Baixo",
      "medium":   "Médio",
      "high":     "Alto",
      "validated": "Validado"
    };
    var reliabilityLabel = reliabilityMap[p.reliability_level] || p.reliability_level || "—";
    setField("reliability_level", reliabilityLabel);

    // ─── NOTAS ───
    setField("notes", p.notes);

    // ─── AUDITORIA ───
    setField("created_at_full", formatDateTime(p.created_at));
    setField("created_by", p.created_by);
    setField("updated_at", formatDateTime(p.updated_at));
    setField("updated_by", p.updated_by);

    // Nota de pessoa arquivada (decisão (c) + D48 por analogia).
    if (archivedNoteEl) archivedNoteEl.hidden = (p.status !== "archived");

    // Botão "Editar" (decisão (b)/D58): leva à lista com o modal aberto.
    if (editBtnEl) {
      editBtnEl.onclick = function () {
        window.location.href = "/persons?edit=" + encodeURIComponent(p.id);
      };
    }

    showContent();
  }

  // ---------- Buscar a pessoa ----------
  function loadPerson() {
    showLoading();

    fetch(API_BASE + "/" + encodeURIComponent(personId), {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 404) {
          showNotFound();
          return null;
        }
        if (!response.ok) {
          throw new Error("Falha ao carregar pessoa (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        renderPerson(data);
      })
      .catch(function (err) {
        console.error("[person_detail] erro ao carregar pessoa", err);
        showNotFound();
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível carregar a pessoa.");
        }
      });
  }

  // ---------- Extrai o id numérico da URL /persons/{id} ----------
  function parsePersonIdFromPath() {
    var m = window.location.pathname.match(/\/persons\/(\d+)\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  // ---------- Inicialização ----------
  function setup() {
    contentEl = document.getElementById("person-detail-content");
    loadingEl = document.getElementById("person-detail-loading");
    // early-return: se não há o esqueleto de detalhe, não é a nossa tela.
    if (!contentEl || !loadingEl) return;

    notFoundEl = document.getElementById("person-detail-notfound");
    archivedNoteEl = document.getElementById("person-detail-archived-note");
    editBtnEl = document.getElementById("person-detail-edit");
    backLinkEl = document.getElementById("person-detail-back");

    personId = parsePersonIdFromPath();
    if (personId === null || isNaN(personId)) {
      // URL sem id numérico válido — não deveria acontecer (rota é :int),
      // mas tratamos defensivamente.
      showNotFound();
      return;
    }

    // Atalho Esc volta para a lista (decisão (d)).
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        e.preventDefault();
        window.location.href = "/persons";
      }
    });

    loadPerson();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
