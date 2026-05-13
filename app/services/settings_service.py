"""
CIRCE Intel Desk — Serviço de configurações operacionais (D11).

Gerencia a tabela `settings`, que armazena parâmetros operacionais
configuráveis pelo operador via UI (Bloco 11). Todos os parâmetros
têm defaults sensatos aplicados no primeiro startup; alterações são
persistidas e refletem no comportamento do sistema.

Exceção a D11: o loopback (`host=127.0.0.1`) NÃO entra aqui. É
hardcoded em run.py por imposição de segurança (D3).

Cache: leitura é O(1) via dict em memória. Cache é invalidado
em escritas (set_value) e populado no startup pelo seed.

Sprint 01 — Bloco 4.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.setting import Setting


# ---------------------------------------------------------------------------
# Defaults — D11
# ---------------------------------------------------------------------------

# Cada entrada: (key, default_value_as_str, value_type, description)
# value_type orienta a conversão na leitura: 'int', 'str', 'bool', 'float'.
_DEFAULTS: list[tuple[str, str, str, str]] = [
    (
        "inactivity_lock_minutes",
        "15",
        "int",
        "Minutos de inatividade ate bloqueio automatico da sessao.",
    ),
    (
        "session_hours",
        "8",
        "int",
        "Horas maximas de duracao de uma sessao antes de exigir novo login.",
    ),
    (
        "bruteforce_max_attempts",
        "5",
        "int",
        "Tentativas de login com falha antes de bloqueio temporario do usuario.",
    ),
    (
        "bruteforce_window_seconds",
        "300",
        "int",
        "Janela em segundos para contagem de tentativas falhas.",
    ),
    (
        "bruteforce_block_seconds",
        "900",
        "int",
        "Duracao em segundos do bloqueio apos exceder tentativas.",
    ),
]


# ---------------------------------------------------------------------------
# Cache em memória
# ---------------------------------------------------------------------------

_cache: dict[str, Any] = {}
_cache_loaded: bool = False


def _now_iso() -> str:
    """Timestamp UTC ISO 8601 com microsegundos, alinhado ao ADR-003."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _cast(value: str, value_type: str) -> Any:
    """Converte string do banco para tipo Python."""
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "bool":
        return value.strip().lower() in ("1", "true", "yes", "on")
    # str e qualquer outro tipo desconhecido caem aqui
    return value


def _serialize(value: Any) -> str:
    """Converte valor Python para string para persistir."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------------------
# Seed — idempotente
# ---------------------------------------------------------------------------


def seed_defaults() -> int:
    """
    Garante que todos os defaults existem na tabela `settings`.

    Idempotente: keys ja presentes nao sao tocadas. Retorna o numero
    de novas chaves criadas nesta chamada.

    Chamado no startup do FastAPI (ver app/main.py lifespan).
    """
    created = 0
    session: Session = SessionLocal()
    try:
        existing_keys = {row.key for row in session.query(Setting.key).all()}
        timestamp = _now_iso()

        for key, default_value, value_type, description in _DEFAULTS:
            if key in existing_keys:
                continue
            row = Setting(
                key=key,
                value=default_value,
                value_type=value_type,
                description=description,
                editable_by_operator=1,
                updated_at=timestamp,
                updated_by=None,  # criado pelo sistema, nao por operador
            )
            session.add(row)
            created += 1

        if created > 0:
            session.commit()

        # Popula cache com TODOS os valores (incluindo os ja existentes).
        _refresh_cache(session)
        return created
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _refresh_cache(session: Optional[Session] = None) -> None:
    """Recarrega o cache a partir do banco."""
    global _cache, _cache_loaded
    owns_session = session is None
    if owns_session:
        session = SessionLocal()
    try:
        rows = session.query(Setting).all()
        _cache = {row.key: _cast(row.value, row.value_type) for row in rows}
        _cache_loaded = True
    finally:
        if owns_session:
            session.close()


def _ensure_cache() -> None:
    """Carrega o cache sob demanda na primeira leitura."""
    if not _cache_loaded:
        _refresh_cache()


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------


def get_value(key: str, default: Any = None) -> Any:
    """Retorna o valor de um parametro, ja convertido para o tipo correto."""
    _ensure_cache()
    return _cache.get(key, default)


def get_all() -> dict[str, Any]:
    """Retorna copia do estado atual do cache (todos os parametros)."""
    _ensure_cache()
    return dict(_cache)


def set_value(key: str, value: Any, updated_by: Optional[int] = None) -> None:
    """
    Atualiza um parametro existente.

    Levanta KeyError se a chave nao existe (defaults sao seedados no
    startup, entao operadores nao devem criar chaves novas pela UI).

    Levanta PermissionError se editable_by_operator=0 (reservado para
    futuras configuracoes internas que nao devam ser tocadas pela UI).
    """
    session: Session = SessionLocal()
    try:
        row = session.query(Setting).filter(Setting.key == key).first()
        if row is None:
            raise KeyError(f"Setting '{key}' nao existe.")
        if row.editable_by_operator != 1:
            raise PermissionError(
                f"Setting '{key}' nao e editavel pelo operador."
            )
        row.value = _serialize(value)
        row.updated_at = _now_iso()
        row.updated_by = updated_by
        session.commit()
        # Atualiza cache na mesma transacao logica
        _cache[key] = _cast(row.value, row.value_type)
    finally:
        session.close()


def invalidate_cache() -> None:
    """Forca recarga do cache na proxima leitura. Util em testes."""
    global _cache_loaded
    _cache_loaded = False
