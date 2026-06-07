/* ============================================================
   CIRCE Intel Desk — cases.js
   Tela funcional de Casos (RF-001) — Sprint 01, Bloco 8, Sub-passo 8.5.

   Sub-passo 8.6-c (alterações cirúrgicas sobre o 8.5):
     - Botão "Abrir" de cada linha agora navega para /cases/{id}
       (tela de detalhe, RF-001 visualizar). Antes ficava disabled.
     - loadCases(onLoaded?) aceita um callback opcional, chamado após
       renderizar a tabela (necessário porque o fetch é assíncrono).
     - setup() chama loadCases(maybeOpenEditFromUrl): se a URL trouxer
       ?edit=id (vinda do botão "Editar" da tela de detalhe, D56), o
       modal de edição abre já no caso certo. Caso fora da lista atual
       (ex.: arquivado com filtro desligado) é buscado por GET singular.
       O ?edit é limpo da URL (replaceState) para não reabrir no F5.
   Nenhuma outra lógica do 8.5 foi tocada.

   Herdado do 8.4 (intacto): listar (GET), criar via modal sem reload
   (POST), validar nome inline (CA-001.3), ordenar por cabeçalho
   (CA-001.7), coluna "Criado em" (created_at).

   Novo no 8.5 (decisões do operador):
     - Editar caso (CA-001.4): MESMO modal, em modo dual create/edit.
       Submit despacha POST (create) ou PATCH /api/cases/{id} (edit).
       No modo editar, case_code aparece readonly (D48 — imutável, NÃO
       vai no PATCH); status nunca entra no formulário (D48).
       Idempotência (D49): só envia campos que mudaram; sem mudança,
       fecha com toast info e NÃO chama a API.
     - Arquivar caso (CA-001.5): modal de confirmação no padrão da casa
       (decisão (c)), depois DELETE /api/cases/{id} (arquivamento lógico).
     - Filtro "arquivados" (CA-001.5): toggle que alterna include_archived
       na query da listagem.
   Campos no modo editar: os MESMOS do modal atual (nome, unidade,
   responsável, procedimento, resumo) — decisão do operador. fact_date/
   tags/notes ficam para a tela de detalhe (8.6).

   Contratos da API (validados no 8.3):
     - PATCH  /api/cases/{id}  body CaseUpdate (campos opcionais: name,
       description, procedure_number, fact_date, unit, responsible,
       tags, notes). case_code e status NÃO entram (D48).
     - DELETE /api/cases/{id}  retorna o caso com status="archived".
     - GET    /api/cases?include_archived=&sort_by=&descending=

   Preservado: D53 (reusa window.CIRCE.toast, não recria), D54
   (handleAuthLapse trata 401 JSON E redirect/HTML em TODOS os fetch),
   D55 (Ctrl+N e ação cases.new da palette — agora abrem modo "create"
   explicitamente).

   Padrão da casa: IIFE, "use strict", namespace window.CIRCE,
   setup no DOMContentLoaded com guarda de readyState, early-return
   se os elementos da tela não existem.
   ============================================================ */

