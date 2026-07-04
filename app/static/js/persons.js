/* ============================================================
   CIRCE Intel Desk — persons.js
   Tela funcional de Pessoas (RF-002) — Sprint 01, Bloco 9, Sub-passo 9.5.

   Espelha app/static/js/cases.js (Bloco 8.4/8.5) na arquitetura geral:
   IIFE + "use strict", estado local, fetch com guarda de sessão (D54),
   modal dual criar/editar, modal de confirmação de arquivamento,
   ordenação por cabeçalho, toast (D53).

   Diferenças do RF-002:
     - CA-002.2: cpf é normalizado no backend; aqui só formatamos para
       EXIBIÇÃO (000.000.000-00) quando tem 11 dígitos.
     - CA-002.3: aliases (";"-separado) exibidas como lista simples em
       mono — sem badge dedicada (evita inventar classe CSS nova).
     - CA-002.5 (decisão do operador, 9.5): ao salvar com CPF duplicado,
       a API responde 409 com {existing_person_id, existing_person_name}.
       A UI mostra um TOAST DE ERRO citando o nome da pessoa existente,
       sem ação direta (não há tela de detalhe de Pessoa ainda).
     - Atalho "Nova pessoa" nasce como Ctrl+Alt+P (não Ctrl+P), já
       aplicando a lição do Ctrl+N -> Ctrl+Alt+N do Bloco 8.6 (Ctrl+P é
       "imprimir" do navegador, mesmo problema).
     - "Abrir" fica DESABILITADO: a tela de detalhe de Pessoa ainda não
       existe (mesmo estado do cases.js antes do Bloco 8.6).
   ============================================================ */

