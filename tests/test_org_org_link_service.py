"""
Testes do org_org_link_service (RF-006).
Sprint 01-B — Sub-passo B7.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.models.base import Base
from app.models.organization import Organization
from app.models.org_org_link import OrgOrgLink
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.setting import Setting
from app.models.case import Case
from app.models.case_person_link import CasePersonLink
from app.models.person import Person
from app.models.person_org_link import PersonOrgLink
from app.services.org_org_link_service import (
    create_link, remove_link, get_link,
    list_links_by_org, SameOrgError,
)
from app.services.audit_service import verify_chain


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


@pytest.fixture
def org_a(db):
    o = Organization(name="PCC", status="active", reliability_level="pending", created_at=_now())
    db.add(o); db.commit(); db.refresh(o)
    return o


@pytest.fixture
def org_b(db):
    o = Organization(name="CV", status="active", reliability_level="pending", created_at=_now())
    db.add(o); db.commit(); db.refresh(o)
    return o


def test_create_link_basico(db, org_a, org_b):
    link = create_link(db, org_a.id, org_b.id, "rivalidade", "Inteligência", user_id=1)
    assert link.id is not None
    assert link.active == 1
    assert link.relation_type == "rivalidade"


def test_create_link_gera_audit(db, org_a, org_b):
    create_link(db, org_a.id, org_b.id, "alianca", "fonte", user_id=1)
    log = db.query(AuditLog).filter_by(action="org_org_link_create").first()
    assert log is not None


def test_create_mesma_org_rejeitado(db, org_a):
    with pytest.raises(SameOrgError):
        create_link(db, org_a.id, org_a.id, "rivalidade", "fonte", user_id=1)


def test_multiplas_relacoes_permitidas(db, org_a, org_b):
    link1 = create_link(db, org_a.id, org_b.id, "rivalidade", "fonte", user_id=1)
    link2 = create_link(db, org_a.id, org_b.id, "alianca", "fonte", user_id=1)
    assert link1.id != link2.id


def test_list_by_org_inclui_ambos_lados(db, org_a, org_b):
    create_link(db, org_a.id, org_b.id, "rivalidade", "fonte", user_id=1)
    assert len(list_links_by_org(db, org_a.id)) == 1
    assert len(list_links_by_org(db, org_b.id)) == 1


def test_remove_link_exclusao_logica(db, org_a, org_b):
    link = create_link(db, org_a.id, org_b.id, "rivalidade", "fonte", user_id=1)
    removed = remove_link(db, link.id, user_id=1)
    assert removed.active == 0
    log = db.query(AuditLog).filter_by(action="org_org_link_remove").first()
    assert log is not None


def test_remove_exclui_da_lista_padrao(db, org_a, org_b):
    link = create_link(db, org_a.id, org_b.id, "rivalidade", "fonte", user_id=1)
    remove_link(db, link.id, user_id=1)
    assert len(list_links_by_org(db, org_a.id)) == 0


def test_remove_idempotente(db, org_a, org_b):
    link = create_link(db, org_a.id, org_b.id, "rivalidade", "fonte", user_id=1)
    remove_link(db, link.id, user_id=1)
    count = db.query(AuditLog).filter_by(action="org_org_link_remove").count()
    remove_link(db, link.id, user_id=1)
    assert db.query(AuditLog).filter_by(action="org_org_link_remove").count() == count


def test_cadeia_integra_apos_operacoes(db, org_a, org_b):
    link = create_link(db, org_a.id, org_b.id, "dissidencia", "fonte", user_id=1)
    remove_link(db, link.id, user_id=1)
    result = verify_chain(db)
    assert result["ok"] is True