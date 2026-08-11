"""Teste integrado do link_service contra o audit_service real (ADR-003a).

Reproduz fielmente o session.py do projeto: engine SQLite em memória,
check_same_thread=False, FK on, SEM isolation_level customizado,
SessionLocal com expire_on_commit=False.

Espelha o padrão de test_case_service.py e test_person_service.py.
Testes extras cobrem a checagem de vínculo duplicado (CA-003.6,
DuplicateLinkError) e a exclusão lógica (CA-003.7).

NOTA DE SCHEMA (D-B10-02): a constraint UNIQUE(case_id, person_id,
role_in_case) no banco não é parcial — aplica-se a todos os registros,
inclusive os com active=0. Portanto, após remoção lógica de um vínculo,
não é possível recriar o mesmo vínculo (mesma tripla) sem exclusão física
do registro removido. O CA-003.7 não exige recriação — este é o
comportamento correto e defensivo. Recriação por procedimento
administrativo fica fora do escopo do MVP-0. Se futuramente for
necessário, exige migração para partial index ou campo deleted_at na
constraint — novo ADR antes de implementar.

Sprint 01 — Bloco 10, Sub-passo 10.3.
"""
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
import app.models.case            # noqa: F401  (registra tabela cases)
import app.models.person          # noqa: F401  (registra tabela persons)
import app.models.case_person_link  # noqa: F401  (registra tabela case_person_links)
import app.models.audit_log       # noqa: F401  (registra tabela audit_logs)

from app.schemas.cases import CaseCreate
from app.schemas.persons import PersonCreate
from app.services import link_service, audit_service, case_service, person_service


# ---------------------------------------------------------------------------
# Fixture principal
# ---------------------------------------------------------------------------

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
    with engine.connect() as conn:
        conn.execute(text('CREATE VIRTUAL TABLE IF NOT EXISTS fts_cases USING fts5(case_id UNINDEXED, name, case_code, description, unit, responsible, tokenize="unicode61")'))
        conn.execute(text('CREATE VIRTUAL TABLE IF NOT EXISTS fts_persons USING fts5(person_id UNINDEXED, full_name, aliases, notes, tokenize="unicode61")'))
        conn.execute(text('CREATE VIRTUAL TABLE IF NOT EXISTS fts_organizations USING fts5(org_id UNINDEXED, name, aliases, description, tokenize="unicode61")'))
        conn.execute(text('CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(document_id UNINDEXED, original_filename, title, tokenize="unicode61")'))
        conn.commit()
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    s = SessionLocal()

    # Operador base (id=1) — usado como created_by em todas as operações.
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


# ---------------------------------------------------------------------------
# Helpers — criam caso e pessoa via serviços reais (não SQL bruto),
# para que o audit log esteja íntegro antes dos testes de vínculo.
# ---------------------------------------------------------------------------

def _cria_caso(db, nome="Caso Teste"):
    return case_service.create_case(db, CaseCreate(name=nome), user_id=1)


def _cria_pessoa(db, nome="Pessoa Teste"):
    return person_service.create_person(db, PersonCreate(full_name=nome), user_id=1)


# ---------------------------------------------------------------------------
# Testes — criação de vínculo (CA-003.3 a CA-003.6, CA-003.8)
# ---------------------------------------------------------------------------

def test_create_link_basico_e_audita(db):
    """Cria vínculo com campos obrigatórios e verifica auditoria (CA-003.3–CA-003.5, CA-003.8)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db,
        case_id=caso.id,
        person_id=pessoa.id,
        role_in_case="suspeito",
        source="Relatório de inteligência nº 001/2026",
        user_id=1,
        reliability_level="medium",
    )

    assert link.id is not None
    assert link.case_id == caso.id
    assert link.person_id == pessoa.id
    assert link.role_in_case == "suspeito"
    assert link.source == "Relatório de inteligência nº 001/2026"
    assert link.reliability_level == "medium"
    assert link.active == 1

    # Auditoria: deve existir um registro case_person_link_create
    actions = [
        r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()
    ]
    assert "case_person_link_create" in actions

    # Cadeia íntegra após a operação
    result = audit_service.verify_chain(db)
    assert result["ok"] is True, result.get("error")


def test_create_link_reliability_default_pending(db):
    """reliability_level omitido → default 'pending' (CA-003.5)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db,
        case_id=caso.id,
        person_id=pessoa.id,
        role_in_case="testemunha",
        source="Declaração verbal",
        user_id=1,
        # reliability_level não informado
    )

    assert link.reliability_level == "pending"


