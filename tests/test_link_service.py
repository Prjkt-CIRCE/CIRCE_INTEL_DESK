"""Teste integrado do link_service contra o audit_service real (ADR-003a).

Reproduz fielmente o session.py do projeto: engine SQLite em memoria,
check_same_thread=False, FK on, SEM isolation_level customizado,
SessionLocal com expire_on_commit=False.

Espelha o padrao de test_case_service.py e test_person_service.py.
Testes extras cobrem a checagem de vinculo duplicado (CA-003.6,
DuplicateLinkError) e a exclusao logica (CA-003.7).

NOTA DE SCHEMA (D-B10-02): a constraint UNIQUE(case_id, person_id,
role_in_case) no banco nao e parcial - aplica-se a todos os registros,
inclusive os com active=0. Portanto, apos remocao logica de um vinculo,
nao e possivel recriar o mesmo vinculo (mesma tripla) sem exclusao fisica
do registro removido. O CA-003.7 nao exige recracao - este e o
comportamento correto e defensivo. Recracao por procedimento
administrativo fica fora do escopo do MVP-0. Se futuramente for
necessario, exige migracao para partial index ou campo deleted_at na
constraint - novo ADR antes de implementar.

Sprint 01 - Bloco 10, Sub-passo 10.3.

Fixture 'db' definida em conftest.py (Sprint 03-0: inclui tabelas FTS5).
"""
import pytest
from sqlalchemy import text

from app.schemas.cases import CaseCreate
from app.schemas.persons import PersonCreate
from app.services import link_service, audit_service, case_service, person_service


# ---------------------------------------------------------------------------
# Helpers - criam caso e pessoa via servicos reais (nao SQL bruto),
# para que o audit log esteja integro antes dos testes de vinculo.
# ---------------------------------------------------------------------------

def _cria_caso(db, nome="Caso Teste"):
    return case_service.create_case(db, CaseCreate(name=nome), user_id=1)


def _cria_pessoa(db, nome="Pessoa Teste"):
    return person_service.create_person(db, PersonCreate(full_name=nome), user_id=1)


# ---------------------------------------------------------------------------
# Testes - criacao de vinculo (CA-003.3 a CA-003.6, CA-003.8)
# ---------------------------------------------------------------------------

def test_create_link_basico_e_audita(db):
    """Cria vinculo com campos obrigatorios e verifica auditoria (CA-003.3-CA-003.5, CA-003.8)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db,
        case_id=caso.id,
        person_id=pessoa.id,
        role_in_case="suspeito",
        source="Relatorio de inteligencia 001/2026",
        user_id=1,
        reliability_level="medium",
    )

    assert link.id is not None
    assert link.case_id == caso.id
    assert link.person_id == pessoa.id
    assert link.role_in_case == "suspeito"
    assert link.reliability_level == "medium"
    assert link.active == 1

    actions = [
        r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()
    ]
    assert "case_person_link_create" in actions

    result = audit_service.verify_chain(db)
    assert result["ok"] is True, result.get("error")


def test_create_link_reliability_default_pending(db):
    """reliability_level omitido -> default 'pending' (CA-003.5)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db,
        case_id=caso.id,
        person_id=pessoa.id,
        role_in_case="testemunha",
        source="Declaracao verbal",
        user_id=1,
    )

    assert link.reliability_level == "pending"


def test_create_link_com_notes(db):
    """notes opcional e persistido corretamente."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db,
        case_id=caso.id,
        person_id=pessoa.id,
        role_in_case="envolvido",
        source="BO 2026/001",
        user_id=1,
        notes="Flagrado nas imediações no dia dos fatos.",
    )

    assert link.notes == "Flagrado nas imediações no dia dos fatos."


def test_create_link_duplicado_rejeitado(db):
    """Vinculo duplicado (mesmo caso + pessoa + papel) levanta DuplicateLinkError (CA-003.6)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    original = link_service.create_link(
        db,
        case_id=caso.id,
        person_id=pessoa.id,
        role_in_case="investigado",
        source="Fonte A",
        user_id=1,
    )

    with pytest.raises(link_service.DuplicateLinkError) as exc_info:
        link_service.create_link(
            db,
            case_id=caso.id,
            person_id=pessoa.id,
            role_in_case="investigado",
            source="Fonte B",
            user_id=1,
        )

    err = exc_info.value
    assert err.existing_link_id == original.id
    assert err.case_id == caso.id
    assert err.person_id == pessoa.id
    assert err.role_in_case == "investigado"

    n_links = db.execute(text("SELECT COUNT(*) FROM case_person_links")).scalar()
    assert n_links == 1


