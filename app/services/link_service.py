"""
CIRCE Intel Desk — Serviço de Vínculos Pessoa↔Caso (RF-003).

Regras de domínio do vínculo pessoa-caso:
  - role_in_case obrigatório na camada de serviço (CA-003.3) — o banco
    aceita NULL para compatibilidade de schema, mas o serviço recusa
    vínculo sem papel declarado.
  - source obrigatório (CA-003.4).
  - reliability_level obrigatório; default "pending" (CA-003.5).
  - Vínculo duplicado (mesmo case_id + person_id + role_in_case, com
    active=1) é recusado com DuplicateLinkError → API responde 409
    (CA-003.6). A constraint UNIQUE no banco (uq_case_person_role) é a
    segunda linha de defesa; a checagem aqui é a primeira, e acontece
    dentro do BEGIN IMMEDIATE para cobrir corrida teórica.
  - Remoção é exclusão lógica: active=0 (CA-003.7). O registro permanece
    no banco para rastreabilidade; o log de auditoria registra a remoção
    (CA-003.8).
  - Criação e remoção auditadas na mesma transação que altera o dado
    (CA-003.8, ADR-003 §2.4, ADR-003a).

Transação e auditoria (ADR-003 §2.4 + ADR-003a) — MESMO contrato dos
serviços anteriores (case_service, person_service):
    1. db.execute(text("BEGIN IMMEDIATE"))     -> lock de escrita
    2. checagem de duplicidade DENTRO do lock
    3. db.add(link); db.flush()               -> materializa link.id
    4. audit_service.log_action(..., manage_transaction=False)
    5. db.commit()                             -> commit único; falha -> rollback

Strings de action (enum 05_MODELO_DE_DADOS.md §6.4 — contrato do hash,
ADR-003 §3.2): "case_person_link_create", "case_person_link_remove".
Renomear estas strings invalida a cadeia retroativamente (ADR-003 §3.2).

Sprint 01 — Bloco 10, Sub-passo 10.2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.case_person_link import CasePersonLink
from app.services import audit_service

# Tipo de entidade usado nos logs de auditoria (05_MODELO_DE_DADOS.md §3.8)
_ENTITY_TYPE = "case_person_link"

# Papéis válidos para role_in_case (CA-003.3).
# Mantido aqui como referência canônica para validação no serviço.
# O schema Pydantic (10.2) usa o mesmo conjunto.
ROLES_VALIDOS = {
    "suspeito",
    "investigado",
    "vitima",
    "testemunha",
    "envolvido",
    "interlocutor",
    "outro",
}

# Graus de confiabilidade válidos (05_MODELO_DE_DADOS.md §6.2).
RELIABILITY_VALIDOS = {"pending", "low", "medium", "high", "validated"}


class DuplicateLinkError(Exception):
    """Levantada quando já existe vínculo ativo com o mesmo caso, pessoa e papel.

    Carrega o id do vínculo existente para que a API/UI possa informar o
    operador com precisão (CA-003.6, mesmo espírito de DuplicateCPFError
    do RF-002 / D57).
    """

    def __init__(
        self,
        case_id: int,
        person_id: int,
        role_in_case: str,
        existing_link_id: int,
    ):
        self.case_id = case_id
        self.person_id = person_id
        self.role_in_case = role_in_case
        self.existing_link_id = existing_link_id
        super().__init__(
            f"Já existe vínculo ativo id={existing_link_id} entre "
            f"pessoa {person_id} e caso {case_id} com papel {role_in_case!r}."
        )


def _now_iso() -> str:
    """Timestamp ISO 8601 UTC com microsegundos e sufixo Z.

    Mesmo formato do audit_service (ADR-003 §2.1) e dos demais serviços,
    por consistência.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _find_active_link(
    db: Session,
    case_id: int,
    person_id: int,
    role_in_case: str,
) -> Optional[CasePersonLink]:
    """Busca vínculo ativo com a mesma tripla (case_id, person_id, role_in_case).

    Deve ser chamada DENTRO da transação imediata aberta por create_link,
    para que a leitura e a inserção subsequente fiquem sob o mesmo lock
    de escrita (mesmo raciocínio de generate_case_code no case_service).
    """
    stmt = (
        select(CasePersonLink)
        .where(CasePersonLink.case_id == case_id)
        .where(CasePersonLink.person_id == person_id)
        .where(CasePersonLink.role_in_case == role_in_case)
        .where(CasePersonLink.active == 1)
    )
    return db.execute(stmt).scalars().first()