def test_create_link_com_notes(db):
    """notes opcional é persistido corretamente."""
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
    """Vínculo duplicado (mesmo caso + pessoa + papel) levanta DuplicateLinkError (CA-003.6)."""
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
            role_in_case="investigado",  # mesmo papel → duplicado
            source="Fonte B",
            user_id=1,
        )

    err = exc_info.value
    assert err.existing_link_id == original.id
    assert err.case_id == caso.id
    assert err.person_id == pessoa.id
    assert err.role_in_case == "investigado"

    # Apenas o vínculo original deve existir (rollback da tentativa duplicada)
    n_links = db.execute(text("SELECT COUNT(*) FROM case_person_links")).scalar()
    assert n_links == 1


def test_create_link_mesmo_par_papeis_diferentes_permitido(db):
    """Mesma pessoa + caso com papéis diferentes → dois vínculos distintos (CA-003.6).

    A constraint UNIQUE é na tripla (case_id, person_id, role_in_case).
    Uma pessoa pode ser 'testemunha' E 'vítima' no mesmo caso.
    """
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link1 = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="vitima", source="BO", user_id=1,
    )
    link2 = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="testemunha", source="Declaração", user_id=1,
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
# Testes — remoção de vínculo (CA-003.7, CA-003.8)
# ---------------------------------------------------------------------------

def test_remove_link_exclusao_logica_e_audita(db):
    """Remoção define active=0 e gera log case_person_link_remove (CA-003.7, CA-003.8)."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="interlocutor", source="OSINT", user_id=1,
    )

    removido = link_service.remove_link(db, link_id=link.id, user_id=1)

    assert removido.active == 0  # exclusão lógica, não física

    # O registro ainda existe no banco
    n_total = db.execute(text("SELECT COUNT(*) FROM case_person_links")).scalar()
    assert n_total == 1

    # Log de remoção presente
    actions = [
        r[0] for r in db.execute(text("SELECT action FROM audit_logs")).fetchall()
    ]
    assert "case_person_link_remove" in actions

    # Cadeia íntegra
    assert audit_service.verify_chain(db)["ok"] is True


def test_remove_link_idempotente(db):
    """Remover vínculo já removido não gera segundo log de remoção."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="outro", source="Informante", user_id=1,
    )
    link_service.remove_link(db, link_id=link.id, user_id=1)

    n_logs_antes = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()

    # segunda remoção — idempotente
    link_service.remove_link(db, link_id=link.id, user_id=1)

    n_logs_depois = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
    assert n_logs_antes == n_logs_depois  # nenhum log novo gerado


def test_remove_link_inexistente_retorna_none(db):
    """Remover link que não existe retorna None sem levantar exceção."""
    resultado = link_service.remove_link(db, link_id=9999, user_id=1)
    assert resultado is None


def test_create_link_apos_remocao_reativa_registro(db):
    """Após remoção lógica, recriar o mesmo vínculo REATIVA o registro (D-B10-05).

    O operador pode incluir, remover e reincluir vínculos livremente.
    A reativação atualiza source, reliability_level e notes com os novos valores
    e gera log case_person_link_create com reactivated=True no metadata.
    O id do registro é o mesmo (não cria novo row), mas os dados são atualizados.
    """
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    # Cria o vínculo original
    link_original = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="suspeito", source="Fonte A", user_id=1,
        reliability_level="low",
    )
    id_original = link_original.id

    # Remove
    link_service.remove_link(db, link_id=id_original, user_id=1)

    # Recria com novos dados — deve reativar sem erro
    link_reativado = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="suspeito", source="Fonte B — nova evidência", user_id=1,
        reliability_level="high",
        notes="Reincluído após confirmação.",
    )

    # Mesmo id (reativação, não nova inserção)
    assert link_reativado.id == id_original
    assert link_reativado.active == 1
    assert link_reativado.source == "Fonte B — nova evidência"
    assert link_reativado.reliability_level == "high"
    assert link_reativado.notes == "Reincluído após confirmação."

    # Apenas um registro no banco (não criou duplicata)
    n_links = db.execute(text("SELECT COUNT(*) FROM case_person_links")).scalar()
    assert n_links == 1

    # Cadeia íntegra
    assert audit_service.verify_chain(db)["ok"] is True


# ---------------------------------------------------------------------------
# Testes — listagem (CA-003.1, CA-003.2)
# ---------------------------------------------------------------------------

