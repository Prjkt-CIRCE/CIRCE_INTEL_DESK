/**
 * CIRCE Intel Desk — inatividade + Ctrl+L (RF-021).
 *
 * Responsabilidades:
 *  - Detectar inatividade do operador e redirecionar para /lock
 *    (CA-021.7).
 *  - Capturar Ctrl+L e disparar o mesmo fluxo (CA-021.8).
 *
 * Lê configuração via data-attributes do <body>, injetados pelo
 * template base autenticado (auth_base.html não, mas o base.html
 * da shell — sub-passo 6.8):
 *
 *   <body data-inactivity-minutes="5" data-page-public="false">
 *
 * Comportamento por valor de data-inactivity-minutes:
 *   - número > 0 : arma o timer com esse intervalo.
 *   - 0 (D33)    : "nunca bloquear" — timer NÃO é armado.
 *   - ausente/inválido : trata como 0 (fail-safe).
 *
 * Em páginas públicas (data-page-public="true"), o script é no-op
 * integral: não arma timer, não captura Ctrl+L. Faz sentido — /login,
 * /setup e /lock já SÃO o portão; lock dentro do portão é absurdo.
 *
 * Sprint 01 — Bloco 6.7.
 *
 * MVP-0: vanilla JS, sem build step, sem framework (ADR-001).
 */
(function () {
  "use strict";

  // ----------------------------------------------------------------
  // Configuração — lida do DOM
  // ----------------------------------------------------------------

  const body = document.body;
  const isPublicPage = body.dataset.pagePublic === "true";

  // Em páginas de portão, encerra silenciosamente.
  if (isPublicPage) {
    return;
  }

  const rawMinutes = body.dataset.inactivityMinutes;
  const minutes = parseInt(rawMinutes, 10);

  // D33: minutes inválido OU <= 0 significa "nunca bloquear" para o
  // timer. Ctrl+L manual continua funcionando independentemente.
  const inactivityEnabled = Number.isFinite(minutes) && minutes > 0;
  const inactivityMs = inactivityEnabled ? minutes * 60 * 1000 : 0;

  // Janela mínima entre resets do timer por evento de atividade.
  // mousemove dispara 60+x/s; sem throttle, vira pressão no event
  // loop. 1 segundo é imperceptível para o operador.
  const RESET_THROTTLE_MS = 1000;

  // ----------------------------------------------------------------
  // Helpers
  // ----------------------------------------------------------------

  /**
   * Monta o URL de bloqueio preservando a página atual em ?from=
   * (CA-021.7: "sem perda de estado"). Usa pathname + search;
   * deliberadamente NÃO inclui o hash (fragmentos JS internos não
   * são parte da rota servida).
   */
  function buildLockUrl() {
    const current = window.location.pathname + window.location.search;
    return "/lock?from=" + encodeURIComponent(current);
  }

  /**
   * Aciona o lock. Single source of truth: timer e Ctrl+L caem aqui.
   * Usa window.location.assign para deixar a entrada no histórico
   * do navegador — o operador pode usar "voltar" após reautenticar
   * (comportamento natural, não exigido pelo CA).
   */
  function goToLock() {
    window.location.assign(buildLockUrl());
  }

  // ----------------------------------------------------------------
  // Timer de inatividade (CA-021.7)
  // ----------------------------------------------------------------

  let inactivityTimerId = null;
  let lastResetAt = 0;

  function armTimer() {
    if (!inactivityEnabled) return;
    inactivityTimerId = window.setTimeout(goToLock, inactivityMs);
  }

  function resetTimer() {
    if (!inactivityEnabled) return;
    const now = Date.now();
    if (now - lastResetAt < RESET_THROTTLE_MS) return;
    lastResetAt = now;
    if (inactivityTimerId !== null) {
      window.clearTimeout(inactivityTimerId);
    }
    armTimer();
  }

  if (inactivityEnabled) {
    // Eventos que sinalizam "operador ativo".
    // - mousemove / mousedown : interação com mouse.
    // - keydown               : digitação.
    // - scroll                : leitura ativa.
    // - touchstart            : tablets com touch (improvável, mas
    //                           barato cobrir).
    // - visibilitychange      : voltar à aba após estar em outra.
    const ACTIVITY_EVENTS = [
      "mousemove",
      "mousedown",
      "keydown",
      "scroll",
      "touchstart",
      "visibilitychange",
    ];
    ACTIVITY_EVENTS.forEach(function (evt) {
      // passive: true onde aplicável — sinaliza ao navegador que
      // o handler não chama preventDefault, permitindo scroll
      // suave em dispositivos touch.
      window.addEventListener(evt, resetTimer, { passive: true });
    });

    armTimer();
  }

  // ----------------------------------------------------------------
  // Atalho Ctrl+L (CA-021.8) — independente do timer
  // ----------------------------------------------------------------

  /**
   * Ctrl+L no navegador foca a barra de URL por padrão. preventDefault
   * impede isso. stopPropagation evita que outros handlers em camadas
   * acima (command palette, etc) também recebam o evento.
   *
   * Coordenação com a Sprint 0.5:
   * - Ctrl+K (command palette): tecla diferente, sem colisão.
   * - Ctrl+? (modal de atalhos): tecla diferente, sem colisão.
   *
   * Importante: capturar tanto e.ctrlKey quanto e.metaKey (Cmd no
   * macOS). O CIRCE roda em Windows hoje, mas o operador pode usar
   * em outras máquinas no futuro.
   */
  window.addEventListener(
    "keydown",
    function (e) {
      const isCtrlOrCmd = e.ctrlKey || e.metaKey;
      // e.key é case-sensitive; com Shift vira "L" maiúsculo.
      // toLowerCase normaliza.
      const isL = (e.key || "").toLowerCase() === "l";
      if (isCtrlOrCmd && isL) {
        e.preventDefault();
        e.stopPropagation();
        goToLock();
      }
    },
    // capture: true — recebe o evento ANTES de qualquer handler
    // em bubble phase. Garante que stopPropagation funcione contra
    // listeners de outros scripts da shell (command palette, etc).
    { capture: true }
  );
})();