def test_create_link_mesmo_par_papeis_diferentes_permitido(db):
    """Mesma pessoa + caso com papeis diferentes -> dois vinculos distintos (CA-003.6)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link1 = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="vitima", source="BO", user_id=1,
    )
    link2 = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="testemunha", source="Declaracao", user_id=1,
    )

    assert link1.id != link2.id
    assert link1.role_in_case == "vitima"
    assert link2.role_in_case == "testemunha"


def test_create_link_pessoa_diferente_mesmo_caso_permitido(db):
    """Pessoas diferentes podem ter o mesmo papel no mesmo caso."""
    caso = _cria_caso(db)
    p1 = _cria_pessoa(db, "Pessoa Um")
    p2 = _cria_pessoa(db, "Pessoa Dois")

    link1 = link_service.create_link(
        db, case_id=caso.id, person_id=p1.id,
        role_in_case="suspeito", source="Fonte", user_id=1,
    )
    link2 = link_service.create_link(
        db, case_id=caso.id, person_id=p2.id,
        role_in_case="suspeito", source="Fonte", user_id=1,
    )

    assert link1.id != link2.id


# ---------------------------------------------------------------------------
# Testes - remocao de vinculo (CA-003.7, CA-003.8)
# ---------------------------------------------------------------------------

def test_remove_link_exclusao_logica_e_audita(db):
    """Remocao define active=0 e gera log case_person_link_remove (CA-003.7, CA-003.8)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="interlocutor", source="OSINT", user_id=1,
    )

    removido = link_service.remove_link(db, link_id=link.id, user_id=1)

    assert removido.active == 0

    n_total = db.execute(text("SELECT COUNT(*) FROM case_person_links")).scalar()
    assert n_total == 1

    actions = [
        r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()
    ]
    assert "case_person_link_remove" in actions

    assert audit_service.verify_chain(db)["ok"] is True


def test_remove_link_idempotente(db):
    """Remover vinculo ja removido nao gera segundo log de remocao."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="outro", source="Informante", user_id=1,
    )
    link_service.remove_link(db, link_id=link.id, user_id=1)

    n_logs_antes = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
    link_service.remove_link(db, link_id=link.id, user_id=1)
    n_logs_depois = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
    assert n_logs_antes == n_logs_depois


def test_remove_link_inexistente_retorna_none(db):
    """Remover link que nao existe retorna None sem levantar excecao."""
    resultado = link_service.remove_link(db, link_id=9999, user_id=1)
    assert resultado is None


def test_create_link_apos_remocao_reativa_registro(db):
    """Apos remocao logica, recriar o mesmo vinculo REATIVA o registro (D-B10-05)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link_original = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="suspeito", source="Fonte A", user_id=1,
        reliability_level="low",
    )
    id_original = link_original.id

    link_service.remove_link(db, link_id=id_original, user_id=1)

    link_reativado = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="suspeito", source="Fonte B - nova evidencia", user_id=1,
        reliability_level="high",
        notes="Reincluido apos confirmacao.",
    )

    assert link_reativado.id == id_original
    assert link_reativado.active == 1
    assert link_reativado.source == "Fonte B - nova evidencia"
    assert link_reativado.reliability_level == "high"
    assert link_reativado.notes == "Reincluido apos confirmacao."

    n_links = db.execute(text("SELECT COUNT(*) FROM case_person_links")).scalar()
    assert n_links == 1

    assert audit_service.verify_chain(db)["ok"] is True


# ---------------------------------------------------------------------------
# Testes - listagem (CA-003.1, CA-003.2)
# ---------------------------------------------------------------------------

def test_list_links_by_case(db):
    """Listagem por caso retorna apenas vinculos ativos daquele caso (CA-003.1)."""
    caso1 = _cria_caso(db, "Caso Um")
    caso2 = _cria_caso(db, "Caso Dois")
    p1 = _cria_pessoa(db, "Alpha")
    p2 = _cria_pessoa(db, "Beta")

    link_service.create_link(db, case_id=caso1.id, person_id=p1.id, role_in_case="suspeito", source="Fonte", user_id=1)
    link_service.create_link(db, case_id=caso1.id, person_id=p2.id, role_in_case="vitima", source="Fonte", user_id=1)
    link_service.create_link(db, case_id=caso2.id, person_id=p1.id, role_in_case="testemunha", source="Fonte", user_id=1)

    links_caso1 = link_service.list_links_by_case(db, caso1.id)
    assert len(links_caso1) == 2
    assert all(lk.case_id == caso1.id for lk in links_caso1)

    links_caso2 = link_service.list_links_by_case(db, caso2.id)
    assert len(links_caso2) == 1


