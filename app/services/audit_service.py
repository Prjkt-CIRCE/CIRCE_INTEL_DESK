"""
CIRCE Intel Desk — Serviço de Auditoria.

Responsabilidades:
  - Calcular record_hash de cada registro (SHA-256 encadeado, ADR-003 §2.1).
  - Inserir registros em audit_logs de forma transacional (ADR-003 §2.3).
  - Verificar integridade da cadeia (ADR-003 §2.7).

Regras inegociáveis (ADR-003):
  - Separador canônico: \x1f (Unit Separator, byte 0x1F).
  - Marcador de campo nulo: \x00 (NULL byte).
  - Timestamp: YYYY-MM-DDTHH:MM:SS.ffffffZ (UTC, ISO 8601).
  - Hash: SHA-256, hexadecimal lowercase, 64 caracteres, sem prefixo.
  - JSON canônico: sort_keys=True, separators=(",", ":"), ensure_ascii=False.
  - Inserção dentro de transação única com BEGIN IMMEDIATE (SQLite).
  - Erro de log bloqueia a ação principal (04_SEGURANCA.md §7.1).

Sprint 01 — Bloco 7.
Sprint 01 — Bloco 8 (ADR-003a): parâmetro manage_transaction em log_action,
para permitir auditoria atômica de operações que criam/alteram entidades.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes canônicas (ADR-003 §2.1)
# ---------------------------------------------------------------------------

_SEP = "\x1f"   # Unit Separator — separa campos na string canônica
_NULL = "\x00"  # Marcador de campo nulo (distinto de string vazia "")

# Ordem exata dos campos canônicos conforme ADR-003 §2.1
_CANONICAL_FIELDS = (
    "previous_hash",
    "timestamp",
    "user_id",
    "action",
    "entity_type",
    "entity_id",
    "description",
    "metadata",
    "status",
)


# ---------------------------------------------------------------------------
# Funções internas de hash
# ---------------------------------------------------------------------------

def _serialize_field(field_name: str, value: Any) -> str:
    """
    Serializa um campo para sua representação canônica (string).

    Regras (ADR-003 §2.1):
      - None       → marcador _NULL ("\x00")
      - user_id, entity_id → inteiro decimal sem padding ("42", não "00042")
      - timestamp  → ISO 8601 UTC com microsegundos e sufixo Z
                     (esperamos que já chegue nesse formato; validamos aqui)
      - metadata   → JSON canônico (sort_keys, sem espaços, ensure_ascii=False)
                     se não for None; None → _NULL
      - demais     → str(value)
    """
    if value is None:
        return _NULL

    if field_name in ("user_id", "entity_id"):
        return str(int(value))  # inteiro decimal, sem padding

    if field_name == "metadata":
        # metadata chega como string JSON (como está no banco) ou como dict
        if isinstance(value, str):
            # Re-serializar para garantir canonicidade
            try:
                parsed = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                # Se não for JSON válido, usa a string como veio
                # Isso nunca deveria acontecer em operação normal
                logger.error("audit_service: metadata não é JSON válido: %r", value)
                return value
            return json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if isinstance(value, dict):
            return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return str(value)

    if field_name == "timestamp":
        # Aceita string já formatada ou objeto datetime
        if isinstance(value, datetime):
            # Garante UTC e formata com microsegundos
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        # Já é string — confia no formato (quem inseriu é responsável)
        return str(value)

    return str(value)


def _canonical_string(record_dict: dict[str, Any]) -> bytes:
    """
    Monta a string canônica de um registro e retorna em bytes UTF-8.

    A string é a concatenação dos campos em _CANONICAL_FIELDS,
    separados por _SEP (\x1f), na ordem exata definida em ADR-003 §2.1.

    Args:
        record_dict: dicionário com os campos do registro. A chave
                     "metadata" deve usar o nome canônico do ADR-003
                     (não "metadata_json"). Quem chama é responsável
                     por mapear o atributo Python para o nome canônico.

    Returns:
        bytes: string canônica codificada em UTF-8.
    """
    parts = [
        _serialize_field(field, record_dict.get(field))
        for field in _CANONICAL_FIELDS
    ]
    canonical = _SEP.join(parts)
    return canonical.encode("utf-8")


def _compute_hash(canonical_bytes: bytes) -> str:
    """
    Calcula SHA-256 sobre os bytes canônicos.

    Returns:
        str: hexadecimal lowercase, 64 caracteres, sem prefixo.
             Exemplo: "a3f1b2c4d5e6..."
    """
    return hashlib.sha256(canonical_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Função pública principal
# ---------------------------------------------------------------------------

def log_action(
    db: Session,
    *,
    action: str,
    user_id: Optional[int] = None,
    user_display_name: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    description: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    status: str = "success",
    manage_transaction: bool = True,
) -> AuditLog:
    """
    Insere um registro imutável em audit_logs.

    Esta função deve ser chamada dentro da MESMA transação da ação de domínio
    (ADR-003 §2.4). Se o log falhar, a transação inteira faz rollback e a
    ação de domínio também é desfeita. Não há ação não-logada.

    Controle de transação (ADR-003a):
        manage_transaction=True  (padrão): a função abre a transação com
            BEGIN IMMEDIATE antes de ler o último hash, garantindo o lock de
            escrita do SQLite (ADR-003 §2.3). Use para eventos autônomos que
            commitam logo em seguida (login, logout, lock).
        manage_transaction=False: a função NÃO abre a transação. O chamador é
            responsável por ter aberto BEGIN IMMEDIATE e por commitar/rollback.
            Use em serviços de domínio que inserem uma entidade e auditam na
            mesma transação — pois o INSERT da entidade precede o log (para
            materializar entity_id) e já abre a transação, impedindo um segundo
            BEGIN aqui (cannot start a transaction within a transaction).

    A função usa BEGIN IMMEDIATE para garantir exclusividade de escrita
    durante a leitura do último hash e a inserção do novo registro,
    evitando condição de corrida (ADR-003 §2.3).

    Args:
        db:               sessão SQLAlchemy ativa.
        action:           string do enum (ex.: "login", "login_failed").
        user_id:          ID do operador; None em eventos pré-autenticação.
        user_display_name: snapshot do nome do operador (não entra no hash).
        entity_type:      tipo de entidade afetada (ex.: "case", "person").
        entity_id:        ID da entidade afetada.
        description:      texto livre descritivo.
        metadata:         dict com dados extras; serializado como JSON canônico.
        status:           "success" | "failure" | "alert" (padrão: "success").
        manage_transaction: ver bloco "Controle de transação" acima.

    Returns:
        AuditLog: o objeto inserido (com id preenchido pelo banco).

    Raises:
        Exception: qualquer falha de banco ou de cálculo de hash.
                   O chamador deve deixar propagar para garantir rollback.
    """
    # 1. Captura o hash do último registro (ou None se tabela vazia)
    #    BEGIN IMMEDIATE garante lock de escrita desde já (ADR-003 §2.3).
    #    Quando manage_transaction=False, o chamador já abriu a transação
    #    (ADR-003a) — não reabrimos, sob pena de erro de transação aninhada.
    if manage_transaction:
        db.execute(text("BEGIN IMMEDIATE"))

    row = db.execute(
        text("SELECT record_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
    ).fetchone()
    previous_hash: Optional[str] = row[0] if row else None

    # 2. Monta timestamp em UTC com microsegundos
    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"

    # 3. Serializa metadata para JSON canônico (ou None)
    metadata_str: Optional[str] = None
    if metadata is not None:
        metadata_str = json.dumps(
            metadata,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    # 4. Monta dicionário canônico para cálculo do hash
    #    Usa "metadata" (nome canônico do ADR-003), não "metadata_json"
    record_dict = {
        "previous_hash": previous_hash,
        "timestamp": timestamp_str,
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "description": description,
        "metadata": metadata_str,
        "status": status,
    }

    # 5. Calcula hash
    canonical = _canonical_string(record_dict)
    record_hash = _compute_hash(canonical)

    # 6. Cria o objeto ORM e insere
    log_entry = AuditLog(
        timestamp=timestamp_str,
        user_id=user_id,
        user_display_name=user_display_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        metadata_json=metadata_str,   # atributo Python usa "metadata_json"
        status=status,
        previous_hash=previous_hash,
        record_hash=record_hash,
    )
    db.add(log_entry)
    db.flush()  # envia o INSERT sem fazer COMMIT — quem controla o commit é o chamador

    logger.info(
        "audit: action=%r user_id=%s entity=%s/%s status=%s hash=%.16s…",
        action, user_id, entity_type, entity_id, status, record_hash,
    )

    return log_entry


# ---------------------------------------------------------------------------
# Verificação da cadeia
# ---------------------------------------------------------------------------

def verify_chain(db: Session) -> dict[str, Any]:
    """
    Percorre audit_logs em ordem crescente de id e verifica:
      1. O record_hash armazenado bate com o hash recalculado.
      2. O previous_hash armazenado bate com o record_hash do registro anterior.

    Não tem efeito colateral — apenas leitura.

    Returns:
        dict com:
          - ok (bool): True se a cadeia está íntegra.
          - broken_at_id (int | None): id do primeiro registro com problema.
          - total (int): total de registros verificados.
          - error (str | None): descrição do problema encontrado.
    """
    records = db.execute(
        text(
            "SELECT id, timestamp, user_id, action, entity_type, entity_id, "
            "description, metadata, status, previous_hash, record_hash "
            "FROM audit_logs ORDER BY id ASC"
        )
    ).fetchall()

    if not records:
        return {"ok": True, "broken_at_id": None, "total": 0, "error": None}

    previous_hash_expected: Optional[str] = None

    for i, row in enumerate(records):
        (
            row_id, timestamp, user_id, action, entity_type, entity_id,
            description, metadata_raw, status, stored_previous_hash, stored_record_hash,
        ) = row

        # Verifica encadeamento: previous_hash deste registro deve ser
        # o record_hash do anterior (ou None para o primeiro)
        if stored_previous_hash != previous_hash_expected:
            return {
                "ok": False,
                "broken_at_id": row_id,
                "total": i,
                "error": (
                    f"Encadeamento quebrado no id={row_id}: "
                    f"previous_hash armazenado={stored_previous_hash!r} "
                    f"esperado={previous_hash_expected!r}"
                ),
            }

        # Reconstrói o dicionário canônico com os valores do banco
        record_dict = {
            "previous_hash": stored_previous_hash,
            "timestamp": timestamp,
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "description": description,
            "metadata": metadata_raw,  # já é string JSON (ou None) — como está no banco
            "status": status,
        }

        recalculated_hash = _compute_hash(_canonical_string(record_dict))

        if recalculated_hash != stored_record_hash:
            return {
                "ok": False,
                "broken_at_id": row_id,
                "total": i,
                "error": (
                    f"Hash corrompido no id={row_id}: "
                    f"recalculado={recalculated_hash!r} "
                    f"armazenado={stored_record_hash!r}"
                ),
            }

        previous_hash_expected = stored_record_hash

    return {
        "ok": True,
        "broken_at_id": None,
        "total": len(records),
        "error": None,
    }