def test_list_links_by_case(db):
    """Listagem por caso retorna apenas vínculos ativos daquele caso (CA-003.1)."""
    caso1 = _cria_caso(db, "Caso Um")
    caso2 = _cria_caso(db, "Caso Dois")
    p1 = _cria_pessoa(db, "Alpha")
    p2 = _cria_pessoa(db, "Beta")

    link_service.create_link(
        db, case_id=caso1.id, person_id=p1.id,
        role_in_case="suspeito", source="Fonte", user_id=1,
    )
    link_service.create_link(
        db, case_id=caso1.id, person_id=p2.id,
        role_in_case="vitima", source="Fonte", user_id=1,
    )
    link_service.create_link(
        db, case_id=caso2.id, person_id=p1.id,
        role_in_case="testemunha", source="Fonte", user_id=1,
    )

    links_caso1 = link_service.list_links_by_case(db, caso1.id)
    assert len(links_caso1) == 2
    assert all(lk.case_id == caso1.id for lk in links_caso1)

    links_caso2 = link_service.list_links_by_case(db, caso2.id)
    assert len(links_caso2) == 1


def test_list_links_by_person(db):
    """Listagem por pessoa retorna apenas vínculos ativos daquela pessoa (CA-003.2)."""
    caso1 = _cria_caso(db, "Caso A")
    caso2 = _cria_caso(db, "Caso B")
    pessoa = _cria_pessoa(db, "Fulano")
    outra = _cria_pessoa(db, "Outra")

    link_service.create_link(
        db, case_id=caso1.id, person_id=pessoa.id,
        role_in_case="investigado", source="Fonte", user_id=1,
    )
    link_service.create_link(
        db, case_id=caso2.id, person_id=pessoa.id,
        role_in_case="suspeito", source="Fonte", user_id=1,
    )
    link_service.create_link(
        db, case_id=caso1.id, person_id=outra.id,
        role_in_case="testemunha", source="Fonte", user_id=1,
    )

    links_pessoa = link_service.list_links_by_person(db, pessoa.id)
    assert len(links_pessoa) == 2
    assert all(lk.person_id == pessoa.id for lk in links_pessoa)


def test_list_by_case_exclui_removidos_por_padrao(db):
    """Vínculos com active=0 não aparecem na listagem padrão."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="envolvido", source="Fonte", user_id=1,
    )
    link_service.remove_link(db, link_id=link.id, user_id=1)

    ativos = link_service.list_links_by_case(db, caso.id)
    assert len(ativos) == 0

    todos = link_service.list_links_by_case(db, caso.id, include_removed=True)
    assert len(todos) == 1


def test_list_by_person_exclui_removidos_por_padrao(db):
    """Análogo ao anterior, mas via list_links_by_person."""
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)

    link = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="outro", source="Fonte", user_id=1,
    )
    link_service.remove_link(db, link_id=link.id, user_id=1)

    ativos = link_service.list_links_by_person(db, pessoa.id)
    assert len(ativos) == 0

    todos = link_service.list_links_by_person(db, pessoa.id, include_removed=True)
    assert len(todos) == 1


# ---------------------------------------------------------------------------
# Testes — get_link
# ---------------------------------------------------------------------------

def test_get_link_existente(db):
    caso = _cria_caso(db)
    pessoa = _cria_pessoa(db)
    link = link_service.create_link(
        db, case_id=caso.id, person_id=pessoa.id,
        role_in_case="suspeito", source="Fonte", user_id=1,
    )
    recuperado = link_service.get_link(db, link.id)
    assert recuperado is not None
    assert recuperado.id == link.id


def test_get_link_inexistente_retorna_none(db):
    resultado = link_service.get_link(db, 9999)
    assert resultado is None


# ---------------------------------------------------------------------------
# Testes — atomicidade e integridade da cadeia (ADR-003, ADR-003a)
# ---------------------------------------------------------------------------

def test_atomicidade_rollback_em_falha_de_log(db, monkeypatch):
    """Falha no log_action reverte o vínculo — nenhuma ação não-logada (ADR-003 §2.4)."""
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
    assert n_links_antes == n_links_depois  # rollback reverteu o vínculo


def test_cadeia_integra_apos_multiplas_operacoes(db):
    """Cadeia de auditoria permanece íntegra após sequência completa de operações."""
    caso = _cria_caso(db)
    p1 = _cria_pessoa(db, "Alpha")
    p2 = _cria_pessoa(db, "Beta")

    # Cria dois vínculos com papéis diferentes
    link1 = link_service.create_link(
        db, case_id=caso.id, person_id=p1.id,
        role_in_case="suspeito", source="Fonte A", user_id=1,
    )
    link_service.create_link(
        db, case_id=caso.id, person_id=p2.id,
        role_in_case="vitima", source="Fonte B", user_id=1,
    )

    # Remove um
    link_service.remove_link(db, link_id=link1.id, user_id=1)

    # Cadeia deve estar íntegra ao final
    result = audit_service.verify_chain(db)
    assert result["ok"] is True, result.get("error")
