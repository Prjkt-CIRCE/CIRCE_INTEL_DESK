"""Teste integrado do person_service contra o audit_service real (ADR-003a).
Reproduz fielmente o session.py do projeto: engine SQLite, check_same_thread=False,
FK on, SEM isolation_level customizado, SessionLocal com expire_on_commit=False.
Espelha tests/test_case_service.py; testes extras cobrem a checagem de CPF
duplicado (CA-002.5, decisao D57) que o case_service nao tem equivalente.

Fixture 'db' definida em conftest.py (Sprint 03-0: inclui tabelas FTS5)."""
import pytest
from sqlalchemy import text

from app.schemas.persons import PersonCreate, PersonUpdate
from app.services import person_service, audit_service


def test_create_normaliza_cpf_e_audita(db):
    p = person_service.create_person(
        db, PersonCreate(full_name="Fulano de Tal", cpf="123.456.789-00"), user_id=1
    )
    assert p.cpf == "12345678900"  # normalizado para apenas digitos (CA-002.2)
    assert p.status == "active"
    assert p.reliability_level == "pending"  # default aplicado
    logs = db.execute(text("SELECT action, entity_type, entity_id FROM audit_logs")).fetchall()
    assert ("person_create", "person", p.id) in [(r[0], r[1], r[2]) for r in logs]
    result = audit_service.verify_chain(db)
    assert result["ok"] is True, result.get("error")


def test_create_sem_cpf_nao_verifica_duplicidade(db):
    p1 = person_service.create_person(db, PersonCreate(full_name="Sem CPF Um"), user_id=1)
    p2 = person_service.create_person(db, PersonCreate(full_name="Sem CPF Dois"), user_id=1)
    assert p1.cpf is None and p2.cpf is None  # dois CPFs nulos nao colidem


def test_create_cpf_duplicado_rejeitado(db):
    original = person_service.create_person(
        db, PersonCreate(full_name="Pessoa Original", cpf="111.222.333-44"), user_id=1
    )
    with pytest.raises(person_service.DuplicateCPFError) as exc_info:
        # mesmo CPF, mascara diferente - deve colidir apos normalizacao (CA-002.5)
        person_service.create_person(
            db, PersonCreate(full_name="Pessoa Duplicada", cpf="11122233344"), user_id=1
        )
    err = exc_info.value
    assert err.existing_person_id == original.id
    assert err.existing_person_name == "Pessoa Original"
    # a pessoa duplicada NAO deve ter sido persistida (rollback)
    n_pessoas = db.execute(text("SELECT COUNT(*) FROM persons")).scalar()
    assert n_pessoas == 1


def test_nome_vazio_rejeitado(db):
    with pytest.raises(Exception):
        PersonCreate(full_name="   ")


def test_reliability_invalido_rejeitado(db):
    with pytest.raises(Exception):
        PersonCreate(full_name="Alguem", reliability_level="chutometro")


def test_update_persiste_e_audita(db):
    p = person_service.create_person(db, PersonCreate(full_name="Antes"), user_id=1)
    upd = person_service.update_person(
        db, p.id, PersonUpdate(full_name="Depois", rg="1234567"), user_id=1
    )
    assert upd.full_name == "Depois"
    assert upd.rg == "1234567"
    actions = [r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()]
    assert "person_update" in actions
    assert audit_service.verify_chain(db)["ok"] is True


def test_update_sem_mudanca_real_nao_loga(db):
    p = person_service.create_person(db, PersonCreate(full_name="Igual"), user_id=1)
    n_antes = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
    person_service.update_person(db, p.id, PersonUpdate(full_name="Igual"), user_id=1)
    n_depois = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
    assert n_antes == n_depois  # nenhum log novo


def test_update_cpf_duplicado_rejeitado(db):
    p1 = person_service.create_person(
        db, PersonCreate(full_name="Um", cpf="999.888.777-66"), user_id=1
    )
    p2 = person_service.create_person(db, PersonCreate(full_name="Dois"), user_id=1)

    with pytest.raises(person_service.DuplicateCPFError) as exc_info:
        person_service.update_person(db, p2.id, PersonUpdate(cpf="99988877766"), user_id=1)
    assert exc_info.value.existing_person_id == p1.id

    # p2 nao deve ter ficado com o CPF (rollback da tentativa de update)
    db.refresh(p2)
    assert p2.cpf is None


def test_update_cpf_para_si_mesma_nao_colide(db):
    # editar OUTROS campos sem tocar no cpf ja existente nao deve disparar
    # DuplicateCPFError (a pessoa nao colide "consigo mesma").
    p = person_service.create_person(
        db, PersonCreate(full_name="Estavel", cpf="555.444.333-22"), user_id=1
    )
    upd = person_service.update_person(
        db, p.id, PersonUpdate(cpf="555.444.333-22", notes="reenvio do mesmo cpf"), user_id=1
    )
    assert upd.cpf == "55544433322"
    assert upd.notes == "reenvio do mesmo cpf"


def test_archive_idempotente_remove_da_lista_padrao(db):
    p = person_service.create_person(db, PersonCreate(full_name="Para Arquivar"), user_id=1)
    person_service.archive_person(db, p.id, user_id=1)
    padrao = person_service.list_persons(db)
    assert all(x.id != p.id for x in padrao)
    com_arquivados = person_service.list_persons(db, include_archived=True)
    assert any(x.id == p.id for x in com_arquivados)
    actions = [r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()]
    assert actions.count("person_archive") == 1

    # arquivar de novo e idempotente: nao gera segundo log
    person_service.archive_person(db, p.id, user_id=1)
    actions_depois = [r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()]
    assert actions_depois.count("person_archive") == 1


def test_atomicidade_rollback_em_falha(db, monkeypatch):
    # forca falha dentro do log_action -> pessoa NAO deve persistir
    def boom(*a, **k):
        raise RuntimeError("falha simulada no log")
    monkeypatch.setattr(person_service.audit_service, "log_action", boom)
    n_pessoas_antes = db.execute(text("SELECT COUNT(*) FROM persons")).scalar()
    with pytest.raises(RuntimeError):
        person_service.create_person(db, PersonCreate(full_name="Fantasma"), user_id=1)
    n_pessoas_depois = db.execute(text("SELECT COUNT(*) FROM persons")).scalar()
    assert n_pessoas_antes == n_pessoas_depois  # rollback reverteu a pessoa


def test_list_ordenacao(db):
    person_service.create_person(db, PersonCreate(full_name="Zebra"), user_id=1)
    person_service.create_person(db, PersonCreate(full_name="Alfa"), user_id=1)
    por_nome = person_service.list_persons(db, sort_by="full_name", descending=False)
    nomes = [p.full_name for p in por_nome]
    assert nomes == sorted(nomes)
