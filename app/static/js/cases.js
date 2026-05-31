/* ============================================================
   CIRCE Intel Desk — cases.js
   Tela funcional de Casos (RF-001) — Sprint 01, Bloco 8, Sub-passo 8.4.

   Escopo do 8.4 (decisão do operador, §13 do ESTADO_DO_PROJETO):
     - Listar casos (GET /api/cases).
     - Criar caso via modal "Novo caso" (POST /api/cases), sem reload.
     - Validar nome inline (CA-001.3): botão Salvar desabilitado se vazio.
     - Ordenar pela coluna do cabeçalho (CA-001.7).
   FORA do 8.4 (ficam para o 8.5): editar (CA-001.4), arquivar +
   filtro "arquivados" (CA-001.5).

   Coluna de data exibida: "Criado em" (created_at) — decisão do operador (a).

   Guarda de sessão expirada: o fetch para /api/cases pode encontrar
   DOIS comportamentos, dependendo de qual camada intercepta:
     - middleware do auth_guard: redirect 303 -> /login (HTML).
     - endpoint _current_user_id: 401 JSON (rede de segurança, D30).
   Tratamos AMBOS (decisão do operador). Em qualquer um, mandamos o
   operador para /login em vez de quebrar silenciosamente.

   Padrão da casa: IIFE, "use strict", namespace window.CIRCE,
   setup no DOMContentLoaded com guarda de readyState, early-return
   se os elementos da tela não existem (script carregado só nesta tela,
   mas a guarda é barata e segue o molde de command_palette.js).
   ============================================================ */

