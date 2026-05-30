"""Teste integrado do case_service contra o audit_service real (ADR-003a).
Reproduz fielmente o session.py do projeto: engine SQLite, check_same_thread=False,
FK on, SEM isolation_level customizado, SessionLocal com expire_on_commit=False."""
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
import app.models.case      # noqa: F401  (registra tabela cases)
import app.models.audit_log # noqa: F401  (registra tabela audit_logs)
from app.schemas.cases import CaseCreate, CaseUpdate
from app.services import case_service, audit_service


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _fk(c, r):
        cur = c.cursor(); cur.execute("PRAGMA foreign_keys=ON"); cur.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    s = SessionLocal()

    # Cria o operador (id=1) usado como created_by/updated_by nos casos.
    # Usa o modelo User real (não SQL bruto), para que os defaults definidos
    # na camada Python (ex.: role='operator') sejam aplicados — evita
    # IntegrityError em colunas NOT NULL com default só no modelo.
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


def test_create_gera_codigo_sequencial(db):
    c1 = case_service.create_case(db, CaseCreate(name="Operação Alpha"), user_id=1)
    assert c1.case_code.endswith("-0001")
    assert c1.status == "active"
    c2 = case_service.create_case(db, CaseCreate(name="Operação Beta"), user_id=1)
    assert c2.case_code.endswith("-0002")
    # mesmo ano nos dois
    assert c1.case_code[:4] == c2.case_code[:4]


def test_create_gera_audit_e_cadeia_integra(db):
    case_service.create_case(db, CaseCreate(name="Caso Auditado"), user_id=1)
    logs = db.execute(text("SELECT action, entity_type, entity_id FROM audit_logs")).fetchall()
    assert ("case_create", "case", 1) in [(r[0], r[1], r[2]) for r in logs]
    result = audit_service.verify_chain(db)
    assert result["ok"] is True, result.get("error")


def test_nome_vazio_rejeitado(db):
    with pytest.raises(Exception):
        CaseCreate(name="   ")


def test_update_persiste_e_audita(db):
    c = case_service.create_case(db, CaseCreate(name="Antes"), user_id=1)
    upd = case_service.update_case(db, c.id, CaseUpdate(name="Depois", unit="DIP"), user_id=1)
    assert upd.name == "Depois"
    assert upd.unit == "DIP"
    actions = [r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()]
    assert "case_update" in actions
    assert audit_service.verify_chain(db)["ok"] is True


def test_update_sem_mudanca_real_nao_loga(db):
    c = case_service.create_case(db, CaseCreate(name="Igual"), user_id=1)
    n_antes = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
    case_service.update_case(db, c.id, CaseUpdate(name="Igual"), user_id=1)
    n_depois = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
    assert n_antes == n_depois  # nenhum log novo


def test_archive_remove_da_lista_padrao(db):
    c = case_service.create_case(db, CaseCreate(name="Para Arquivar"), user_id=1)
    case_service.archive_case(db, c.id, user_id=1)
    padrao = case_service.list_cases(db)
    assert all(x.id != c.id for x in padrao)
    com_arquivados = case_service.list_cases(db, include_archived=True)
    assert any(x.id == c.id for x in com_arquivados)
    actions = [r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()]
    assert "case_archive" in actions


def test_atomicidade_rollback_em_falha(db, monkeypatch):
    # força falha dentro do log_action -> caso NÃO deve persistir
    def boom(*a, **k):
        raise RuntimeError("falha simulada no log")
    monkeypatch.setattr(case_service.audit_service, "log_action", boom)
    n_cases_antes = db.execute(text("SELECT COUNT(*) FROM cases")).scalar()
    with pytest.raises(RuntimeError):
        case_service.create_case(db, CaseCreate(name="Fantasma"), user_id=1)
    n_cases_depois = db.execute(text("SELECT COUNT(*) FROM cases")).scalar()
    assert n_cases_antes == n_cases_depois  # rollback reverteu o caso


def test_list_ordenacao(db):
    case_service.create_case(db, CaseCreate(name="Zebra"), user_id=1)
    case_service.create_case(db, CaseCreate(name="Alfa"), user_id=1)
    por_nome = case_service.list_cases(db, sort_by="name", descending=False)
    nomes = [c.name for c in por_nome]
    assert nomes == sorted(nomes)