(function () {
  "use strict";

  var API_BASE = "/api/persons";

  var state = {
    persons: [],
    includeArchived: false,
    sortBy: "created_at",
    descending: true,
  };

  // ---------- DOM refs (populados no setup) ----------
  var tbodyEl, emptyEl, countEl, titleLabelEl, showArchivedEl, newBtnEl;
  var modalEl, modalTitleEl, modalSubtitleEl, saveBtnEl;
  var formNameEl, formNameErrorEl, formAliasesEl, formCpfEl, formRgEl;
  var formSourceEl, formReliabilityEl, formNotesEl;
  var archiveModalEl, archiveNameEl, archiveConfirmBtnEl;

  var editingId = null;       // null = modo criar; caso contrário, id em edição
  var pendingArchiveId = null;

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

  // ---------- Formatação ----------
  var MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
               "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  function formatDateTime(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return pad2(d.getDate()) + "." + MESES[d.getMonth()] + "." + d.getFullYear()
         + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  // CA-002.2: cpf já vem normalizado (só dígitos) da API. Aqui aplicamos
  // a máscara SÓ para exibição, sem alterar o que é enviado ao backend.
  function formatCpfDisplay(cpf) {
    if (!cpf) return "—";
    if (/^\d{11}$/.test(cpf)) {
      return cpf.slice(0, 3) + "." + cpf.slice(3, 6) + "." + cpf.slice(6, 9) + "-" + cpf.slice(9);
    }
    return cpf; // não tem 11 dígitos: mostra cru, sem forçar máscara errada
  }

  // CA-002.3: alcunhas em texto livre separado por ";" -> lista simples.
  function formatAliasesDisplay(aliases) {
    if (!aliases) return "—";
    var parts = aliases.split(";").map(function (s) { return s.trim(); }).filter(Boolean);
    return parts.length ? parts.join(" · ") : "—";
  }

  function statusBadgeHtml(status) {
    var map = {
      "active":   { cls: "badge--ativo",     txt: "[ATIVO]" },
      "archived": { cls: "badge--arquivado", txt: "[ARQUIVADO]" }
    };
    var entry = map[status] || { cls: "badge--arquivado", txt: "[" + String(status).toUpperCase() + "]" };
    return '<span class="badge ' + entry.cls + '">' + entry.txt + "</span>";
  }

  // ---------- Carregar lista ----------
  function loadPersons() {
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
          throw new Error("Falha ao listar pessoas (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        state.persons = Array.isArray(data) ? data : [];
        renderTable();
      })
      .catch(function (err) {
        console.error("[persons] erro ao carregar lista", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível carregar a lista de pessoas.");
        }
      });
  }

  function findPerson(id) {
    for (var i = 0; i < state.persons.length; i++) {
      if (state.persons[i].id === id) return state.persons[i];
    }
    return null;
  }

  // ---------- Renderização da tabela ----------
  function renderTable() {
    tbodyEl.innerHTML = "";
    countEl.textContent = String(state.persons.length).padStart(2, "0") + " REGISTROS";
    emptyEl.hidden = state.persons.length > 0;

    state.persons.forEach(function (p) {
      tbodyEl.appendChild(buildRow(p));
    });
  }

  function buildRow(p) {
    var tr = document.createElement("tr");

    var tdName = document.createElement("td");
    tdName.textContent = p.full_name;
    tr.appendChild(tdName);

    var tdAliases = document.createElement("td");
    tdAliases.className = "mono text-secondary";
    tdAliases.textContent = formatAliasesDisplay(p.aliases);
    tr.appendChild(tdAliases);

    var tdCpf = document.createElement("td");
    tdCpf.className = "mono";
    tdCpf.textContent = formatCpfDisplay(p.cpf);
    tr.appendChild(tdCpf);

    var tdStatus = document.createElement("td");
    tdStatus.innerHTML = statusBadgeHtml(p.status);
    tr.appendChild(tdStatus);

    var tdCreated = document.createElement("td");
    tdCreated.className = "mono";
    tdCreated.textContent = formatDateTime(p.created_at);
    tr.appendChild(tdCreated);

    var tdAction = document.createElement("td");

    // "Abrir" desabilitado — tela de detalhe de Pessoa ainda não existe.
    var openBtn = document.createElement("button");
    openBtn.className = "btn btn--text";
    openBtn.type = "button";
    openBtn.textContent = "Abrir";
    openBtn.disabled = true;
    openBtn.title = "Detalhe da pessoa — sub-passo futuro";
    tdAction.appendChild(openBtn);

    var editBtn = document.createElement("button");
    editBtn.className = "btn btn--text";
    editBtn.type = "button";
    editBtn.textContent = "Editar";
    editBtn.style.marginLeft = "var(--space-2)";
    editBtn.addEventListener("click", function () { openModalEdit(p); });
    tdAction.appendChild(editBtn);

    if (p.status !== "archived") {
      var archiveBtn = document.createElement("button");
      archiveBtn.className = "btn btn--text";
      archiveBtn.type = "button";
      archiveBtn.textContent = "Arquivar";
      archiveBtn.style.marginLeft = "var(--space-2)";
      archiveBtn.addEventListener("click", function () { openArchiveModal(p); });
      tdAction.appendChild(archiveBtn);
    }

    tr.appendChild(tdAction);
    return tr;
  }

  // ---------- Ordenação por cabeçalho ----------
  // Só as colunas que a API aceita (person_service._SORTABLE): full_name,
  // created_at, status. Aliases e CPF não são ordenáveis no backend.
  function setupSortHeaders() {
    var headers = document.querySelectorAll("th[data-sort-key]");
    headers.forEach(function (th) {
      th.addEventListener("click", function () {
        var key = th.getAttribute("data-sort-key");
        if (state.sortBy === key) {
          state.descending = !state.descending;
        } else {
          state.sortBy = key;
          state.descending = false;
        }
        updateSortIndicators();
        loadPersons();
      });
    });
    updateSortIndicators();
  }

  function updateSortIndicators() {
    document.querySelectorAll("th[data-sort-key]").forEach(function (th) {
      var indicator = th.querySelector(".sort-indicator");
      if (!indicator) return;
      if (th.getAttribute("data-sort-key") === state.sortBy) {
        indicator.textContent = state.descending ? "▼" : "▲";
      } else {
        indicator.textContent = "";
      }
    });
  }

  function updateTitleLabel() {
    titleLabelEl.textContent = state.includeArchived
      ? "─── TODAS AS PESSOAS ───"
      : "─── PESSOAS ATIVAS ───";
  }

  // ---------- Modal criar/editar (dual) ----------
  function readForm() {
    return {
      full_name: formNameEl.value.trim(),
      aliases: formAliasesEl.value.trim() || null,
      cpf: formCpfEl.value.trim() || null,
      rg: formRgEl.value.trim() || null,
      source: formSourceEl.value.trim() || null,
      reliability_level: formReliabilityEl.value || null,
      notes: formNotesEl.value.trim() || null,
    };
  }

  function fillForm(p) {
    formNameEl.value = p.full_name || "";
    formAliasesEl.value = p.aliases || "";
    formCpfEl.value = p.cpf || "";
    formRgEl.value = p.rg || "";
    formSourceEl.value = p.source || "";
    formReliabilityEl.value = p.reliability_level || "pending";
    formNotesEl.value = p.notes || "";
  }

  function clearForm() {
    formNameEl.value = "";
    formAliasesEl.value = "";
    formCpfEl.value = "";
    formRgEl.value = "";
    formSourceEl.value = "";
    formReliabilityEl.value = "pending";
    formNotesEl.value = "";
    formNameErrorEl.hidden = true;
  }

  function validateName() {
    var valid = formNameEl.value.trim().length > 0;
    saveBtnEl.disabled = !valid;
    return valid;
  }

  function openModalCreate() {
    editingId = null;
    modalTitleEl.textContent = "NOVA PESSOA";
    modalSubtitleEl.textContent = "RF-002 · Apenas o nome completo é obrigatório";
    clearForm();
    validateName();
    modalEl.setAttribute("data-open", "true");
    formNameEl.focus();
  }

  function openModalEdit(p) {
    editingId = p.id;
    modalTitleEl.textContent = "EDITAR PESSOA";
    modalSubtitleEl.textContent = "RF-002 · Editando " + p.full_name;
    fillForm(p);
    validateName();
    modalEl.setAttribute("data-open", "true");
    formNameEl.focus();
  }

  function closeModal() {
    modalEl.setAttribute("data-open", "false");
    editingId = null;
  }

  function showFieldError(message) {
    formNameErrorEl.textContent = message;
    formNameErrorEl.hidden = false;
  }

  // CA-002.5 (decisão do operador, 9.5): 409 -> toast citando a pessoa
  // existente. Sem ação direta (não há tela de detalhe de Pessoa ainda).
  function handleDuplicateCpf(body) {
    var info = (body && body.detail) || {};
    var nome = info.existing_person_name || "outra pessoa";
    if (window.CIRCE && window.CIRCE.toast) {
      window.CIRCE.toast.error(
        "CPF já cadastrado",
        "Este CPF já pertence a " + nome + "."
      );
    }
  }

  function submitForm() {
    if (!validateName()) return;
    var payload = readForm();
    var isEdit = editingId !== null;
    var url = isEdit ? API_BASE + "/" + editingId : API_BASE;
    var method = isEdit ? "PATCH" : "POST";

    saveBtnEl.disabled = true;

    fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return { __redirected: true };
        return response.json().then(function (body) {
          return { status: response.status, ok: response.ok, body: body };
        });
      })
      .then(function (result) {
        if (result.__redirected) return;
        if (result.status === 409) {
          handleDuplicateCpf(result.body);
          return;
        }
        if (!result.ok) {
          var msg = (result.body && result.body.detail) || "Falha ao salvar pessoa.";
          if (window.CIRCE && window.CIRCE.toast) {
            window.CIRCE.toast.error("Erro", typeof msg === "string" ? msg : JSON.stringify(msg));
          }
          return;
        }
        closeModal();
        loadPersons();
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.success(
            isEdit ? "Pessoa atualizada" : "Pessoa criada",
            result.body.full_name
          );
        }
      })
      .catch(function (err) {
        console.error("[persons] erro ao salvar", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível salvar a pessoa.");
        }
      })
      .finally(function () {
        saveBtnEl.disabled = false;
        validateName();
      });
  }

  // ---------- Modal de arquivamento ----------
  function openArchiveModal(p) {
    pendingArchiveId = p.id;
    archiveNameEl.textContent = p.full_name;
    archiveModalEl.setAttribute("data-open", "true");
  }

  function closeArchiveModal() {
    archiveModalEl.setAttribute("data-open", "false");
    pendingArchiveId = null;
  }

  function confirmArchive() {
    if (pendingArchiveId === null) return;
    var id = pendingArchiveId;

    fetch(API_BASE + "/" + id, {
      method: "DELETE",
      headers: { "Accept": "application/json" },
      credentials: "same-origin",
    })
      .then(function (response) {
        if (handleAuthLapse(response)) return null;
        if (!response.ok) {
          throw new Error("Falha ao arquivar (HTTP " + response.status + ").");
        }
        return response.json();
      })
      .then(function (data) {
        if (data === null) return;
        closeArchiveModal();
        loadPersons();
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.success("Pessoa arquivada", data.full_name);
        }
      })
      .catch(function (err) {
        console.error("[persons] erro ao arquivar", err);
        if (window.CIRCE && window.CIRCE.toast) {
          window.CIRCE.toast.error("Erro", "Não foi possível arquivar a pessoa.");
        }
      });
  }

  // ---------- Inicialização ----------
  function setup() {
    tbodyEl = document.getElementById("persons-tbody");
    if (!tbodyEl) return; // não é a tela de pessoas

    emptyEl = document.getElementById("persons-empty");
    countEl = document.getElementById("persons-count");
    titleLabelEl = document.getElementById("persons-title-label");
    showArchivedEl = document.getElementById("persons-show-archived");
    newBtnEl = document.getElementById("persons-new-btn");

    modalEl = document.getElementById("person-create-modal");
    modalTitleEl = document.getElementById("person-create-title");
    modalSubtitleEl = document.getElementById("person-create-subtitle");
    saveBtnEl = document.getElementById("person-form-save");
    formNameEl = document.getElementById("person-form-name");
    formNameErrorEl = document.getElementById("person-form-name-error");
    formAliasesEl = document.getElementById("person-form-aliases");
    formCpfEl = document.getElementById("person-form-cpf");
    formRgEl = document.getElementById("person-form-rg");
    formSourceEl = document.getElementById("person-form-source");
    formReliabilityEl = document.getElementById("person-form-reliability");
    formNotesEl = document.getElementById("person-form-notes");

    archiveModalEl = document.getElementById("person-archive-modal");
    archiveNameEl = document.getElementById("person-archive-name");
    archiveConfirmBtnEl = document.getElementById("person-archive-confirm");

    newBtnEl.addEventListener("click", openModalCreate);
    formNameEl.addEventListener("input", validateName);
    saveBtnEl.addEventListener("click", submitForm);
    archiveConfirmBtnEl.addEventListener("click", confirmArchive);

    // Fecha modal ao clicar em [data-modal-close] / [data-archive-cancel]
    // ou no backdrop (fora do card) — mesmo padrão da casa.
    modalEl.addEventListener("click", function (e) {
      if (e.target === modalEl || e.target.hasAttribute("data-modal-close")) {
        closeModal();
      }
    });
    archiveModalEl.addEventListener("click", function (e) {
      if (e.target === archiveModalEl || e.target.hasAttribute("data-archive-cancel")) {
        closeArchiveModal();
      }
    });

    showArchivedEl.addEventListener("change", function () {
      state.includeArchived = showArchivedEl.checked;
      updateTitleLabel();
      loadPersons();
    });

    // Teclado: Esc fecha o modal aberto; Ctrl+Alt+P abre "Nova pessoa".
    // Atalho nasce em Ctrl+Alt+P (não Ctrl+P) — Ctrl+P é "imprimir" do
    // navegador, mesmo problema já resolvido para "Novo caso" no 8.6.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (archiveModalEl.getAttribute("data-open") === "true") {
          e.preventDefault();
          closeArchiveModal();
          return;
        }
        if (modalEl.getAttribute("data-open") === "true") {
          e.preventDefault();
          closeModal();
          return;
        }
      }
      if (e.altKey && !e.metaKey && (e.key === "p" || e.key === "P")) {
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
    loadPersons();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
