/* documents_in_case.js - RF-007, Sprint 01-B sub-passo 02-5 */
/* AT-03.7: coluna Platea com toggle [NAO COMPARTILHAR] adicionada */
/* RF-011: botao OCR + painel de validacao (Sprint 04, sub-passo 04-5) */
(function () {
  "use strict";

  var API_BASE  = "/api/documents";
  var API_CASES = "/api/cases";
  var caseId = null;

  // Formatos que suportam OCR (RF-011)
  var OCR_FORMATS = ["pdf", "jpg", "jpeg", "png"];

  // Timers de polling OCR por document_id
  var ocrPollTimers = {};

  // document_id do doc atualmente aberto no modal OCR
  var ocrCurrentDocId = null;

  // --- Elementos de layout ---
  var sectionEl, loadingEl, emptyEl, tableEl, tbodyEl, importBtnEl;

  // --- Modal de importacao ---
  var backdropEl, cancelBtnEl, confirmarBtnEl;
  var fileInputEl, titleInputEl, notesInputEl;
  var dupWarningEl, dupMsgEl, forceDupCbEl;

  // --- Modal OCR ---
  var ocrBackdropEl, ocrCloseBtnEl;
  var ocrSubtitleEl;
  var ocrStatusBadgeEl, ocrValidationBadgeEl, ocrEngineLabelEl;
  var ocrEditAreaEl, ocrTextInputEl;
  var ocrReadonlyAreaEl, ocrReadonlyLabelEl, ocrTextDisplayEl;
  var ocrRejectAreaEl, ocrRejectReasonEl, ocrRejectCancelEl, ocrRejectConfirmEl;
  var ocrRejectedInfoEl, ocrRejectionReasonDisplayEl;
  var ocrActionBtnsEl, ocrBtnValidarEl, ocrBtnRejeitarEl;

  // ---------------------------------------------------------------------------
  // Utilitarios
  // ---------------------------------------------------------------------------

  function handleAuthLapse(r) {
    if (r.status === 401 || r.redirected) {
      window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
      return true;
    }
    return false;
  }

  function toast(msg, tipo) {
    if (window.CIRCE && window.CIRCE.toast) {
      if (tipo === "success") window.CIRCE.toast.success(msg, "");
      else if (tipo === "error") window.CIRCE.toast.error(msg, "");
      else if (tipo === "warning") window.CIRCE.toast.warning(msg, "");
      else window.CIRCE.toast.info(msg, "");
    }
  }

  function escapeHtml(s) {
    if (!s) return "";
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function formatBytes(bytes) {
    if (bytes === null || bytes === undefined) return "--";
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + " MB";
    if (bytes >= 1024)    return (bytes / 1024).toFixed(0) + " KB";
    return bytes + " B";
  }

  function formatDate(iso) {
    if (!iso) return "--";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear() +
           " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  // ---------------------------------------------------------------------------
  // Platea (AT-03.7)
  // ---------------------------------------------------------------------------

  function updatePlateaBadge(spanEl, excluded) {
    if (!spanEl) return;
    if (excluded) {
      spanEl.className = "badge badge--arquivado";
      spanEl.style.fontSize = "0.7rem";
      spanEl.textContent = "[NAO COMPARTILHAR]";
    } else {
      spanEl.className = "badge";
      spanEl.style.fontSize = "0.7rem";
      spanEl.style.opacity = "0.4";
      spanEl.textContent = "[COMPARTILHAR]";
    }
  }

  function toggleDocPlateaExclude(docId, btnEl, badgeSpanEl) {
    var currentExcluded = btnEl.dataset.excluded === "1";
    var novoExclude = !currentExcluded;
    btnEl.disabled = true;
    fetch(
      API_CASES + "/" + encodeURIComponent(caseId) +
      "/items/document/" + encodeURIComponent(docId) +
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
        updatePlateaBadge(badgeSpanEl, data.platea_exclude);
        btnEl.dataset.excluded = data.platea_exclude ? "1" : "0";
        btnEl.textContent = data.platea_exclude ? "Liberar" : "Excluir";
        btnEl.title = data.platea_exclude
          ? "Clique para permitir compartilhamento"
          : "Clique para excluir da Platea";
        var msg = data.platea_exclude
          ? "Documento marcado como [NAO COMPARTILHAR]."
          : "Documento removido de [NAO COMPARTILHAR].";
        toast(msg, "success");
      })
      .catch(function (err) {
        console.error("[documents_in_case] erro ao atualizar platea_exclude", err);
        toast("Erro ao atualizar item.", "error");
      })
      .finally(function () {
        btnEl.disabled = false;
      });
  }

  // ---------------------------------------------------------------------------
  // Integridade
  // ---------------------------------------------------------------------------

  function verifyDoc(docId, cell) {
    cell.textContent = "...";
    fetch(API_BASE + "/detail/" + docId + "/verify", { credentials: "same-origin" })
      .then(function (r) { if (handleAuthLapse(r)) return null; return r.json(); })
      .then(function (data) {
        if (data === null) return;
        if (data.ok) {
          cell.innerHTML = '<span style="color:var(--color-success,green)">OK</span>';
        } else if (data.error === "file_missing") {
          cell.innerHTML = '<span style="color:var(--accent)">AUSENTE</span>';
        } else if (data.error === "hash_mismatch") {
          cell.innerHTML = '<span style="color:var(--accent)">ADULTERADO</span>';
        } else {
          cell.innerHTML = '<span class="text-tertiary">-</span>';
        }
      })
      .catch(function () { cell.textContent = "Erro"; });
  }

  // ---------------------------------------------------------------------------
  // OCR — botao e estado (RF-011, Sprint 04-5)
  // ---------------------------------------------------------------------------

  function isOcrFormat(fmt) {
    return OCR_FORMATS.indexOf((fmt || "").toLowerCase()) !== -1;
  }

  function createOcrBtn(doc) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn--text";
    btn.style.cssText = "font-size: var(--text-sm); color: var(--text-tertiary); margin-left: var(--space-2);";
    btn.id = "ocr-btn-" + doc.id;
    btn.dataset.ocrState = "idle";
    btn.textContent = "[OCR]";
    btn.addEventListener("click", function () { handleOcrClick(doc, btn); });
    return btn;
  }

  function setOcrBtnState(btn, state) {
    if (!btn) return;
    btn.dataset.ocrState = state;
    switch (state) {
      case "idle":
        btn.textContent = "[OCR]";
        btn.disabled = false;
        btn.style.color = "var(--text-tertiary)";
        break;
      case "triggering":
        btn.textContent = "[iniciando...]";
        btn.disabled = true;
        btn.style.color = "var(--text-tertiary)";
        break;
      case "processing":
        btn.textContent = "[processando...]";
        btn.disabled = true;
        btn.style.color = "var(--accent)";
        break;
      case "done":
        btn.textContent = "[ver OCR]";
        btn.disabled = false;
        btn.style.color = "var(--accent)";
        break;
      case "validated":
        btn.textContent = "[OCR ok]";
        btn.disabled = false;
        btn.style.color = "var(--color-success, green)";
        break;
      case "rejected":
        btn.textContent = "[OCR rejeit.]";
        btn.disabled = false;
        btn.style.color = "var(--text-tertiary)";
        break;
    }
  }

  function applyOcrDataToBtn(data, btn, docId) {
    if (data.ocr_status === "processing" || data.ocr_status === "pending") {
      setOcrBtnState(btn, "processing");
      startOcrPolling(docId, btn);
    } else if (data.ocr_status === "done") {
      stopOcrPolling(docId);
      if (data.validation_status === "validated") {
        setOcrBtnState(btn, "validated");
      } else if (data.validation_status === "rejected") {
        setOcrBtnState(btn, "rejected");
      } else {
        setOcrBtnState(btn, "done");
      }
    } else {
      setOcrBtnState(btn, "idle");
    }
    // Atualiza modal se estiver aberto para este documento
    if (ocrCurrentDocId === docId && ocrBackdropEl && ocrBackdropEl.dataset.open === "true") {
      populateOcrModal(data);
    }
  }

  function checkOcrStatus(docId, btn) {
    fetch(API_BASE + "/" + docId + "/ocr", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 404) return null; // OCR nao disparado ainda
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (data === null) {
          setOcrBtnState(btn, "idle");
          return;
        }
        applyOcrDataToBtn(data, btn, docId);
      })
      .catch(function () {
        setOcrBtnState(btn, "idle");
      });
  }

  function startOcrPolling(docId, btn) {
    if (ocrPollTimers[docId]) return; // ja esta em polling
    ocrPollTimers[docId] = setInterval(function () {
      fetch(API_BASE + "/" + docId + "/ocr", { credentials: "same-origin" })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (data) {
          if (data.ocr_status !== "processing" && data.ocr_status !== "pending") {
            stopOcrPolling(docId);
            applyOcrDataToBtn(data, btn, docId);
            if (data.ocr_status === "done") {
              toast("OCR concluido. Clique em [ver OCR] para validar.", "success");
            }
          }
        })
        .catch(function () {
          stopOcrPolling(docId);
          setOcrBtnState(btn, "idle");
        });
    }, 3000);
  }

  function stopOcrPolling(docId) {
    if (ocrPollTimers[docId]) {
      clearInterval(ocrPollTimers[docId]);
      delete ocrPollTimers[docId];
    }
  }

  function handleOcrClick(doc, btn) {
    var state = btn.dataset.ocrState;
    // Se ja tem resultado — abre o modal
    if (state === "done" || state === "validated" || state === "rejected") {
      openOcrModal(doc.id, doc.original_filename, doc.title);
      return;
    }
    // idle → dispara OCR
    setOcrBtnState(btn, "triggering");
    fetch(API_BASE + "/" + doc.id + "/ocr", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Accept": "application/json" }
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (r.status === 409) {
          // Ja existe — consulta estado atual
          checkOcrStatus(doc.id, btn);
          return null;
        }
        if (!r.ok) {
          return r.json().then(function (j) {
            throw new Error((j && j.detail) ? String(j.detail) : "HTTP " + r.status);
          });
        }
        return r.json();
      })
      .then(function (data) {
        if (data === null) return;
        setOcrBtnState(btn, "processing");
        startOcrPolling(doc.id, btn);
        toast("OCR iniciado. Aguarde...", "info");
      })
      .catch(function (err) {
        toast("Erro ao disparar OCR: " + (err.message || err), "error");
        setOcrBtnState(btn, "idle");
      });
  }

  // ---------------------------------------------------------------------------
  // OCR — Modal (RF-011)
  // ---------------------------------------------------------------------------

  function openOcrModal(docId, filename, title) {
    ocrCurrentDocId = docId;
    var displayName = title || filename || ("Documento #" + docId);
    if (ocrSubtitleEl) ocrSubtitleEl.textContent = displayName;
    // Reset para estado de loading
    if (ocrStatusBadgeEl)     { ocrStatusBadgeEl.textContent = "carregando..."; ocrStatusBadgeEl.className = "badge mono"; ocrStatusBadgeEl.style.color = ""; }
    if (ocrValidationBadgeEl) { ocrValidationBadgeEl.textContent = "---"; ocrValidationBadgeEl.className = "badge mono"; ocrValidationBadgeEl.style.color = ""; }
    if (ocrEngineLabelEl)  ocrEngineLabelEl.textContent  = "";
    if (ocrEditAreaEl)     ocrEditAreaEl.hidden     = true;
    if (ocrReadonlyAreaEl) ocrReadonlyAreaEl.hidden = true;
    if (ocrRejectAreaEl)   ocrRejectAreaEl.hidden   = true;
    if (ocrRejectedInfoEl) ocrRejectedInfoEl.hidden = true;
    if (ocrActionBtnsEl)   ocrActionBtnsEl.style.display = "none";
    if (ocrBtnValidarEl)   ocrBtnValidarEl.disabled  = false;
    if (ocrBtnRejeitarEl)  ocrBtnRejeitarEl.disabled = false;
    if (ocrRejectReasonEl) ocrRejectReasonEl.value   = "";
    if (ocrBackdropEl) ocrBackdropEl.dataset.open = "true";
    fetch(API_BASE + "/" + docId + "/ocr", { credentials: "same-origin" })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (data === null) return;
        populateOcrModal(data);
      })
      .catch(function () {
        if (ocrStatusBadgeEl) ocrStatusBadgeEl.textContent = "erro ao carregar";
        toast("Erro ao carregar dados OCR.", "error");
      });
  }

  function populateOcrModal(data) {
    // Badge de status
    if (ocrStatusBadgeEl) {
      ocrStatusBadgeEl.textContent = data.ocr_status || "---";
      ocrStatusBadgeEl.className = "badge mono";
      if (data.ocr_status === "done")       ocrStatusBadgeEl.style.color = "var(--color-success, green)";
      else if (data.ocr_status === "processing") ocrStatusBadgeEl.style.color = "var(--accent)";
      else                                       ocrStatusBadgeEl.style.color = "";
    }
    // Badge de validacao
    if (ocrValidationBadgeEl) {
      ocrValidationBadgeEl.textContent = data.validation_status || "---";
      ocrValidationBadgeEl.className = "badge mono";
      if (data.validation_status === "validated") ocrValidationBadgeEl.style.color = "var(--color-success, green)";
      else if (data.validation_status === "rejected") ocrValidationBadgeEl.style.color = "var(--accent)";
      else                                            ocrValidationBadgeEl.style.color = "";
    }
    // Engine
    if (ocrEngineLabelEl) {
      ocrEngineLabelEl.textContent = data.engine ? "engine: " + data.engine : "";
    }
    // Reset areas de conteudo
    if (ocrEditAreaEl)     ocrEditAreaEl.hidden     = true;
    if (ocrReadonlyAreaEl) ocrReadonlyAreaEl.hidden = true;
    if (ocrRejectAreaEl)   ocrRejectAreaEl.hidden   = true;
    if (ocrRejectedInfoEl) ocrRejectedInfoEl.hidden = true;
    if (ocrActionBtnsEl)   ocrActionBtnsEl.style.display = "none";

    var isPending   = data.validation_status === "pending"   && data.ocr_status === "done";
    var isValidated = data.validation_status === "validated";
    var isRejected  = data.validation_status === "rejected";

    if (isPending) {
      if (ocrTextInputEl) ocrTextInputEl.value = data.raw_text || "";
      if (ocrEditAreaEl)  ocrEditAreaEl.hidden = false;
      if (ocrActionBtnsEl) ocrActionBtnsEl.style.display = "flex";
    } else if (isValidated) {
      if (ocrReadonlyLabelEl) ocrReadonlyLabelEl.textContent = "Texto validado:";
      if (ocrTextDisplayEl)   ocrTextDisplayEl.textContent   = data.validated_text || "(vazio)";
      if (ocrReadonlyAreaEl)  ocrReadonlyAreaEl.hidden = false;
    } else if (isRejected) {
      if (ocrReadonlyLabelEl) ocrReadonlyLabelEl.textContent = "Texto extraido (rejeitado):";
      if (ocrTextDisplayEl)   ocrTextDisplayEl.textContent   = data.raw_text || "(sem texto extraido)";
      if (ocrReadonlyAreaEl)  ocrReadonlyAreaEl.hidden = false;
      if (ocrRejectionReasonDisplayEl) ocrRejectionReasonDisplayEl.textContent = data.rejection_reason || "-";
      if (ocrRejectedInfoEl) ocrRejectedInfoEl.hidden = false;
    } else {
      // processing ou outro — mostra o que tiver
      if (ocrReadonlyLabelEl) ocrReadonlyLabelEl.textContent = "Texto extraido:";
      if (ocrTextDisplayEl)   ocrTextDisplayEl.textContent   = data.raw_text || "(aguardando extracao...)";
      if (ocrReadonlyAreaEl)  ocrReadonlyAreaEl.hidden = false;
    }
  }

  function closeOcrModal() {
    if (ocrBackdropEl) ocrBackdropEl.dataset.open = "false";
    ocrCurrentDocId = null;
    if (ocrRejectAreaEl)   ocrRejectAreaEl.hidden   = true;
    if (ocrRejectReasonEl) ocrRejectReasonEl.value  = "";
    if (ocrBtnValidarEl)   ocrBtnValidarEl.disabled  = false;
    if (ocrBtnRejeitarEl)  ocrBtnRejeitarEl.disabled = false;
  }

  function submitValidate() {
    if (!ocrCurrentDocId) return;
    var text = ocrTextInputEl ? ocrTextInputEl.value.trim() : "";
    if (!text) {
      toast("O texto validado nao pode estar vazio.", "warning");
      return;
    }
    if (ocrBtnValidarEl)  ocrBtnValidarEl.disabled  = true;
    if (ocrBtnRejeitarEl) ocrBtnRejeitarEl.disabled = true;
    fetch(API_BASE + "/" + ocrCurrentDocId + "/ocr/validate", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ action: "validate", validated_text: text })
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) {
          return r.json().then(function (j) {
            throw new Error((j && j.detail) ? String(j.detail) : "HTTP " + r.status);
          });
        }
        return r.json();
      })
      .then(function (data) {
        if (data === null) return;
        toast("Texto OCR validado com sucesso.", "success");
        populateOcrModal(data);
        var btn = document.getElementById("ocr-btn-" + ocrCurrentDocId);
        if (btn) setOcrBtnState(btn, "validated");
      })
      .catch(function (err) {
        toast("Erro ao validar: " + (err.message || err), "error");
        if (ocrBtnValidarEl)  ocrBtnValidarEl.disabled  = false;
        if (ocrBtnRejeitarEl) ocrBtnRejeitarEl.disabled = false;
      });
  }

  function showRejectArea() {
    if (ocrRejectAreaEl) ocrRejectAreaEl.hidden = false;
    if (ocrBtnRejeitarEl) ocrBtnRejeitarEl.disabled = true;
    if (ocrBtnValidarEl)  ocrBtnValidarEl.disabled  = true;
    if (ocrRejectReasonEl) ocrRejectReasonEl.focus();
  }

  function hideRejectArea() {
    if (ocrRejectAreaEl)   ocrRejectAreaEl.hidden  = true;
    if (ocrRejectReasonEl) ocrRejectReasonEl.value = "";
    if (ocrBtnRejeitarEl)  ocrBtnRejeitarEl.disabled = false;
    if (ocrBtnValidarEl)   ocrBtnValidarEl.disabled  = false;
  }

  function submitReject() {
    if (!ocrCurrentDocId) return;
    var reason = ocrRejectReasonEl ? ocrRejectReasonEl.value.trim() : "";
    if (!reason) {
      toast("Informe o motivo da rejeicao.", "warning");
      return;
    }
    if (ocrRejectConfirmEl) ocrRejectConfirmEl.disabled = true;
    fetch(API_BASE + "/" + ocrCurrentDocId + "/ocr/validate", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ action: "reject", rejection_reason: reason })
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) {
          return r.json().then(function (j) {
            throw new Error((j && j.detail) ? String(j.detail) : "HTTP " + r.status);
          });
        }
        return r.json();
      })
      .then(function (data) {
        if (data === null) return;
        toast("Texto OCR rejeitado.", "success");
        hideRejectArea();
        populateOcrModal(data);
        var btn = document.getElementById("ocr-btn-" + ocrCurrentDocId);
        if (btn) setOcrBtnState(btn, "rejected");
      })
      .catch(function (err) {
        toast("Erro ao rejeitar: " + (err.message || err), "error");
      })
      .finally(function () {
        if (ocrRejectConfirmEl) ocrRejectConfirmEl.disabled = false;
      });
  }

  // ---------------------------------------------------------------------------
  // Render de linhas
  // ---------------------------------------------------------------------------

  function renderRows(docs) {
    if (!tbodyEl) return;
    if (!docs || docs.length === 0) {
      if (emptyEl) emptyEl.hidden = false;
      if (tableEl) tableEl.hidden = true;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;
    if (tableEl) tableEl.hidden = false;
    tbodyEl.innerHTML = "";
    docs.forEach(function (doc) {
      var tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-subtle)";
      tr.style.fontSize = "var(--text-sm)";
      var excluded = doc.platea_exclude || false;
      var nomeHtml = doc.title
        ? '<strong>' + escapeHtml(doc.title) + '</strong><br><span class="text-tertiary mono" style="font-size:0.75rem;">' + escapeHtml(doc.original_filename) + '</span>'
        : escapeHtml(doc.original_filename);
      var badgeHtml = '<span class="badge badge--mono">' + escapeHtml((doc.file_format || "").toUpperCase()) + '</span>';
      var tdNome    = '<td style="padding:var(--space-2) var(--space-3);">' + nomeHtml + '</td>';
      var tdFormato = '<td style="padding:var(--space-2) var(--space-3);">' + badgeHtml + '</td>';
      var tdTamanho = '<td style="padding:var(--space-2) var(--space-3);" class="mono text-secondary">' + escapeHtml(formatBytes(doc.file_size)) + '</td>';
      var tdData    = '<td style="padding:var(--space-2) var(--space-3);" class="mono text-secondary">' + escapeHtml(formatDate(doc.imported_at)) + '</td>';
      var tdInteg   = '<td style="padding:var(--space-2) var(--space-3);" class="mono" data-integ="' + doc.id + '"><button type="button" class="btn btn--text" style="font-size:var(--text-sm);">VERIFICAR</button></td>';
      tr.innerHTML = tdNome + tdFormato + tdTamanho + tdData + tdInteg;
      // Celula Platea (AT-03.7)
      var tdPlatea = document.createElement("td");
      tdPlatea.style.cssText = "padding: var(--space-2) var(--space-3); white-space: nowrap;";
      var badgeSpan = document.createElement("span");
      badgeSpan.style.fontSize = "0.7rem";
      if (excluded) {
        badgeSpan.className = "badge badge--arquivado";
        badgeSpan.textContent = "[NAO COMPARTILHAR]";
      } else {
        badgeSpan.className = "badge";
        badgeSpan.style.opacity = "0.4";
        badgeSpan.textContent = "[COMPARTILHAR]";
      }
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
        toggleDocPlateaExclude(doc.id, btnPlatea, badgeSpan);
      });
      tdPlatea.appendChild(badgeSpan);
      tdPlatea.appendChild(btnPlatea);
      tr.appendChild(tdPlatea);
      // Celula Acoes — inclui botao OCR para formatos suportados (RF-011)
      var tdAcoes = document.createElement("td");
      tdAcoes.style.cssText = "padding: var(--space-2) 0 var(--space-2) var(--space-3); white-space: nowrap;";
      if (isOcrFormat(doc.file_format)) {
        tdAcoes.appendChild(createOcrBtn(doc));
      }
      tr.appendChild(tdAcoes);
      // Bind verificacao de integridade
      var integCell = tr.querySelector('[data-integ="' + doc.id + '"]');
      if (integCell) {
        integCell.querySelector("button").addEventListener("click", function () {
          verifyDoc(doc.id, integCell);
        });
      }
      tbodyEl.appendChild(tr);
    });
    // Consulta status OCR de cada documento suportado (async, silencioso)
    docs.forEach(function (doc) {
      if (isOcrFormat(doc.file_format)) {
        var btn = document.getElementById("ocr-btn-" + doc.id);
        if (btn) checkOcrStatus(doc.id, btn);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Carregamento de documentos
  // ---------------------------------------------------------------------------

  function loadDocuments() {
    if (loadingEl) loadingEl.hidden = false;
    if (emptyEl)   emptyEl.hidden   = true;
    if (tableEl)   tableEl.hidden   = true;
    fetch(API_BASE + "/" + caseId, { credentials: "same-origin" })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (loadingEl) loadingEl.hidden = true;
        if (data === null) return;
        renderRows(data);
      })
      .catch(function () {
        if (loadingEl) loadingEl.hidden = true;
        toast("Erro ao carregar documentos.", "error");
      });
  }

  // ---------------------------------------------------------------------------
  // Modal de importacao
  // ---------------------------------------------------------------------------

  function openImportModal() {
    if (fileInputEl)   fileInputEl.value    = "";
    if (titleInputEl)  titleInputEl.value   = "";
    if (notesInputEl)  notesInputEl.value   = "";
    if (forceDupCbEl)  forceDupCbEl.checked = false;
    if (dupWarningEl)  dupWarningEl.hidden   = true;
    if (backdropEl)    backdropEl.dataset.open = "true";
  }

  function closeImportModal() {
    if (backdropEl) backdropEl.dataset.open = "false";
  }

  function submitImport() {
    if (!fileInputEl || !fileInputEl.files || fileInputEl.files.length === 0) {
      toast("Selecione um arquivo.", "warning");
      return;
    }
    var fd = new FormData();
    fd.append("file", fileInputEl.files[0]);
    if (titleInputEl && titleInputEl.value.trim()) fd.append("title", titleInputEl.value.trim());
    if (notesInputEl && notesInputEl.value.trim()) fd.append("notes", notesInputEl.value.trim());
    fd.append("force_duplicate", forceDupCbEl && forceDupCbEl.checked ? "true" : "false");
    if (confirmarBtnEl) confirmarBtnEl.disabled = true;
    fetch(API_BASE + "/" + caseId + "/import", {
      method: "POST",
      credentials: "same-origin",
      body: fd
    })
      .then(function (r) {
        if (handleAuthLapse(r)) return null;
        return r.json().then(function (json) {
          return { status: r.status, ok: r.ok, json: json };
        });
      })
      .then(function (res) {
        if (res === null) return;
        if (res.status === 409) {
          var detail = res.json && res.json.detail ? res.json.detail : {};
          if (dupWarningEl) dupWarningEl.hidden = false;
          if (dupMsgEl) dupMsgEl.textContent = "Ja existe: " + (detail.existing_document_name || "-");
          return;
        }
        if (!res.ok) {
          var msg = (res.json && res.json.detail) ? String(res.json.detail) : String(res.status);
          toast("Erro ao importar: " + msg, "error");
          return;
        }
        closeImportModal();
        toast("Documento importado.", "success");
        loadDocuments();
      })
      .catch(function () {
        toast("Erro ao importar documento.", "error");
      })
      .finally(function () {
        if (confirmarBtnEl) confirmarBtnEl.disabled = false;
      });
  }

  // ---------------------------------------------------------------------------
  // Setup
  // ---------------------------------------------------------------------------

  function setup() {
    sectionEl = document.getElementById("documents-section");
    if (!sectionEl) return;
    var parts = window.location.pathname.split("/").filter(Boolean);
    var rawId = parts[parts.length - 1];
    caseId = parseInt(rawId, 10);
    if (isNaN(caseId)) return;

    // Layout
    loadingEl      = document.getElementById("doc-loading");
    emptyEl        = document.getElementById("doc-empty");
    tableEl        = document.getElementById("doc-table");
    tbodyEl        = document.getElementById("doc-tbody");
    importBtnEl    = document.getElementById("doc-import-btn");

    // Modal importacao
    backdropEl     = document.getElementById("modal-doc-import-backdrop");
    cancelBtnEl    = document.getElementById("modal-doc-cancel");
    confirmarBtnEl = document.getElementById("modal-doc-confirmar");
    fileInputEl    = document.getElementById("doc-file-input");
    titleInputEl   = document.getElementById("doc-title-input");
    notesInputEl   = document.getElementById("doc-notes-input");
    dupWarningEl   = document.getElementById("doc-duplicate-warning");
    dupMsgEl       = document.getElementById("doc-duplicate-msg");
    forceDupCbEl   = document.getElementById("doc-force-duplicate");

    // Modal OCR (RF-011)
    ocrBackdropEl               = document.getElementById("modal-ocr-backdrop");
    ocrCloseBtnEl               = document.getElementById("modal-ocr-close");
    ocrSubtitleEl               = document.getElementById("modal-ocr-subtitle");
    ocrStatusBadgeEl            = document.getElementById("ocr-status-badge");
    ocrValidationBadgeEl        = document.getElementById("ocr-validation-badge");
    ocrEngineLabelEl            = document.getElementById("ocr-engine-label");
    ocrEditAreaEl               = document.getElementById("ocr-edit-area");
    ocrTextInputEl              = document.getElementById("ocr-text-input");
    ocrReadonlyAreaEl           = document.getElementById("ocr-readonly-area");
    ocrReadonlyLabelEl          = document.getElementById("ocr-readonly-label");
    ocrTextDisplayEl            = document.getElementById("ocr-text-display");
    ocrRejectAreaEl             = document.getElementById("ocr-reject-area");
    ocrRejectReasonEl           = document.getElementById("ocr-reject-reason");
    ocrRejectCancelEl           = document.getElementById("ocr-reject-cancel-reason");
    ocrRejectConfirmEl          = document.getElementById("ocr-reject-confirm");
    ocrRejectedInfoEl           = document.getElementById("ocr-rejected-info");
    ocrRejectionReasonDisplayEl = document.getElementById("ocr-rejection-reason-display");
    ocrActionBtnsEl             = document.getElementById("ocr-action-btns");
    ocrBtnValidarEl             = document.getElementById("ocr-btn-validar");
    ocrBtnRejeitarEl            = document.getElementById("ocr-btn-rejeitar");

    // Eventos — modal importacao
    if (importBtnEl)    importBtnEl.addEventListener("click", openImportModal);
    if (cancelBtnEl)    cancelBtnEl.addEventListener("click", closeImportModal);
    if (confirmarBtnEl) confirmarBtnEl.addEventListener("click", submitImport);
    if (backdropEl) {
      backdropEl.addEventListener("click", function (e) {
        if (e.target === backdropEl) closeImportModal();
      });
    }

    // Eventos — modal OCR
    if (ocrCloseBtnEl)     ocrCloseBtnEl.addEventListener("click",  closeOcrModal);
    if (ocrBtnValidarEl)   ocrBtnValidarEl.addEventListener("click",  submitValidate);
    if (ocrBtnRejeitarEl)  ocrBtnRejeitarEl.addEventListener("click", showRejectArea);
    if (ocrRejectCancelEl) ocrRejectCancelEl.addEventListener("click", hideRejectArea);
    if (ocrRejectConfirmEl) ocrRejectConfirmEl.addEventListener("click", submitReject);
    if (ocrBackdropEl) {
      ocrBackdropEl.addEventListener("click", function (e) {
        if (e.target === ocrBackdropEl) closeOcrModal();
      });
    }

    loadDocuments();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
