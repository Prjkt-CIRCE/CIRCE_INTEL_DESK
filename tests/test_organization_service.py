"""
Testes do organization_service (RF-004).

Sprint 01-B - Sub-passo B2.

Fixture 'db' definida em conftest.py (Sprint 03-0: inclui tabelas FTS5).
"""
import pytest
from sqlalchemy import text

from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.services.organization_service import (
    create_organization,
    update_organization,
    archive_organization,
    get_organization,
    list_organizations,
    OrganizationNotFoundError,
)
from app.services.audit_service import verify_chain


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_create_organization_basico(db):
    org = create_organization(db, name="Primeiro Comando da Capital", created_by=1)
    assert org.id is not None
    assert org.name == "Primeiro Comando da Capital"
    assert org.status == "active"
    assert org.reliability_level == "pending"


def test_create_organization_gera_audit(db):
    org = create_organization(db, name="Familia do Norte", created_by=1)
    log = db.query(AuditLog).filter_by(action="org_create").first()
    assert log is not None
    assert log.entity_id == org.id
    assert log.entity_type == "organization"


def test_create_nome_vazio_rejeitado(db):
    with pytest.raises(ValueError):
        create_organization(db, name="", created_by=1)


def test_create_nome_vazio_espacos_rejeitado(db):
    with pytest.raises(ValueError):
        create_organization(db, name="   ", created_by=1)


def test_create_com_campos_opcionais(db):
    org = create_organization(
        db,
        name="CV",
        siglas="CV",
        alcunhas="Comando Vermelho",
        org_type="faccao_prisional",
        area_atuacao="Rio de Janeiro",
        source="Inteligencia",
        reliability_level="alto",
        notes="Faccao com atuacao nacional.",
        created_by=1,
    )
    assert org.siglas == "CV"
    assert org.org_type == "faccao_prisional"
    assert org.reliability_level == "alto"


def test_update_persiste_e_audita(db):
    org = create_organization(db, name="GDE", created_by=1)
    updated = update_organization(db, org.id, name="Guardioes do Estado", updated_by=1)
    assert updated.name == "Guardioes do Estado"
    log = db.query(AuditLog).filter_by(action="org_update").first()
    assert log is not None
    assert "name" in log.metadata_json


def test_update_sem_mudanca_nao_loga(db):
    org = create_organization(db, name="Milicia Sul", created_by=1)
    count_before = db.query(AuditLog).count()
    update_organization(db, org.id, name="Milicia Sul", updated_by=1)
    assert db.query(AuditLog).count() == count_before


def test_update_org_inexistente(db):
    with pytest.raises(OrganizationNotFoundError):
        update_organization(db, 9999, name="X", updated_by=1)


def test_archive_remove_da_lista_padrao(db):
    org = create_organization(db, name="BONDE DO MORRO", created_by=1)
    archive_organization(db, org.id, updated_by=1)
    lista = list_organizations(db)
    assert all(o.id != org.id for o in lista)


def test_archive_idempotente(db):
    org = create_organization(db, name="OS MANOS", created_by=1)
    archive_organization(db, org.id, updated_by=1)
    count = db.query(AuditLog).filter_by(action="org_archive").count()
    archive_organization(db, org.id, updated_by=1)
    assert db.query(AuditLog).filter_by(action="org_archive").count() == count


def test_list_include_archived(db):
    create_organization(db, name="ATIVA", created_by=1)
    org2 = create_organization(db, name="ARQUIVADA", created_by=1)
    archive_organization(db, org2.id, updated_by=1)
    todas = list_organizations(db, include_archived=True)
    assert len(todas) == 2
    ativas = list_organizations(db)
    assert len(ativas) == 1


def test_list_ordenacao(db):
    create_organization(db, name="ZEBRA", created_by=1)
    create_organization(db, name="ALFA", created_by=1)
    lista = list_organizations(db)
    assert lista[0].name == "ALFA"
    assert lista[1].name == "ZEBRA"


def test_atomicidade_rollback_em_falha(db):
    from unittest.mock import patch
    count_before = db.query(Organization).count()
    with patch(
        "app.services.organization_service.log_action",
        side_effect=Exception("falha simulada"),
    ):
        with pytest.raises(Exception):
            create_organization(db, name="TESTE ROLLBACK", created_by=1)
    db.rollback()
    assert db.query(Organization).count() == count_before


def test_cadeia_integra_apos_operacoes(db):
    org = create_organization(db, name="PCC", org_type="faccao_prisional", created_by=1)
    update_organization(db, org.id, area_atuacao="Sao Paulo", updated_by=1)
    archive_organization(db, org.id, updated_by=1)
    result = verify_chain(db)
    assert result["ok"] is True
