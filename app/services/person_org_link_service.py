"""
CIRCE Intel Desk — Serviço de Vínculos Pessoa↔Organização (RF-005).

Regras de domínio:
  - link_type obrigatório (CA-005.3).
  - source obrigatório (CA-005.6).
  - reliability_level obrigatório; default "pending" (CA-005.6).
  - Vínculo duplicado (mesmo person_id + org_id + link_type, active=1)
    recusado com DuplicatePersonOrgLinkError → API 409.
  - Reativação silenciosa se registro removido existir (D-B10-05 por analogia).
  - Remoção é exclusão lógica: active=0 (CA-005.9).
  - Criação e remoção auditadas na mesma transação (ADR-003a, D47).

Strings de action: "person_org_link_create", "person_org_link_remove".

Sprint 01-B — Sub-passo B6.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.person_org_link import PersonOrgLink
from app.services import audit_service

_ENTITY_TYPE = "person_org_link"

LINK_TYPES_VALIDOS = {
    "membro",
    "suspeito_membro",
    "simpatizante",
    "ex_membro",
    "familiar",
    "vitima",
    "rival",
}

RELIABILITY_VALIDOS = {"pending", "baixo", "medio", "alto", "validado"}


class DuplicatePersonOrgLinkError(Exception):
    def __init__(self, person_id: int, org_id: int, link_type: str, existing_id: int):
        self.person_id = person_id
        self.org_id = org_id
        self.link_type = link_type
        self.existing_link_id = existing_id
        super().__init__(
            f"Já existe vínculo ativo id={existing_id} entre "
            f"pessoa {person_id} e organização {org_id} com tipo {link_type!r}."
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _find_active_link(
    db: Session, person_id: int, org_id: int, link_type: str
) -> Optional[PersonOrgLink]:
    stmt = (
        select(PersonOrgLink)
        .where(PersonOrgLink.person_id == person_id)
        .where(PersonOrgLink.org_id == org_id)
        .where(PersonOrgLink.link_type == link_type)
        .where(PersonOrgLink.active == 1)
    )
    return db.execute(stmt).scalars().first()


def _find_removed_link(
    db: Session, person_id: int, org_id: int, link_type: str
) -> Optional[PersonOrgLink]:
    stmt = (
        select(PersonOrgLink)
        .where(PersonOrgLink.person_id == person_id)
        .where(PersonOrgLink.org_id == org_id)
        .where(PersonOrgLink.link_type == link_type)
        .where(PersonOrgLink.active == 0)
    )
    return db.execute(stmt).scalars().first()


def create_link(
    db: Session,
    person_id: int,
    org_id: int,
    link_type: str,
    source: str,
    user_id: int,
    *,
    position: Optional[str] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    reliability_level: str = "pending",
    notes: Optional[str] = None,
) -> PersonOrgLink:
    """Cria vínculo pessoa↔organização e audita (CA-005.3–CA-005.9)."""
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        existing_active = _find_active_link(db, person_id, org_id, link_type)
        if existing_active is not None:
            db.rollback()
            raise DuplicatePersonOrgLinkError(person_id, org_id, link_type, existing_active.id)

        removed = _find_removed_link(db, person_id, org_id, link_type)
        if removed is not None:
            removed.active = 1
            removed.source = source
            removed.position = position
            removed.period_start = period_start
            removed.period_end = period_end
            removed.reliability_level = reliability_level
            removed.notes = notes
            db.flush()

            audit_service.log_action(
                db,
                action="person_org_link_create",
                user_id=user_id,
                entity_type=_ENTITY_TYPE,
                entity_id=removed.id,
                description=f"Vínculo reativado: pessoa id={person_id} → org id={org_id} como {link_type!r}",
                metadata={"person_id": person_id, "org_id": org_id, "link_type": link_type, "reactivated": True},
                manage_transaction=False,
            )
            db.commit()
            db.refresh(removed)
            return removed

        now = _now_iso()
        link = PersonOrgLink(
            person_id=person_id,
            org_id=org_id,
            link_type=link_type,
            position=position,
            period_start=period_start,
            period_end=period_end,
            source=source,
            reliability_level=reliability_level,
            notes=notes,
            active=1,
            created_at=now,
            created_by=user_id,
        )
        db.add(link)
        db.flush()

        audit_service.log_action(
            db,
            action="person_org_link_create",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=link.id,
            description=f"Vínculo criado: pessoa id={person_id} → org id={org_id} como {link_type!r}",
            metadata={"person_id": person_id, "org_id": org_id, "link_type": link_type, "reliability_level": reliability_level},
            manage_transaction=False,
        )
        db.commit()
        db.refresh(link)
        return link

    except DuplicatePersonOrgLinkError:
        raise
    except Exception:
        db.rollback()
        raise


def remove_link(
    db: Session, link_id: int, user_id: int
) -> Optional[PersonOrgLink]:
    """Remove vínculo por exclusão lógica e audita."""
    link = db.get(PersonOrgLink, link_id)
    if link is None:
        return None
    if link.active == 0:
        return link

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        link.active = 0
        db.flush()

        audit_service.log_action(
            db,
            action="person_org_link_remove",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=link.id,
            description=f"Vínculo removido: pessoa id={link.person_id} → org id={link.org_id} (tipo: {link.link_type!r})",
            metadata={"person_id": link.person_id, "org_id": link.org_id, "link_type": link.link_type},
            manage_transaction=False,
        )
        db.commit()
        db.refresh(link)
        return link

    except Exception:
        db.rollback()
        raise


def get_link(db: Session, link_id: int) -> Optional[PersonOrgLink]:
    return db.get(PersonOrgLink, link_id)


def list_links_by_org(
    db: Session, org_id: int, *, include_removed: bool = False
) -> list[PersonOrgLink]:
    """Lista vínculos de uma organização (CA-005.8)."""
    stmt = (
        select(PersonOrgLink)
        .where(PersonOrgLink.org_id == org_id)
        .order_by(PersonOrgLink.created_at.asc())
    )
    if not include_removed:
        stmt = stmt.where(PersonOrgLink.active == 1)
    return list(db.execute(stmt).scalars().all())


def list_links_by_person(
    db: Session, person_id: int, *, include_removed: bool = False
) -> list[PersonOrgLink]:
    """Lista vínculos de uma pessoa (CA-005.7)."""
    stmt = (
        select(PersonOrgLink)
        .where(PersonOrgLink.person_id == person_id)
        .order_by(PersonOrgLink.created_at.asc())
    )
    if not include_removed:
        stmt = stmt.where(PersonOrgLink.active == 1)
    return list(db.execute(stmt).scalars().all())