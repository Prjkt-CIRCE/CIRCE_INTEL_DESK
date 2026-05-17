"""
CIRCE Intel Desk — Testes da cadeia de auditoria imutável.

Cobre os 5 cenários previstos em ADR-003 §5:
  1. Registro gênese.
  2. Encadeamento de N registros.
  3. Detecção de adulteração em record_hash.
  4. Detecção de adulteração em campo canônico.
  5. Detecção de remoção de registro do meio.

Cada teste usa banco SQLite em memória — sem efeito colateral, sem arquivo em disco.

Sprint 01 — Bloco 7.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.audit_log import AuditLog
from app.services.audit_service import log_action, verify_chain


# ---------------------------------------------------------------------------
# Fixture: banco em memória com schema completo
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """
    Cria um banco SQLite em memória, aplica o schema e entrega uma Session.
    Ao final do teste, descarta tudo.

    'check_same_thread=False' é necessário para SQLite em memória com SQLAlchemy.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_log(db: Session, action: str = "login", **kwargs) -> AuditLog:
    """Insere um registro de audit log e faz commit. Retorna o objeto inserido."""
    entry = log_action(db, action=action, **kwargs)
    db.commit()
    return entry


def _tamper_record_hash(db: Session, record_id: int) -> None:
    """Adultera o record_hash de um registro diretamente no banco (simula ataque)."""
    db.execute(
        text("UPDATE audit_logs SET record_hash = 'hash_adulterado_000000000000000000000000000000000000000000000000000000' WHERE id = :id"),
        {"id": record_id},
    )
    db.commit()


def _tamper_action(db: Session, record_id: int, new_action: str) -> None:
    """Adultera o campo 'action' de um registro diretamente no banco (simula ataque)."""
    db.execute(
        text("UPDATE audit_logs SET action = :action WHERE id = :id"),
        {"action": new_action, "id": record_id},
    )
    db.commit()


# ---------------------------------------------------------------------------
# Teste 1 — Registro gênese
# ---------------------------------------------------------------------------

def test_genesis_record(db: Session):
    """
    O primeiro registro da tabela deve ter previous_hash = None
    e um record_hash válido (64 caracteres hex lowercase).
    verify_chain deve retornar ok=True com total=1.
    """
    entry = _insert_log(db, action="setup", description="Primeiro operador cadastrado.")

    assert entry.id is not None, "Registro deve ter id atribuído pelo banco"
    assert entry.previous_hash is None, "Registro gênese deve ter previous_hash = None"
    assert entry.record_hash is not None, "record_hash não pode ser None"
    assert len(entry.record_hash) == 64, "SHA-256 hex deve ter exatamente 64 caracteres"
    assert entry.record_hash == entry.record_hash.lower(), "Hash deve ser lowercase"
    assert all(c in "0123456789abcdef" for c in entry.record_hash), (
        "Hash deve conter apenas caracteres hexadecimais"
    )

    result = verify_chain(db)
    assert result["ok"] is True
    assert result["total"] == 1
    assert result["broken_at_id"] is None


# ---------------------------------------------------------------------------
# Teste 2 — Encadeamento de N registros
# ---------------------------------------------------------------------------

def test_chain_encadeamento(db: Session):
    """
    Após N inserções, cada registro deve ter previous_hash igual
    ao record_hash do registro anterior.
    verify_chain deve retornar ok=True com total=N.
    """
    n = 5
    entries = []
    for i in range(n):
        entry = _insert_log(
            db,
            action="login",
            user_id=1,
            description=f"Login {i + 1}",
        )
        entries.append(entry)

    # Verifica encadeamento manual
    assert entries[0].previous_hash is None, "Primeiro deve ter previous_hash=None"
    for i in range(1, n):
        assert entries[i].previous_hash == entries[i - 1].record_hash, (
            f"Registro {i + 1}: previous_hash deve apontar para record_hash do anterior"
        )

    # Verifica via função oficial
    result = verify_chain(db)
    assert result["ok"] is True
    assert result["total"] == n
    assert result["broken_at_id"] is None


# ---------------------------------------------------------------------------
# Teste 3 — Detecção de adulteração em record_hash
# ---------------------------------------------------------------------------

def test_deteccao_adulteracao_record_hash(db: Session):
    """
    Se o record_hash de um registro for alterado diretamente no banco,
    verify_chain deve detectar e retornar ok=False com broken_at_id correto.
    """
    e1 = _insert_log(db, action="login", user_id=1)
    e2 = _insert_log(db, action="logout", user_id=1)
    e3 = _insert_log(db, action="login", user_id=1)

    # Adultera o record_hash do segundo registro
    _tamper_record_hash(db, e2.id)

    result = verify_chain(db)
    assert result["ok"] is False
    # O problema é detectado no próprio registro adulterado (hash não bate)
    # OU no seguinte (previous_hash quebrado) — ambos são corretos.
    # O importante é que broken_at_id não seja None e seja >= e2.id.
    assert result["broken_at_id"] is not None
    assert result["broken_at_id"] >= e2.id, (
        "A corrupção deve ser detectada a partir do registro adulterado"
    )


# ---------------------------------------------------------------------------
# Teste 4 — Detecção de adulteração em campo canônico
# ---------------------------------------------------------------------------

def test_deteccao_adulteracao_campo_canonico(db: Session):
    """
    Se um campo canônico (ex.: action) for alterado diretamente no banco
    — sem recalcular o hash — verify_chain deve detectar a divergência.
    """
    e1 = _insert_log(db, action="login", user_id=1)
    e2 = _insert_log(db, action="logout", user_id=1)

    # Adultera o campo 'action' do segundo registro sem atualizar o hash
    _tamper_action(db, e2.id, new_action="login_failed")

    result = verify_chain(db)
    assert result["ok"] is False
    assert result["broken_at_id"] == e2.id, (
        "A corrupção deve ser detectada exatamente no registro adulterado"
    )


# ---------------------------------------------------------------------------
# Teste 5 — Detecção de remoção de registro do meio
# ---------------------------------------------------------------------------

def test_deteccao_remocao_registro_do_meio(db: Session):
    """
    Se um registro for removido do meio da cadeia,
    o previous_hash do registro seguinte não vai bater mais,
    e verify_chain deve detectar.
    """
    e1 = _insert_log(db, action="login", user_id=1)
    e2 = _insert_log(db, action="case_create", user_id=1, entity_type="case", entity_id=1)
    e3 = _insert_log(db, action="logout", user_id=1)

    # Remove o registro do meio diretamente no banco
    db.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": e2.id})
    db.commit()

    result = verify_chain(db)
    assert result["ok"] is False
    # e3.previous_hash aponta para e2.record_hash, que não existe mais.
    # A verificação vai detectar que o previous_hash de e3 não bate
    # com o record_hash do registro anterior (que agora é e1).
    assert result["broken_at_id"] == e3.id, (
        "A corrupção deve ser detectada no registro cujo previous_hash ficou órfão"
    )