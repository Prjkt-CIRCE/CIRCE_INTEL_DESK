"""
CIRCE Intel Desk — Serviço de mitigação de força bruta de login.

Mantém contador de tentativas falhas de login por username, em memória
do processo (Decisão A, Bloco 6 §8). Quando o número de falhas dentro
da janela deslizante atinge o limite, o usuário fica bloqueado por
um período configurável.

Decisões herdadas:
- D32-A — parâmetros lidos de settings_service (bruteforce_max_attempts,
  bruteforce_window_seconds, bruteforce_block_seconds).
- §8 Decisão A — estado em memória; reset no restart do servidor é
  aceitável no modelo de ameaças do CIRCE (loopback, single-user).
- §8 Decisão B — chave = username. Usernames inexistentes NÃO devem ser
  registrados aqui (responsabilidade do chamador em api/auth.py); isto
  evita oráculo de enumeração indireta e mantém o comportamento externo
  uniforme entre username válido e inválido (já há hash dummy contra
  timing em api/auth.py).

Concorrência: protegido por threading.Lock. FastAPI/Uvicorn em modo
default usa um único event loop, mas dependências futuras (workers,
BackgroundTasks) podem chamar daqui em paralelo.

Sprint 01 — Bloco 6.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from app.services import settings_service


# ---------------------------------------------------------------------------
# Estado em memória
# ---------------------------------------------------------------------------


@dataclass
class _UserState:
    """Estado por usuário. Privado ao módulo."""

    # Timestamps (epoch float) das tentativas falhas recentes.
    failures: deque[float] = field(default_factory=deque)
    # Epoch em que o bloqueio expira; 0.0 se não está bloqueado.
    blocked_until: float = 0.0


_lock = threading.Lock()
_state: dict[str, _UserState] = {}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _now() -> float:
    """Monotônico não serve — precisamos comparar com janelas relativas
    e isso funciona bem com time.time(). Em prática, ajuste manual de
    relógio do sistema durante o uso do CIRCE não é vetor relevante."""
    return time.time()


def _params() -> tuple[int, int, int]:
    """Lê parâmetros do settings_service. Defaults conservadores se
    settings_service ainda não estiver carregado (lifespan no startup
    garante que estará, mas evitamos crash em casos de borda)."""
    max_attempts = int(settings_service.get_value("bruteforce_max_attempts", 5))
    window = int(settings_service.get_value("bruteforce_window_seconds", 300))
    block = int(settings_service.get_value("bruteforce_block_seconds", 900))
    return max_attempts, window, block


def _get_or_create(username: str) -> _UserState:
    """Retorna o estado do usuário, criando vazio se ainda não existir.
    Assume que o caller já adquiriu o _lock."""
    s = _state.get(username)
    if s is None:
        s = _UserState()
        _state[username] = s
    return s


def _prune_old_failures(state: _UserState, window: int, now: float) -> None:
    """Descarta tentativas mais antigas que a janela. Janela deslizante.
    Assume que o caller já adquiriu o _lock."""
    cutoff = now - window
    while state.failures and state.failures[0] < cutoff:
        state.failures.popleft()


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------


def is_blocked(username: str) -> tuple[bool, int]:
    """
    Retorna (bloqueado, segundos_restantes).

    Se o bloqueio expirou, limpa o flag e retorna (False, 0).
    Nunca cria entrada nova; usuários nunca antes vistos retornam
    (False, 0) sem efeito colateral.
    """
    now = _now()
    with _lock:
        state = _state.get(username)
        if state is None:
            return False, 0
        if state.blocked_until <= now:
            # Bloqueio expirou (ou nunca houve). Limpa o flag.
            state.blocked_until = 0.0
            return False, 0
        remaining = int(state.blocked_until - now) + 1  # arredonda para cima
        return True, remaining


def register_failure(username: str) -> tuple[bool, int]:
    """
    Registra uma tentativa falha de login para o usuário.

    Aplica a janela deslizante. Se o número de falhas dentro da janela
    atingir o limite, ativa o bloqueio.

    Retorna (bloqueado_agora, segundos_de_bloqueio). 'bloqueado_agora'
    é True se ESTA chamada acabou de ativar o bloqueio (ou se o usuário
    já estava bloqueado).

    Importante: o caller (api/auth.py) só deve chamar esta função para
    usernames que EXISTEM no banco. Tentativas com username inexistente
    não devem ser registradas aqui (§8 Decisão B).
    """
    max_attempts, window, block = _params()
    now = _now()

    with _lock:
        state = _get_or_create(username)

        # Já bloqueado? Não acumula mais falhas — só informa o estado.
        if state.blocked_until > now:
            remaining = int(state.blocked_until - now) + 1
            return True, remaining

        # Limpa falhas fora da janela antes de contar a nova.
        _prune_old_failures(state, window, now)
        state.failures.append(now)

        if len(state.failures) >= max_attempts:
            state.blocked_until = now + block
            # Limpa o histórico de falhas — só o bloqueio importa agora.
            state.failures.clear()
            return True, block

        return False, 0


def register_success(username: str) -> None:
    """
    Limpa o histórico do usuário após login bem-sucedido.

    Em particular: zera o contador de falhas E o flag de bloqueio.
    Login válido prova que é o operador legítimo; sem motivo para
    manter o estado punitivo.
    """
    with _lock:
        if username in _state:
            del _state[username]


def reset(username: Optional[str] = None) -> None:
    """
    Limpa o estado.

    - reset() — limpa todos os usuários (útil em testes ou troca manual
      de parâmetros via UI no Bloco 11).
    - reset("alice") — limpa apenas o usuário 'alice'.
    """
    with _lock:
        if username is None:
            _state.clear()
        else:
            _state.pop(username, None)


def _debug_snapshot() -> dict:
    """Inspeção interna do estado. NÃO usar em código de produção;
    apenas em testes e debug manual."""
    with _lock:
        return {
            u: {
                "failures": list(s.failures),
                "blocked_until": s.blocked_until,
            }
            for u, s in _state.items()
        }