"""
CIRCE Intel Desk — Serviço de Casos (RF-001).

Regras de domínio do cadastro de casos:
  - Geração de case_code no padrão {ano}-{sequencial-4d} (CA-001.1).
  - Criação, edição e arquivamento, cada um auditado (CA-001.6).
  - Listagem com ordenação e filtro de arquivados (CA-001.5, CA-001.7).

Transação e auditoria (ADR-003 §2.4 + ADR-003a):
  Operações que escrevem estado seguem o contrato do ADR-003a:
    1. db.execute(text("BEGIN IMMEDIATE"))     -> lock de escrita (ADR-003 §2.3)
    2. db.add(entidade); db.flush()            -> materializa entity_id
    3. audit_service.log_action(..., manage_transaction=False)
    4. db.commit()                             -> commit único; falha -> rollback
  Assim, entidade e log vivem na MESMA transação: não há ação não-logada.

  Funções de leitura (get/list) NÃO abrem transação imediata e NÃO auditam
  (visualização de caso não é evento auditável no RF-001; auditoria de
  visualização é escopo de RF-020, tratado à parte).

Strings de action (enum 05_MODELO_DE_DADOS.md §6.4 — contrato do hash,
ADR-003 §3.2): "case_create", "case_update", "case_archive".

Sprint 01 — Bloco 8, Sub-passo 8.2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.case import Case
from app.schemas.cases import CaseCreate, CaseUpdate
from app.services import audit_service

# Tipo de entidade usado nos logs de auditoria (05_MODELO_DE_DADOS.md §3.8)
_ENTITY_TYPE = "case"

# Colunas permitidas para ordenação na listagem (CA-001.7).
# Mapeia o nome aceito na API para o atributo do modelo, evitando
# injeção de nome de coluna arbitrário vindo do cliente.
_SORTABLE = {
    "case_code": Case.case_code,
    "name": Case.name,
    "created_at": Case.created_at,
    "status": Case.status,
}


def _now_iso() -> str:
    """Timestamp ISO 8601 UTC com microsegundos e sufixo Z.

    Mesmo formato usado pelo audit_service (ADR-003 §2.1), por consistência.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def generate_case_code(db: Session) -> str:
    """Gera o próximo case_code no padrão {ano}-{NNNN} (CA-001.1).

    O sequencial é por ano: busca o maior sufixo numérico já usado em códigos
    do ano corrente e incrementa. Primeiro caso do ano -> '2026-0001'.

    Deve ser chamado DENTRO da transação imediata aberta pelo serviço de
    criação (ver create_case), para que a leitura do maior sequencial e a
    inserção subsequente fiquem sob o mesmo lock de escrita (ADR-003 §2.3),
    evitando dois casos com o mesmo código numa corrida.
    """
    year = datetime.now(timezone.utc).strftime("%Y")
    prefix = f"{year}-"

    rows = db.execute(
        select(Case.case_code).where(Case.case_code.like(f"{prefix}%"))
    ).scalars().all()

    max_seq = 0
    for code in rows:
        suffix = code[len(prefix):]
        if suffix.isdigit():
            n = int(suffix)
            if n > max_seq:
                max_seq = n

    return f"{prefix}{max_seq + 1:04d}"


def create_case(db: Session, data: CaseCreate, user_id: int) -> Case:
    """Cria um caso e registra a auditoria na mesma transação (CA-001.1, CA-001.6).

    Sequência conforme ADR-003a: BEGIN IMMEDIATE -> insere caso -> flush
    (materializa id) -> log_action(manage_transaction=False) -> commit.
    Qualquer falha faz rollback de caso e log juntos.
    """
    db.execute(text("BEGIN IMMEDIATE"))  # ADR-003 §2.3 / ADR-003a passo 1
    try:
        now = _now_iso()
        case = Case(
            case_code=generate_case_code(db),
            name=data.name,
            description=data.description,
            procedure_number=data.procedure_number,
            fact_date=data.fact_date,
            unit=data.unit,
            responsible=data.responsible,
            status="active",          # default aplicado explicitamente (D45)
            tags=data.tags,
            notes=data.notes,
            created_at=now,
            created_by=user_id,
        )
        db.add(case)
        db.flush()  # materializa case.id para usar como entity_id

        audit_service.log_action(
            db,
            action="case_create",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=case.id,
            description=f"Criação do caso {case.case_code} — {case.name}",
            manage_transaction=False,  # ADR-003a: a transação é deste serviço
        )

        db.commit()
        db.refresh(case)
        return case
    except Exception:
        db.rollback()
        raise


def update_case(
    db: Session, case_id: int, data: CaseUpdate, user_id: int
) -> Optional[Case]:
    """Edita campos de um caso e audita (CA-001.4, CA-001.6).

    Aplica apenas os campos enviados (edição parcial). case_code e status
    NÃO são alterados por aqui (case_code é imutável; arquivar é archive_case).
    Retorna None se o caso não existir.
    """
    case = db.get(Case, case_id)
    if case is None:
        return None

    # Só os campos efetivamente enviados (exclude_unset) entram na edição.
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return case  # nada a alterar; não gera log de edição vazia

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        changed_fields = []
        for field, value in changes.items():
            if getattr(case, field) != value:
                setattr(case, field, value)
                changed_fields.append(field)

        if not changed_fields:
            # Valores idênticos aos atuais: nada mudou de fato.
            db.rollback()
            return case

        case.updated_at = _now_iso()
        case.updated_by = user_id
        db.flush()

        audit_service.log_action(
            db,
            action="case_update",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=case.id,
            description=f"Edição do caso {case.case_code}",
            metadata={"changed_fields": sorted(changed_fields)},
            manage_transaction=False,
        )

        db.commit()
        db.refresh(case)
        return case
    except Exception:
        db.rollback()
        raise


def archive_case(db: Session, case_id: int, user_id: int) -> Optional[Case]:
    """Arquiva um caso (exclusão lógica) e audita (CA-001.5, CA-001.6).

    Define status='archived'. Retorna None se o caso não existir.
    Idempotente: arquivar um caso já arquivado não gera novo log.
    """
    case = db.get(Case, case_id)
    if case is None:
        return None
    if case.status == "archived":
        return case  # já arquivado; nada a fazer

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        case.status = "archived"
        case.updated_at = _now_iso()
        case.updated_by = user_id
        db.flush()

        audit_service.log_action(
            db,
            action="case_archive",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=case.id,
            description=f"Arquivamento do caso {case.case_code}",
            manage_transaction=False,
        )

        db.commit()
        db.refresh(case)
        return case
    except Exception:
        db.rollback()
        raise


def get_case(db: Session, case_id: int) -> Optional[Case]:
    """Retorna um caso por id, ou None. Leitura pura — não audita."""
    return db.get(Case, case_id)


def list_cases(
    db: Session,
    *,
    include_archived: bool = False,
    sort_by: str = "created_at",
    descending: bool = True,
) -> list[Case]:
    """Lista casos com ordenação e filtro de arquivados (CA-001.5, CA-001.7).

    Por padrão, oculta arquivados (lista padrão) e ordena por data de criação
    decrescente. sort_by aceita: case_code, name, created_at, status.
    Leitura pura — não audita.
    """
    column = _SORTABLE.get(sort_by, Case.created_at)
    order = column.desc() if descending else column.asc()

    stmt = select(Case)
    if not include_archived:
        stmt = stmt.where(Case.status != "archived")
    stmt = stmt.order_by(order)

    return list(db.execute(stmt).scalars().all())