(function () {
  "use strict";

  var API_BASE = "/api/cases";

  // ---------- Estado ----------
  var state = {
    cases: [],
    sortBy: "created_at",     // alinhado ao default da API
    descending: true,         // alinhado ao default da API
    includeArchived: false,   // toggle "Mostrar arquivados" (8.5)
    mode: "create",           // "create" | "edit" — modo do modal (8.5)
    editingId: null,          // id do caso em edição (modo edit)
    editingOriginal: null     // snapshot do caso original p/ diff (D49)
  };

  // ---------- DOM refs ----------
  var tbodyEl = null;
  var countEl = null;
  var emptyEl = null;
  var titleLabelEl = null;
  var newBtnEl = null;
  var showArchivedEl = null;

  // Modal criar/editar
  var modalEl = null;
  var modalTitleEl = null;
  var modalSubtitleEl = null;
  var codeFieldEl = null;
  var formCodeEl = null;
  var formNameEl = null;
  var formDescEl = null;
  var formUnitEl = null;
  var formRespEl = null;
  var formProcEl = null;
  var nameErrorEl = null;
  var nameHintEl = null;
  var saveBtnEl = null;
  var cancelEls = null;

  // Modal de confirmação de arquivamento
  var archiveModalEl = null;
  var archiveCodeEl = null;
  var archiveNameEl = null;
  var archiveConfirmBtnEl = null;
  var archiveCancelEls = null;
  var archiveTargetId = null;   // id do caso a arquivar (enquanto o modal está aberto)

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

  // ---------- Guarda de sessão expirada (D54) ----------
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
  // onLoaded (opcional, 8.6-c): callback chamado APÓS o estado ser
  // populado e a tabela renderizada. Necessário porque o fetch é
  // assíncrono — abrir o modal de edição a partir de ?edit=id exige que
  // state.cases já esteja preenchido. Chamadas sem argumento (todas as
  // anteriores ao 8.6) seguem funcionando sem mudança.
  function loadCases(onLoaded) {
    var url = API_BASE
      + "?include_archived=" + (state.includeArchived ? "true" : "false")
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
        if (typeof onLoaded === "function") onLoaded();
      })
      .catch(function (err) {
        console.error("[cases] erro ao carregar lista", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível carregar a lista de casos.");
        }
      });
  }

  // ---------- Título da listagem conforme filtro ----------
  function updateTitleLabel() {
    if (!titleLabelEl) return;
    titleLabelEl.textContent = state.includeArchived
      ? "─── TODOS OS CASOS ───"
      : "─── CASOS ATIVOS ───";
  }

  // ---------- Renderizar tabela ----------
  function renderTable(highlightId) {
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
      tbodyEl.appendChild(buildRow(c, highlightId != null && c.id === highlightId));
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

    // ---------- Coluna de ação (8.5) ----------
    // "Abrir" continua desabilitado (é do 8.6 — tela de detalhe).
    // "Editar" e "Arquivar" são os novos do 8.5.
    // Arquivar só faz sentido em casos ativos; em arquivados, ocultamos.
    var tdAction = document.createElement("td");

    var openBtn = document.createElement("button");
    openBtn.className = "btn btn--text";
    openBtn.type = "button";
    openBtn.textContent = "Abrir";
    // 8.6-c: navega para a tela de detalhe (RF-001 visualizar). O id é
    // sempre numérico (vem do banco) e casa com a rota /cases/{case_id:int}.
    openBtn.addEventListener("click", function () {
      window.location.href = "/cases/" + encodeURIComponent(c.id);
    });
    tdAction.appendChild(openBtn);

    var editBtn = document.createElement("button");
    editBtn.className = "btn btn--text";
    editBtn.type = "button";
    editBtn.textContent = "Editar";
    editBtn.setAttribute("data-action", "edit");
    tdAction.appendChild(editBtn);

    if (c.status !== "archived") {
      var archiveBtn = document.createElement("button");
      archiveBtn.className = "btn btn--text";
      archiveBtn.type = "button";
      archiveBtn.textContent = "Arquivar";
      archiveBtn.setAttribute("data-action", "archive");
      tdAction.appendChild(archiveBtn);
    }

    tr.appendChild(tdAction);

    if (highlight) {
      tr.setAttribute("data-selected", "true");
    }
    return tr;
  }

  // Localiza um caso no estado pelo id.
  function findCase(id) {
    for (var i = 0; i < state.cases.length; i++) {
      if (state.cases[i].id === id) return state.cases[i];
    }
    return null;
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

  // ---------- Modal criar/editar (modo dual, 8.5) ----------

  // Preenche/limpa os campos do formulário a partir de um caso (ou vazio).
  function fillForm(c) {
    if (formNameEl) formNameEl.value = c ? (c.name || "") : "";
    if (formDescEl) formDescEl.value = c ? (c.description || "") : "";
    if (formUnitEl) formUnitEl.value = c ? (c.unit || "") : "";
    if (formRespEl) formRespEl.value = c ? (c.responsible || "") : "";
    if (formProcEl) formProcEl.value = c ? (c.procedure_number || "") : "";
  }

  function openModalCreate() {
    if (!modalEl) return;
    state.mode = "create";
    state.editingId = null;
    state.editingOriginal = null;

    if (modalTitleEl) modalTitleEl.textContent = "NOVO CASO";
    if (modalSubtitleEl) modalSubtitleEl.textContent = "RF-001 · O código será gerado automaticamente";
    if (codeFieldEl) codeFieldEl.hidden = true;        // sem case_code no create
    if (formCodeEl) formCodeEl.value = "";
    if (nameHintEl) { nameHintEl.hidden = false; }
    if (saveBtnEl) saveBtnEl.textContent = "Salvar caso";

    fillForm(null);
    clearNameError();
    validateName();
    modalEl.setAttribute("data-open", "true");
    requestAnimationFrame(function () { if (formNameEl) formNameEl.focus(); });
  }

  function openModalEdit(c) {
    if (!modalEl || !c) return;
    state.mode = "edit";
    state.editingId = c.id;
    state.editingOriginal = c;

    if (modalTitleEl) modalTitleEl.textContent = "EDITAR CASO";
    if (modalSubtitleEl) modalSubtitleEl.textContent = "RF-001 · O código do caso é imutável";
    if (codeFieldEl) codeFieldEl.hidden = false;       // mostra case_code readonly (D48)
    if (formCodeEl) formCodeEl.value = c.case_code || "";
    if (nameHintEl) { nameHintEl.hidden = true; }      // dica de geração não se aplica ao editar
    if (saveBtnEl) saveBtnEl.textContent = "Salvar alterações";

    fillForm(c);
    clearNameError();
    validateName();
    modalEl.setAttribute("data-open", "true");
    requestAnimationFrame(function () { if (formNameEl) { formNameEl.focus(); formNameEl.select(); } });
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

  // Lê os campos do formulário, normalizando vazios para string vazia.
  function readForm() {
    return {
      name: formNameEl ? formNameEl.value.trim() : "",
      description: formDescEl ? formDescEl.value.trim() : "",
      unit: formUnitEl ? formUnitEl.value.trim() : "",
      responsible: formRespEl ? formRespEl.value.trim() : "",
      procedure_number: formProcEl ? formProcEl.value.trim() : ""
    };
  }

  // ---------- Submit (despacha create vs. edit) ----------
  function submitCase() {
    if (!validateName()) {
      showNameError("O nome do caso é obrigatório.");
      if (formNameEl) formNameEl.focus();
      return;
    }
    clearNameError();
    if (state.mode === "edit") {
      submitEdit();
    } else {
      submitCreate();
    }
  }

  // ---------- Criar caso (POST) — fluxo do 8.4 ----------
  function submitCreate() {
    if (saveBtnEl) saveBtnEl.disabled = true; // evita duplo-clique

    var f = readForm();
    var payload = { name: f.name };
    // Opcionais — só envia se preenchidos (o backend normaliza vazios para None).
    if (f.description) payload.description = f.description;
    if (f.unit) payload.unit = f.unit;
    if (f.responsible) payload.responsible = f.responsible;
    if (f.procedure_number) payload.procedure_number = f.procedure_number;

    fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 422) {
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

  // ---------- Editar caso (PATCH) — CA-001.4 ----------
  // Idempotência (D49): monta o payload apenas com os campos que mudaram
  // em relação ao caso original. Sem diff => não chama a API.
  function submitEdit() {
    var id = state.editingId;
    var orig = state.editingOriginal;
    if (id == null || !orig) return;

    var f = readForm();
    var fields = ["name", "description", "unit", "responsible", "procedure_number"];
    var payload = {};
    fields.forEach(function (k) {
      // Original pode vir null; tratamos null como "" para comparar com o form.
      var origVal = orig[k] == null ? "" : String(orig[k]);
      if (f[k] !== origVal) {
        // Campo opcional esvaziado vira null (limpa no banco); name nunca é "".
        payload[k] = (f[k] === "" && k !== "name") ? null : f[k];
      }
    });

    // D49 — nada mudou: fecha sem chamar a API, sem gerar log.
    if (Object.keys(payload).length === 0) {
      closeModal();
      if (window.CIRCE && window.CIRCE.toast) {
        window.CIRCE.toast.info("Sem alterações", "Nenhum campo foi modificado.");
      }
      return;
    }

    if (saveBtnEl) saveBtnEl.disabled = true; // evita duplo-clique

    fetch(API_BASE + "/" + encodeURIComponent(id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 422) {
          return response.json().then(function (body) {
            throw { kind: "validation", body: body };
          });
        }
        if (response.status === 404) {
          throw new Error("Caso não encontrado (HTTP 404).");
        }
        if (!response.ok) {
          throw new Error("Falha ao editar caso (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (updated) {
        if (updated === null) return; // redirecionou
        onCaseUpdated(updated);
      })
      .catch(function (err) {
        if (saveBtnEl) saveBtnEl.disabled = false;
        if (err && err.kind === "validation") {
          showNameError("O nome do caso é obrigatório.");
          return;
        }
        console.error("[cases] erro ao editar caso", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível salvar as alterações.");
        }
      });
  }

  // CA-001.2: caso criado aparece na lista SEM reload.
  function onCaseCreated(created) {
    closeModal();
    state.cases.unshift(created);
    if (state.sortBy === "created_at" && state.descending) {
      renderTable(created.id);
    } else {
      loadCases();
    }
    if (window.CIRCE && window.CIRCE.toast) {
      window.CIRCE.toast.success("Caso criado", created.case_code + " — " + created.name);
    }
  }

  // CA-001.4: alteração reflete na lista sem reload.
  function onCaseUpdated(updated) {
    closeModal();
    // Substitui o registro no estado e re-renderiza, mantendo a ordem atual.
    for (var i = 0; i < state.cases.length; i++) {
      if (state.cases[i].id === updated.id) {
        state.cases[i] = updated;
        break;
      }
    }
    renderTable(updated.id);
    if (window.CIRCE && window.CIRCE.toast) {
      window.CIRCE.toast.success("Caso atualizado", updated.case_code + " — " + updated.name);
    }
  }

  // ---------- Arquivar caso (CA-001.5) ----------
  // Decisão (c): confirmação via modal da casa, não confirm() nativo.
  function openArchiveModal(c) {
    if (!archiveModalEl || !c) return;
    archiveTargetId = c.id;
    if (archiveCodeEl) archiveCodeEl.textContent = c.case_code || "—";
    if (archiveNameEl) archiveNameEl.textContent = c.name || "";
    archiveModalEl.setAttribute("data-open", "true");
    requestAnimationFrame(function () { if (archiveConfirmBtnEl) archiveConfirmBtnEl.focus(); });
  }

  function closeArchiveModal() {
    if (!archiveModalEl) return;
    archiveModalEl.setAttribute("data-open", "false");
    archiveTargetId = null;
  }

  function confirmArchive() {
    var id = archiveTargetId;
    if (id == null) { closeArchiveModal(); return; }
    if (archiveConfirmBtnEl) archiveConfirmBtnEl.disabled = true;

    fetch(API_BASE + "/" + encodeURIComponent(id), {
      method: "DELETE",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 404) {
          throw new Error("Caso não encontrado (HTTP 404).");
        }
        if (!response.ok) {
          throw new Error("Falha ao arquivar caso (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (archived) {
        if (archived === null) return; // redirecionou
        onCaseArchived(archived);
      })
      .catch(function (err) {
        console.error("[cases] erro ao arquivar caso", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível arquivar o caso.");
        }
      })
      .then(function () {
        // finally — reabilita o botão e fecha o modal em qualquer desfecho.
        if (archiveConfirmBtnEl) archiveConfirmBtnEl.disabled = false;
        closeArchiveModal();
      });
  }

  // CA-001.5: arquivado some da lista padrão; recarrega respeitando o filtro.
  function onCaseArchived(archived) {
    // Recarrega do servidor: garante coerência com o filtro atual
    // (se "Mostrar arquivados" estiver desligado, ele desaparece; se
    // ligado, reaparece já com badge [ARQUIVADO]).
    loadCases();
    if (window.CIRCE && window.CIRCE.toast) {
      window.CIRCE.toast.success("Caso arquivado", archived.case_code + " — " + archived.name);
    }
  }

  // ---------- Delegação de ações na tabela (editar / arquivar) ----------
  function onTbodyClick(e) {
    var btn = e.target.closest ? e.target.closest("button[data-action]") : null;
    if (!btn) return;
    var tr = btn.closest("tr[data-case-id]");
    if (!tr) return;
    var id = parseInt(tr.getAttribute("data-case-id"), 10);
    if (isNaN(id)) return;
    var c = findCase(id);
    if (!c) return;

    var action = btn.getAttribute("data-action");
    if (action === "edit") {
      openModalEdit(c);
    } else if (action === "archive") {
      openArchiveModal(c);
    }
  }

  // ---------- Registro na command palette (Ctrl+K) — D55 ----------
  function registerPaletteAction() {
    if (window.CIRCE && window.CIRCE.palette && typeof window.CIRCE.palette.register === "function") {
      window.CIRCE.palette.register({
        id: "cases.new",
        label: "Novo caso",
        group: "Ações",
        keywords: ["novo", "caso", "criar", "case", "new"],
        hint: "Ctrl+N",
        handler: function () { openModalCreate(); }
      });
    }
  }

  // ---------- Abertura do modal de edição via ?edit=id (8.6-c / D56) ----------
  // A tela de detalhe (case_detail.js) manda o operador de volta à lista
  // com /cases?edit={id} quando ele clica "Editar". Aqui detectamos esse
  // parâmetro e abrimos o modal de edição já no caso certo.
  //
  // Dois caminhos para obter o caso:
  //   1) Está na lista já carregada (state.cases) — uso direto.
  //   2) Não está (ex.: caso ARQUIVADO e o filtro "Mostrar arquivados"
  //      está desligado) — busco via GET /api/cases/{id} como fallback,
  //      para não falhar silenciosamente.
  //
  // Em qualquer caso, limpamos o ?edit da URL (replaceState) para que um
  // F5 não reabra o modal indefinidamente.
  function maybeOpenEditFromUrl() {
    var params = new URLSearchParams(window.location.search);
    var raw = params.get("edit");
    if (raw === null) return;

    var id = parseInt(raw, 10);

    // Remove o ?edit da URL sem recarregar a página.
    params.delete("edit");
    var clean = window.location.pathname
      + (params.toString() ? "?" + params.toString() : "");
    window.history.replaceState({}, "", clean);

    if (isNaN(id)) return;

    var c = findCase(id);
    if (c) {
      openModalEdit(c);
      return;
    }

    // Fallback: caso fora da lista atual (provavelmente arquivado).
    fetch(API_BASE + "/" + encodeURIComponent(id), {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (response.status === 404) {
          if (window.CIRCE && window.CIRCE.toast) {
            window.CIRCE.toast.error("Caso não encontrado", "O caso a editar não existe mais.");
          }
          return null;
        }
        if (!response.ok) {
          throw new Error("Falha ao carregar caso para edição (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (caseObj) {
        if (caseObj === null) return;
        openModalEdit(caseObj);
      })
      .catch(function (err) {
        console.error("[cases] erro ao abrir edição via ?edit", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível abrir o caso para edição.");
        }
      });
  }

  // ---------- Inicialização ----------
  function setup() {
    tbodyEl = document.getElementById("cases-tbody");
    if (!tbodyEl) return; // não estamos na tela de casos — early return

    countEl = document.getElementById("cases-count");
    emptyEl = document.getElementById("cases-empty");
    titleLabelEl = document.getElementById("cases-title-label");
    newBtnEl = document.getElementById("cases-new-btn");
    showArchivedEl = document.getElementById("cases-show-archived");

    modalEl = document.getElementById("case-create-modal");
    if (modalEl) {
      modalTitleEl = modalEl.querySelector("#case-create-title");
      modalSubtitleEl = modalEl.querySelector("#case-create-subtitle");
      codeFieldEl = modalEl.querySelector("#case-form-code-field");
      formCodeEl = modalEl.querySelector("#case-form-code");
      formNameEl = modalEl.querySelector("#case-form-name");
      formDescEl = modalEl.querySelector("#case-form-description");
      formUnitEl = modalEl.querySelector("#case-form-unit");
      formRespEl = modalEl.querySelector("#case-form-responsible");
      formProcEl = modalEl.querySelector("#case-form-procedure");
      nameErrorEl = modalEl.querySelector("#case-form-name-error");
      nameHintEl = modalEl.querySelector("#case-form-name-hint");
      saveBtnEl = modalEl.querySelector("#case-form-save");
      cancelEls = modalEl.querySelectorAll("[data-modal-close]");
    }

    archiveModalEl = document.getElementById("case-archive-modal");
    if (archiveModalEl) {
      archiveCodeEl = archiveModalEl.querySelector("#case-archive-code");
      archiveNameEl = archiveModalEl.querySelector("#case-archive-name");
      archiveConfirmBtnEl = archiveModalEl.querySelector("#case-archive-confirm");
      archiveCancelEls = archiveModalEl.querySelectorAll("[data-archive-cancel]");
    }

    // Botão "Novo caso" abre o modal em modo create.
    if (newBtnEl) newBtnEl.addEventListener("click", openModalCreate);

    // Toggle "Mostrar arquivados".
    if (showArchivedEl) {
      showArchivedEl.addEventListener("change", function () {
        state.includeArchived = !!showArchivedEl.checked;
        updateTitleLabel();
        loadCases();
      });
    }

    // Validação inline do nome (CA-001.3).
    if (formNameEl) {
      formNameEl.addEventListener("input", function () {
        clearNameError();
        validateName();
      });
    }

    // Salvar (despacha create/edit).
    if (saveBtnEl) saveBtnEl.addEventListener("click", submitCase);

    // Cancelar / fechar o modal de criar/editar.
    if (cancelEls) {
      cancelEls.forEach(function (el) { el.addEventListener("click", closeModal); });
    }
    if (modalEl) {
      modalEl.addEventListener("click", function (e) {
        if (e.target === modalEl) closeModal();
      });
    }

    // Modal de confirmação de arquivamento: confirmar / cancelar / backdrop.
    if (archiveConfirmBtnEl) archiveConfirmBtnEl.addEventListener("click", confirmArchive);
    if (archiveCancelEls) {
      archiveCancelEls.forEach(function (el) { el.addEventListener("click", closeArchiveModal); });
    }
    if (archiveModalEl) {
      archiveModalEl.addEventListener("click", function (e) {
        if (e.target === archiveModalEl) closeArchiveModal();
      });
    }

    // Delegação das ações por linha (editar / arquivar).
    tbodyEl.addEventListener("click", onTbodyClick);

    // Teclado: Esc fecha o modal aberto (confirmação tem prioridade);
    // Alt+N abre "Novo caso" (revisa D55 — ver nota abaixo).
    //
    // NOTA (8.6, revisão de D55): o atalho era Ctrl+N, mas Ctrl+N é
    // RESERVADO pelo navegador (nova janela) e disparado antes do JS,
    // então preventDefault() não o segura numa aba normal. Trocado por
    // Alt+N, que é capturável. A guarda !ctrlKey && !metaKey impede que
    // Ctrl+Alt+N (ou Cmd+Alt+N) dispare por engano. A formalização desta
    // revisão de D55 fica para o fechamento do bloco (8.7).
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (archiveModalEl && archiveModalEl.getAttribute("data-open") === "true") {
          e.preventDefault();
          closeArchiveModal();
          return;
        }
        if (modalEl && modalEl.getAttribute("data-open") === "true") {
          e.preventDefault();
          closeModal();
          return;
        }
      }
      if (e.altKey && !e.ctrlKey && !e.metaKey && (e.key === "n" || e.key === "N")) {
        var paletteOpen = window.CIRCE && window.CIRCE.palette
          && typeof window.CIRCE.palette.isOpen === "function"
          && window.CIRCE.palette.isOpen();
        if (!paletteOpen) {
          e.preventDefault();
          openModalCreate();
        }
      }
    });

    updateTitleLabel();
    setupSortHeaders();
    registerPaletteAction();
    // 8.6-c: ao terminar de carregar a lista, verifica ?edit=id na URL
    // (vinda do botão "Editar" da tela de detalhe, D56) e abre o modal.
    loadCases(maybeOpenEditFromUrl);
  }

  // ---------- API pública (mínima) ----------
  window.CIRCE = window.CIRCE || {};
  window.CIRCE.cases = {
    reload: loadCases,
    openNew: openModalCreate
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
