"""
Fixture compartilhada de banco de dados para os testes do CIRCE Intel Desk.

Registra todos os modelos SQLAlchemy e cria as tabelas virtuais FTS5
(fts_cases, fts_persons, fts_organizations, fts_documents) que existem
no banco de producao via Alembic mas nao sao criadas por Base.metadata.create_all.

Sprint 03 - Sub-passo 03-0: adicionado suporte a FTS5 para que os testes
dos servicos de dominio (que agora chamam search_service.index_*) passem.
"""
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User

# Registrar todos os modelos para que create_all crie suas tabelas
import app.models.case               # noqa: F401
import app.models.person             # noqa: F401
import app.models.organization       # noqa: F401
import app.models.audit_log          # noqa: F401
import app.models.case_person_link   # noqa: F401
import app.models.person_org_link    # noqa: F401
import app.models.org_org_link       # noqa: F401
import app.models.document           # noqa: F401
import app.models.setting            # noqa: F401


_FTS5_DDL = [
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS fts_cases USING fts5(
        case_id UNINDEXED,
        name,
        case_code,
        description,
        unit,
        responsible,
        tokenize='unicode61'
    )
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS fts_persons USING fts5(
        person_id UNINDEXED,
        full_name,
        aliases,
        notes,
        tokenize='unicode61'
    )
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS fts_organizations USING fts5(
        org_id UNINDEXED,
        name,
        aliases,
        description,
        tokenize='unicode61'
    )
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(
        document_id UNINDEXED,
        original_filename,
        title,
        tokenize='unicode61'
    )
    """,
]


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk(c, r):
        cur = c.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)

    # Criar tabelas virtuais FTS5 (nao gerenciadas pelo SQLAlchemy)
    with engine.connect() as conn:
        for ddl in _FTS5_DDL:
            conn.execute(text(ddl))
        conn.commit()

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    s = SessionLocal()

    # Operador padrao usado como created_by/updated_by nos testes
    operador = User(
        id=1,
        username="op",
        display_name="Operador",
        password_hash="x",
        created_at="2026-05-30T00:00:00.000000Z",
    )
    s.add(operador)
    s.commit()

    yield s
    s.close()
