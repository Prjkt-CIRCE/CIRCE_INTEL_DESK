/* ============================================================
   CIRCE Intel Desk — case_detail.js
   Tela de detalhe de um caso (RF-001) — Sprint 01, Bloco 8, Sub-passo 8.6.

   Decisões do operador no 8.6:
     - (a) Renderização SPA-leve: a rota /cases/{id} serve só o
       esqueleto (detail.html); este script busca GET /api/cases/{id}
       e popula os slots [data-field]. Trata 3 estados: carregando,
       não-encontrado (404), conteúdo.
     - (b/D56) "Editar" NÃO abre modal aqui: navega para
       /cases?edit={id}; a lista (cases.js, 8.6-c) abre o modal de
       edição já no caso certo. Evita refatorar o cases.js fechado.
     - (c) "Reativar" caso arquivado: FORA do 8.6 (D48). Em caso
       arquivado, apenas exibimos a nota #case-detail-archived-note;
       nenhum botão de reativar.
     - (d) Voltar: link "< CASOS" (href no HTML) + atalho Esc (aqui).

   Contrato da API (validado no 8.3, confirmado no 8.6):
     - GET /api/cases/{case_id:int} -> CaseResponse | 404.
       Campos: id, case_code, name, description, procedure_number,
       fact_date, unit, responsible, status, tags, notes,
       created_at, created_by, updated_at, updated_by.

   Preservado do padrão da casa: IIFE, "use strict", namespace
   window.CIRCE, setup no DOMContentLoaded com guarda de readyState,
   early-return se os elementos da tela não existem, D53 (reusa
   window.CIRCE.toast) e D54 (handleAuthLapse em TODO fetch).

   NOTA DE DÍVIDA (anotada com o operador no 8.6-b): formatDate e
   statusBadgeHtml são REPLICADOS de cases.js, não compartilhados.
   Extrair ambos (e o modal, decisão (b)) para um util/módulo comum
   é pendência para quando a 2ª tela (Pessoas, RF-002) pedir o mesmo
   padrão — aí a extração se paga. Replicar agora evita mexer no
   cases.js fechado/validado no 8.5.
   ============================================================ */

(function () {
  "use strict";

  var API_BASE = "/api/cases";

  // ---------- DOM refs ----------
  var loadingEl = null;
  var notFoundEl = null;
  var contentEl = null;
  var archivedNoteEl = null;
  var editBtnEl = null;
  var backLinkEl = null;

  // id do caso (extraído da URL /cases/{id}).
  var caseId = null;

  // ---------- Utilidades de data (REPLICADAS de cases.js — ver nota de dívida) ----------
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

  // fact_date é Optional[str] e representa uma DATA (do fato), não um
  // carimbo de sistema. Pode chegar como "YYYY-MM-DD" (sem hora) ou ISO
  // completo. Para não exibir um falso "00:00", mostramos só a parte de
  // data quando não há componente de hora detectável. Se o parse falhar,
  // mostramos cru (não escondemos o problema — mesmo princípio do cases.js).
  function formatDateOnly(value) {
    if (!value) return "—";
    var s = String(value);
    // Se vier "YYYY-MM-DD" puro (10 chars, sem 'T'), formata sem hora.
    var dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(s);
    var d = new Date(s);
    if (isNaN(d.getTime())) return s;
    if (dateOnly) {
      // Usa componentes UTC para "YYYY-MM-DD" (o JS interpreta data pura
      // como meia-noite UTC; usar getDate local poderia recuar 1 dia).
      return pad2(d.getUTCDate()) + "." + MESES[d.getUTCMonth()] + "." + d.getUTCFullYear();
    }
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  // ---------- Badge de status (REPLICADO de cases.js — ver nota de dívida) ----------
  function statusBadgeHtml(status) {
    var map = {
      "active":   { cls: "badge--ativo",     txt: "[ATIVO]" },
      "archived": { cls: "badge--arquivado", txt: "[ARQUIVADO]" }
    };
    var entry = map[status] || { cls: "badge--arquivado", txt: "[" + String(status).toUpperCase() + "]" };
    return '<span class="badge ' + entry.cls + '">' + entry.txt + "</span>";
  }

  // ---------- Guarda de sessão expirada (D54 — idêntico ao cases.js) ----------
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
  // Escreve texto num slot [data-field]; usa "—" para valores vazios.
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

  // ---------- Popular a tela com o caso ----------
  function renderCase(c) {
    // Header.
    setField("case_code", c.case_code);
    setField("name", c.name);

    var badgeSlot = contentEl ? contentEl.querySelector('[data-field="status_badge"]') : null;
    if (badgeSlot) badgeSlot.innerHTML = statusBadgeHtml(c.status);

    // Strip de metadados.
    setField("unit", c.unit);
    setField("responsible", c.responsible);
    setField("created_at", formatDateTime(c.created_at));

    // Seções.
    setField("description", c.description);
    setField("procedure_number", c.procedure_number);
    setField("fact_date", formatDateOnly(c.fact_date));
    setField("tags", c.tags);
    setField("notes", c.notes);

    // Auditoria.
    setField("created_at_full", formatDateTime(c.created_at));
    setField("created_by", c.created_by);
    setField("updated_at", formatDateTime(c.updated_at));
    setField("updated_by", c.updated_by);

    // Nota de caso arquivado (decisão (c) + D48): sem botão de reativar.
    if (archivedNoteEl) archivedNoteEl.hidden = (c.status !== "archived");

    // Botão "Editar" (decisão (b)/D56): leva à lista com o modal aberto.
    if (editBtnEl) {
      editBtnEl.onclick = function () {
        window.location.href = "/cases?edit=" + encodeURIComponent(c.id);
      };
    }

    showContent();
  }

  // ---------- Buscar o caso ----------
  function loadCase() {
    showLoading();

    fetch(API_BASE + "/" + encodeURIComponent(caseId), {
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
          throw new Error("Falha ao carregar caso (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (data) {
        if (data === null) return; // redirecionou ou 404 já tratado
        renderCase(data);
      })
      .catch(function (err) {
        console.error("[case_detail] erro ao carregar caso", err);
        // Em erro de rede/500, mostramos o estado "não encontrado" como
        // fallback visível (a shell não pode ficar travada em "Carregando")
        // e avisamos via toast no padrão da casa (D53).
        showNotFound();
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível carregar o caso.");
        }
      });
  }

  // ---------- Extrai o id numérico da URL /cases/{id} ----------
  function parseCaseIdFromPath() {
    var m = window.location.pathname.match(/\/cases\/(\d+)\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  // ---------- Inicialização ----------
  function setup() {
    contentEl = document.getElementById("case-detail-content");
    loadingEl = document.getElementById("case-detail-loading");
    // early-return: se não há o esqueleto de detalhe, não é a nossa tela.
    if (!contentEl || !loadingEl) return;

    notFoundEl = document.getElementById("case-detail-notfound");
    archivedNoteEl = document.getElementById("case-detail-archived-note");
    editBtnEl = document.getElementById("case-detail-edit");
    backLinkEl = document.getElementById("case-detail-back");

    caseId = parseCaseIdFromPath();
    if (caseId === null || isNaN(caseId)) {
      // URL sem id numérico válido — não deveria acontecer (a rota é :int),
      // mas tratamos defensivamente como "não encontrado".
      showNotFound();
      return;
    }

    // Atalho Esc volta para a lista (decisão (d)). O link "< CASOS" já
    // tem href; aqui só adicionamos o teclado.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        e.preventDefault();
        window.location.href = "/cases";
      }
    });

    loadCase();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