(function () {
  "use strict";

  var API_BASE = "/api/cases";

  // ---------- Estado ----------
  var state = {
    cases: [],
    sortBy: "created_at",   // alinhado ao default da API
    descending: true        // alinhado ao default da API
  };

  // ---------- DOM refs ----------
  var tbodyEl = null;
  var countEl = null;
  var emptyEl = null;
  var newBtnEl = null;
  var modalEl = null;
  var formNameEl = null;
  var formDescEl = null;
  var formUnitEl = null;
  var formRespEl = null;
  var formProcEl = null;
  var nameErrorEl = null;
  var saveBtnEl = null;
  var cancelEls = null;

  // ---------- Utilidades de data ----------
  // created_at chega como string ISO (CaseResponse serializa do ORM).
  // Exibimos em formato curto, mono, estilo ficha: DD.MMM.AAAA HH:MM.
  var MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
               "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  function formatDate(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) {
      // Se o backend mandar um formato que o Date não parseia, mostramos
      // cru em vez de "Invalid Date" — não escondemos o problema.
      return String(iso);
    }
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  // ---------- Badge de status ----------
  // Classes canônicas do design system (components.css).
  function statusBadgeHtml(status) {
    var map = {
      "active":   { cls: "badge--ativo",      txt: "[ATIVO]" },
      "archived": { cls: "badge--arquivado",  txt: "[ARQUIVADO]" }
    };
    var entry = map[status] || { cls: "badge--arquivado", txt: "[" + String(status).toUpperCase() + "]" };
    return '<span class="badge ' + entry.cls + '">' + entry.txt + "</span>";
  }

  // ---------- Guarda de sessão expirada ----------
  // Detecta os dois caminhos possíveis. Retorna true se a resposta
  // indica sessão expirada/não-autenticada (e já redirecionou).
  function handleAuthLapse(response) {
    var isHtmlRedirect =
      response.redirected ||
      (response.headers.get("content-type") || "").indexOf("text/html") >= 0;
    if (response.status === 401 || isHtmlRedirect) {
      // Preserva para onde voltar depois do login.
      var next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = "/login?next=" + next;
      return true;
    }
    return false;
  }

  // ---------- Carregar lista ----------
  function loadCases() {
    var url = API_BASE
      + "?include_archived=false"
      + "&sort_by=" + encodeURIComponent(state.sortBy)
      + "&descending=" + (state.descending ? "true" : "false");

    fetch(url, {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (!response.ok) {
          throw new Error("Falha ao listar casos (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (data) {
        if (data === null) return; // já redirecionou
        state.cases = Array.isArray(data) ? data : [];
        renderTable();
      })
      .catch(function (err) {
        console.error("[cases] erro ao carregar lista", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível carregar a lista de casos.");
        }
      });
  }

  // ---------- Renderizar tabela ----------
  function renderTable() {
    if (!tbodyEl) return;
    tbodyEl.innerHTML = "";

    if (countEl) {
      countEl.textContent = pad2(state.cases.length) + " REGISTRO"
        + (state.cases.length === 1 ? "" : "S");
    }

    if (state.cases.length === 0) {
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;

    state.cases.forEach(function (c) {
      tbodyEl.appendChild(buildRow(c));
    });
  }

  function buildRow(c, highlight) {
    var tr = document.createElement("tr");
    tr.setAttribute("data-case-id", String(c.id));

    var tdCode = document.createElement("td");
    tdCode.className = "col-mono";
    tdCode.textContent = c.case_code;
    tr.appendChild(tdCode);

    var tdName = document.createElement("td");
    tdName.textContent = c.name;
    tr.appendChild(tdName);

    var tdStatus = document.createElement("td");
    tdStatus.innerHTML = statusBadgeHtml(c.status);
    tr.appendChild(tdStatus);

    var tdCreated = document.createElement("td");
    tdCreated.className = "col-mono";
    tdCreated.textContent = formatDate(c.created_at);
    tr.appendChild(tdCreated);

    // Coluna de ação — "Abrir" leva à tela de detalhe (8.6).
    // Por ora aponta para a futura rota; não é alvo do 8.4.
    var tdAction = document.createElement("td");
    var openBtn = document.createElement("button");
    openBtn.className = "btn btn--text";
    openBtn.type = "button";
    openBtn.textContent = "Abrir";
    openBtn.disabled = true;             // habilita no 8.6 (tela de detalhe)
    openBtn.title = "Detalhe do caso — Sub-passo 8.6";
    tdAction.appendChild(openBtn);
    tr.appendChild(tdAction);

    if (highlight) {
      // Marca a linha recém-criada (CA-001.2 — feedback visual).
      tr.setAttribute("data-selected", "true");
    }
    return tr;
  }

  // ---------- Ordenação por cabeçalho (CA-001.7) ----------
  function setupSortHeaders() {
    var headers = document.querySelectorAll("[data-sort-key]");
    headers.forEach(function (th) {
      th.addEventListener("click", function () {
        var key = th.getAttribute("data-sort-key");
        if (state.sortBy === key) {
          state.descending = !state.descending; // alterna direção
        } else {
          state.sortBy = key;
          state.descending = true;
        }
        updateSortIndicators();
        loadCases();
      });
    });
    updateSortIndicators();
  }

  function updateSortIndicators() {
    var headers = document.querySelectorAll("[data-sort-key]");
    headers.forEach(function (th) {
      var key = th.getAttribute("data-sort-key");
      var indicator = th.querySelector(".sort-indicator");
      if (!indicator) return;
      if (key === state.sortBy) {
        indicator.textContent = state.descending ? "↓" : "↑";
      } else {
        indicator.textContent = "";
      }
    });
  }

  // ---------- Modal "Novo caso" ----------
  function openModal() {
    if (!modalEl) return;
    // Limpa o formulário a cada abertura.
    if (formNameEl) formNameEl.value = "";
    if (formDescEl) formDescEl.value = "";
    if (formUnitEl) formUnitEl.value = "";
    if (formRespEl) formRespEl.value = "";
    if (formProcEl) formProcEl.value = "";
    clearNameError();
    validateName();
    modalEl.setAttribute("data-open", "true");
    requestAnimationFrame(function () { if (formNameEl) formNameEl.focus(); });
  }

  function closeModal() {
    if (!modalEl) return;
    modalEl.setAttribute("data-open", "false");
  }

  function clearNameError() {
    if (formNameEl) formNameEl.classList.remove("input--error");
    if (nameErrorEl) { nameErrorEl.textContent = ""; nameErrorEl.hidden = true; }
  }

  function showNameError(msg) {
    if (formNameEl) formNameEl.classList.add("input--error");
    if (nameErrorEl) { nameErrorEl.textContent = msg; nameErrorEl.hidden = false; }
  }

  // CA-001.3: botão Salvar desabilitado enquanto o nome está vazio.
  function validateName() {
    var valid = formNameEl && formNameEl.value.trim().length > 0;
    if (saveBtnEl) saveBtnEl.disabled = !valid;
    return valid;
  }

  // ---------- Criar caso (POST) ----------
  function submitCase() {
    if (!validateName()) {
      showNameError("O nome do caso é obrigatório.");
      if (formNameEl) formNameEl.focus();
      return;
    }
    clearNameError();
    if (saveBtnEl) saveBtnEl.disabled = true; // evita duplo-clique

    var payload = { name: formNameEl.value.trim() };
    // Opcionais — só envia se preenchidos (o backend normaliza vazios para None).
    if (formDescEl && formDescEl.value.trim()) payload.description = formDescEl.value.trim();
    if (formUnitEl && formUnitEl.value.trim()) payload.unit = formUnitEl.value.trim();
    if (formRespEl && formRespEl.value.trim()) payload.responsible = formRespEl.value.trim();
    if (formProcEl && formProcEl.value.trim()) payload.procedure_number = formProcEl.value.trim();

    fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 422) {
          // Erro de validação do schema (ex.: nome vazio escapou).
          return response.json().then(function (body) {
            throw { kind: "validation", body: body };
          });
        }
        if (!response.ok) {
          throw new Error("Falha ao criar caso (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (created) {
        if (created === null) return; // redirecionou
        onCaseCreated(created);
      })
      .catch(function (err) {
        if (saveBtnEl) saveBtnEl.disabled = false;
        if (err && err.kind === "validation") {
          showNameError("O nome do caso é obrigatório.");
          return;
        }
        console.error("[cases] erro ao criar caso", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível criar o caso.");
        }
      });
  }

  // CA-001.2: caso criado aparece na lista SEM reload.
  function onCaseCreated(created) {
    closeModal();
    // Insere conforme a ordenação atual. Caminho simples e correto:
    // recarrega a lista do servidor (fonte de verdade da ordenação).
    // Mas para o feedback "sem reload" ser nítido, inserimos a linha
    // imediatamente no topo (created_at desc é o default) e marcamos,
    // depois sincronizamos.
    state.cases.unshift(created);
    if (state.sortBy === "created_at" && state.descending) {
      // Já está no topo na ordem correta — render direto com destaque.
      renderTableWithHighlight(created.id);
    } else {
      // Ordenação diferente: recarrega para respeitar o sort do servidor.
      loadCases();
    }
    if (window.CIRCE && window.CIRCE.toast) {
      window.CIRCE.toast.success("Caso criado", created.case_code + " — " + created.name);
    }
  }

  function renderTableWithHighlight(highlightId) {
    if (!tbodyEl) return;
    tbodyEl.innerHTML = "";
    if (countEl) {
      countEl.textContent = pad2(state.cases.length) + " REGISTRO"
        + (state.cases.length === 1 ? "" : "S");
    }
    if (emptyEl) emptyEl.hidden = state.cases.length !== 0;
    state.cases.forEach(function (c) {
      tbodyEl.appendChild(buildRow(c, c.id === highlightId));
    });
  }

  // ---------- Registro na command palette (Ctrl+K) ----------
  function registerPaletteAction() {
    if (window.CIRCE && window.CIRCE.palette && typeof window.CIRCE.palette.register === "function") {
      window.CIRCE.palette.register({
        id: "cases.new",
        label: "Novo caso",
        group: "Ações",
        keywords: ["novo", "caso", "criar", "case", "new"],
        hint: "Ctrl+N",
        handler: function () { openModal(); }
      });
    }
  }

  // ---------- Inicialização ----------
  function setup() {
    tbodyEl = document.getElementById("cases-tbody");
    if (!tbodyEl) return; // não estamos na tela de casos — early return

    countEl = document.getElementById("cases-count");
    emptyEl = document.getElementById("cases-empty");
    newBtnEl = document.getElementById("cases-new-btn");
    modalEl = document.getElementById("case-create-modal");

    if (modalEl) {
      formNameEl = modalEl.querySelector("#case-form-name");
      formDescEl = modalEl.querySelector("#case-form-description");
      formUnitEl = modalEl.querySelector("#case-form-unit");
      formRespEl = modalEl.querySelector("#case-form-responsible");
      formProcEl = modalEl.querySelector("#case-form-procedure");
      nameErrorEl = modalEl.querySelector("#case-form-name-error");
      saveBtnEl = modalEl.querySelector("#case-form-save");
      cancelEls = modalEl.querySelectorAll("[data-modal-close]");
    }

    // Botão "Novo caso" abre o modal.
    if (newBtnEl) newBtnEl.addEventListener("click", openModal);

    // Validação inline do nome (CA-001.3).
    if (formNameEl) {
      formNameEl.addEventListener("input", function () {
        clearNameError();
        validateName();
      });
    }

    // Salvar.
    if (saveBtnEl) saveBtnEl.addEventListener("click", submitCase);

    // Cancelar / fechar.
    if (cancelEls) {
      cancelEls.forEach(function (el) {
        el.addEventListener("click", closeModal);
      });
    }

    // Backdrop click fecha (padrão dos modais da casa).
    if (modalEl) {
      modalEl.addEventListener("click", function (e) {
        if (e.target === modalEl) closeModal();
      });
    }

    // Esc fecha o modal (somente quando aberto).
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modalEl && modalEl.getAttribute("data-open") === "true") {
        e.preventDefault();
        closeModal();
      }
      // Ctrl+N abre "Novo caso" quando nesta tela (atalho previsto no
      // modal de atalhos da 0.5, marcado para a Sprint 01).
      if ((e.ctrlKey || e.metaKey) && (e.key === "n" || e.key === "N")) {
        // Só intercepta se o palette não estiver aberto.
        var paletteOpen = window.CIRCE && window.CIRCE.palette
          && typeof window.CIRCE.palette.isOpen === "function"
          && window.CIRCE.palette.isOpen();
        if (!paletteOpen) {
          e.preventDefault();
          openModal();
        }
      }
    });

    setupSortHeaders();
    registerPaletteAction();
    loadCases();
  }

  // ---------- API pública (mínima) ----------
  window.CIRCE = window.CIRCE || {};
  window.CIRCE.cases = {
    reload: loadCases,
    openNew: openModal
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