def _find_removed_link(
    db: Session,
    case_id: int,
    person_id: int,
    role_in_case: str,
) -> Optional[CasePersonLink]:
    """Busca vínculo REMOVIDO (active=0) com a mesma tripla.

    Usado por create_link para reativar em vez de inserir novo registro,
    evitando violação da constraint UNIQUE (D-B10-05).
    Deve ser chamada DENTRO da transação imediata aberta por create_link.
    """
    stmt = (
        select(CasePersonLink)
        .where(CasePersonLink.case_id == case_id)
        .where(CasePersonLink.person_id == person_id)
        .where(CasePersonLink.role_in_case == role_in_case)
        .where(CasePersonLink.active == 0)
    )
    return db.execute(stmt).scalars().first()


def create_link(
    db: Session,
    case_id: int,
    person_id: int,
    role_in_case: str,
    source: str,
    user_id: int,
    *,
    reliability_level: str = "pending",
    notes: Optional[str] = None,
) -> CasePersonLink:
    """Cria vínculo pessoa↔caso e audita na mesma transação (CA-003.3–CA-003.8).

    Sequência conforme ADR-003a:
      BEGIN IMMEDIATE -> checa duplicidade -> insere link -> flush ->
      log_action(manage_transaction=False) -> commit.
    Qualquer falha faz rollback de link e log juntos.

    Levanta DuplicateLinkError se já existe vínculo ativo com a mesma
    tripla (case_id, person_id, role_in_case) — CA-003.6.

    Parâmetros:
      case_id          — id do caso (deve existir no banco).
      person_id        — id da pessoa (deve existir no banco).
      role_in_case     — papel: suspeito|investigado|vitima|testemunha|
                         envolvido|interlocutor|outro (CA-003.3).
      source           — fonte da informação (CA-003.4).
      user_id          — id do operador autenticado.
      reliability_level — grau de confiabilidade (CA-003.5); default "pending".
      notes            — observação livre, opcional.
    """
    db.execute(text("BEGIN IMMEDIATE"))  # ADR-003 §2.3 / ADR-003a passo 1
    try:
        # Passo 1: verifica duplicidade ATIVA (CA-003.6).
        existing_active = _find_active_link(db, case_id, person_id, role_in_case)
        if existing_active is not None:
            db.rollback()
            raise DuplicateLinkError(case_id, person_id, role_in_case, existing_active.id)

        # Passo 2: verifica se existe registro REMOVIDO (D-B10-05).
        # Se sim, reativa em vez de inserir — evita violação da constraint UNIQUE.
        removed = _find_removed_link(db, case_id, person_id, role_in_case)
        if removed is not None:
            # Reativação: atualiza campos e religa o vínculo.
            removed.active = 1
            removed.source = source
            removed.reliability_level = reliability_level
            removed.notes = notes
            db.flush()

            audit_service.log_action(
                db,
                action="case_person_link_create",
                user_id=user_id,
                entity_type=_ENTITY_TYPE,
                entity_id=removed.id,
                description=(
                    f"Vínculo reativado: pessoa id={person_id} → caso id={case_id} "
                    f"como {role_in_case!r}"
                ),
                metadata={
                    "case_id": case_id,
                    "person_id": person_id,
                    "role_in_case": role_in_case,
                    "reliability_level": reliability_level,
                    "reactivated": True,
                },
                manage_transaction=False,
            )

            db.commit()
            db.refresh(removed)
            return removed

        # Passo 3: inserção normal (nenhum registro existente).
        now = _now_iso()
        link = CasePersonLink(
            case_id=case_id,
            person_id=person_id,
            role_in_case=role_in_case,
            source=source,
            reliability_level=reliability_level,
            notes=notes,
            active=1,
            created_at=now,
            created_by=user_id,
        )
        db.add(link)
        db.flush()  # materializa link.id para usar como entity_id

        audit_service.log_action(
            db,
            action="case_person_link_create",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=link.id,
            description=(
                f"Vínculo criado: pessoa id={person_id} → caso id={case_id} "
                f"como {role_in_case!r}"
            ),
            metadata={
                "case_id": case_id,
                "person_id": person_id,
                "role_in_case": role_in_case,
                "reliability_level": reliability_level,
            },
            manage_transaction=False,  # ADR-003a: transação pertence a este serviço
        )

        db.commit()
        db.refresh(link)
        return link

    except DuplicateLinkError:
        # rollback já executado antes de levantar; apenas repropaga.
        raise
    except Exception:
        db.rollback()
        raise


