"""
Testes do person_org_link_service (RF-005).
Sprint 01-B — Sub-passo B6.

Nota: os fixtures pessoa e org fazem commit explícito antes de ceder
controle ao teste, para que a sessão não tenha transação aberta quando
create_link executar BEGIN IMMEDIATE (mesmo padrão do test_link_service.py).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.models.base import Base
from app.models.organization import Organization
from app.models.person import Person
from app.models.person_org_link import PersonOrgLink
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.setting import Setting
from app.models.case import Case
from app.models.case_person_link import CasePersonLink
from app.services.person_org_link_service import (
    create_link, remove_link, get_link,
    list_links_by_org, list_links_by_person,
    DuplicatePersonOrgLinkError,
)
from app.services.audit_service import verify_chain


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


@pytest.fixture
def pessoa(db):
    p = Person(full_name="João Silva", status="active",
               reliability_level="pending", created_at=_now())
    db.add(p)
    db.commit()   # commit limpo — sessão sem transação aberta após isso
    db.refresh(p)
    return p


@pytest.fixture
def org(db):
    o = Organization(name="PCC", status="active",
                     reliability_level="pending", created_at=_now())
    db.add(o)
    db.commit()   # commit limpo
    db.refresh(o)
    return o


def test_create_link_basico(db, pessoa, org):
    link = create_link(db, pessoa.id, org.id, "membro", "Inteligência", user_id=1)
    assert link.id is not None
    assert link.active == 1
    assert link.link_type == "membro"


def test_create_link_gera_audit(db, pessoa, org):
    create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    log = db.query(AuditLog).filter_by(action="person_org_link_create").first()
    assert log is not None


def test_create_link_duplicado_rejeitado(db, pessoa, org):
    create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    with pytest.raises(DuplicatePersonOrgLinkError):
        create_link(db, pessoa.id, org.id, "membro", "fonte2", user_id=1)


def test_create_link_tipos_diferentes_permitido(db, pessoa, org):
    create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    link2 = create_link(db, pessoa.id, org.id, "rival", "fonte", user_id=1)
    assert link2.id is not None


def test_remove_link_exclusao_logica(db, pessoa, org):
    link = create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    removed = remove_link(db, link.id, user_id=1)
    assert removed.active == 0
    log = db.query(AuditLog).filter_by(action="person_org_link_remove").first()
    assert log is not None


def test_remove_link_idempotente(db, pessoa, org):
    link = create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    remove_link(db, link.id, user_id=1)
    count = db.query(AuditLog).filter_by(action="person_org_link_remove").count()
    remove_link(db, link.id, user_id=1)
    assert db.query(AuditLog).filter_by(action="person_org_link_remove").count() == count


def test_reativacao_apos_remocao(db, pessoa, org):
    link = create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    remove_link(db, link.id, user_id=1)
    reativado = create_link(db, pessoa.id, org.id, "membro", "nova fonte", user_id=1)
    assert reativado.id == link.id
    assert reativado.active == 1
    assert reativado.source == "nova fonte"


def test_list_by_org(db, pessoa, org):
    create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    links = list_links_by_org(db, org.id)
    assert len(links) == 1


def test_list_by_person(db, pessoa, org):
    create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    links = list_links_by_person(db, pessoa.id)
    assert len(links) == 1


def test_list_exclui_removidos_por_padrao(db, pessoa, org):
    link = create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    remove_link(db, link.id, user_id=1)
    assert len(list_links_by_org(db, org.id)) == 0
    assert len(list_links_by_person(db, pessoa.id)) == 0


def test_cadeia_integra_apos_operacoes(db, pessoa, org):
    link = create_link(db, pessoa.id, org.id, "membro", "fonte", user_id=1)
    remove_link(db, link.id, user_id=1)
    create_link(db, pessoa.id, org.id, "membro", "nova fonte", user_id=1)
    result = verify_chain(db)
    assert result["ok"] is True