def test_list_links_by_person(db):
    """Listagem por pessoa retorna apenas vinculos ativos daquela pessoa (CA-003.2)."""
    caso1 = _cria_caso(db, "Caso A")
    caso2 = _cria_caso(db, "Caso B")
    pessoa = _cria_pessoa(db, "Fulano")
    outra = _cria_pessoa(db, "Outra")

    link_service.create_link(db, case_id=caso1.id, person_id=pessoa.id, role_in_case="investigado", source="Fonte", user_id=1)
    link_service.create_link(db, case_id=caso2.id, person_id=pessoa.id, role_in_case="suspeito", source="Fonte", user_id=1)
    link_service.create_link(db, case_id=caso1.id, person_id=outra.id, role_in_case="testemunha", source="Fonte", user_id=1)

    links_pessoa = link_service.list_links_by_person(db, pessoa.id)
    assert len(links_pessoa) == 2
    assert all(lk.person_id == pessoa.id for lk in links_pessoa)


def test_list_by_case_exclui_removidos_por_padrao(db):
    """Vinculos com active=0 nao aparecem na listagem padrao."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(db, case_id=caso.id, person_id=pessoa.id, role_in_case="envolvido", source="Fonte", user_id=1)
    link_service.remove_link(db, link_id=link.id, user_id=1)

    ativos = link_service.list_links_by_case(db, caso.id)
    assert len(ativos) == 0

    todos = link_service.list_links_by_case(db, caso.id, include_removed=True)
    assert len(todos) == 1


def test_list_by_person_exclui_removidos_por_padrao(db):
    """Analogo ao anterior, mas via list_links_by_person."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(db, case_id=caso.id, person_id=pessoa.id, role_in_case="outro", source="Fonte", user_id=1)
    link_service.remove_link(db, link_id=link.id, user_id=1)

    ativos = link_service.list_links_by_person(db, pessoa.id)
    assert len(ativos) == 0

    todos = link_service.list_links_by_person(db, pessoa.id, include_removed=True)
    assert len(todos) == 1


# ---------------------------------------------------------------------------
# Testes - get_link
# ---------------------------------------------------------------------------

def test_get_link_existente(db):
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)
    link = link_service.create_link(db, case_id=caso.id, person_id=pessoa.id, role_in_case="suspeito", source="Fonte", user_id=1)
    recuperado = link_service.get_link(db, link.id)
    assert recuperado is not None
    assert recuperado.id == link.id


def test_get_link_inexistente_retorna_none(db):
    resultado = link_service.get_link(db, 9999)
    assert resultado is None


# ---------------------------------------------------------------------------
# Testes - atomicidade e integridade da cadeia (ADR-003, ADR-003a)
# ---------------------------------------------------------------------------

def test_atomicidade_rollback_em_falha_de_log(db, monkeypatch):
    """Falha no log_action reverte o vinculo - nenhuma acao nao-logada (ADR-003 §2.4)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    def boom(*a, **k):
        raise RuntimeError("falha simulada no log")

    monkeypatch.setattr(link_service.audit_service, "log_action", boom)

    n_links_antes = db.execute(text("SELECT COUNT(*) FROM case_person_links")).scalar()

    with pytest.raises(RuntimeError):
        link_service.create_link(
            db, case_id=caso.id, person_id=pessoa.id,
            role_in_case="suspeito", source="Fonte", user_id=1,
        )

    n_links_depois = db.execute(text("SELECT COUNT(*) FROM case_person_links")).scalar()
    assert n_links_antes == n_links_depois


def test_cadeia_integra_apos_multiplas_operacoes(db):
    """Cadeia de auditoria permanece integra apos sequencia completa de operacoes."""
    caso = _cria_caso(db)
    p1 = _cria_pessoa(db, "Alpha")
    p2 = _cria_pessoa(db, "Beta")

    link1 = link_service.create_link(db, case_id=caso.id, person_id=p1.id, role_in_case="suspeito", source="Fonte A", user_id=1)
    link_service.create_link(db, case_id=caso.id, person_id=p2.id, role_in_case="vitima", source="Fonte B", user_id=1)
    link_service.remove_link(db, link_id=link1.id, user_id=1)

    result = audit_service.verify_chain(db)
    assert result["ok"] is True, result.get("error")