def remove_link(
    db: Session,
    link_id: int,
    user_id: int,
) -> Optional[CasePersonLink]:
    """Remove vínculo por exclusão lógica (active=0) e audita (CA-003.7, CA-003.8).

    Retorna None se o vínculo não existir.
    Idempotente: remover vínculo já removido (active=0) não gera novo log
    (mesmo espírito de idempotência de archive_case / archive_person).
    """
    link = db.get(CasePersonLink, link_id)
    if link is None:
        return None
    if link.active == 0:
        return link  # já removido; sem log de remoção repetida

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        link.active = 0
        db.flush()

        audit_service.log_action(
            db,
            action="case_person_link_remove",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=link.id,
            description=(
                f"Vínculo removido: pessoa id={link.person_id} → "
                f"caso id={link.case_id} (papel: {link.role_in_case!r})"
            ),
            metadata={
                "case_id": link.case_id,
                "person_id": link.person_id,
                "role_in_case": link.role_in_case,
            },
            manage_transaction=False,
        )

        db.commit()
        db.refresh(link)
        return link

    except Exception:
        db.rollback()
        raise


def get_link(db: Session, link_id: int) -> Optional[CasePersonLink]:
    """Retorna um vínculo por id, ou None. Leitura pura — não audita."""
    return db.get(CasePersonLink, link_id)


def list_links_by_case(
    db: Session,
    case_id: int,
    *,
    include_removed: bool = False,
) -> list[CasePersonLink]:
    """Lista vínculos ativos de um caso (CA-003.1).

    Por padrão, retorna apenas vínculos com active=1.
    include_removed=True retorna todos (ativo + removido) — útil para
    auditoria interna; não é exposto na UI padrão do MVP-0.
    Leitura pura — não audita.
    """
    stmt = (
        select(CasePersonLink)
        .where(CasePersonLink.case_id == case_id)
        .order_by(CasePersonLink.created_at.asc())
    )
    if not include_removed:
        stmt = stmt.where(CasePersonLink.active == 1)

    return list(db.execute(stmt).scalars().all())


def list_links_by_person(
    db: Session,
    person_id: int,
    *,
    include_removed: bool = False,
) -> list[CasePersonLink]:
    """Lista vínculos ativos de uma pessoa (CA-003.2).

    Por padrão, retorna apenas vínculos com active=1.
    Leitura pura — não audita.
    """
    stmt = (
        select(CasePersonLink)
        .where(CasePersonLink.person_id == person_id)
        .order_by(CasePersonLink.created_at.asc())
    )
    if not include_removed:
        stmt = stmt.where(CasePersonLink.active == 1)

    return list(db.execute(stmt).scalars().all())
