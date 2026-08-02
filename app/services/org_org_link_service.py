"""
CIRCE Intel Desk — Serviço de Vínculos Organização↔Organização (RF-006).

Regras:
  - relation_type obrigatório (CA-006.2).
  - source obrigatório.
  - org_a_id != org_b_id (CA-006.5) — enforced por CheckConstraint no modelo.
  - Sem deduplicação por (org_a, org_b, tipo) — múltiplas relações do mesmo
    tipo entre as mesmas organizações são permitidas (ex: rivalidade em 2020
    e aliança em 2022). Remoção é exclusão lógica.
  - Criação e remoção auditadas (CA-006.7, ADR-003a, D47).

Sprint 01-B — Sub-passo B7.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.org_org_link import OrgOrgLink
from app.services import audit_service

_ENTITY_TYPE = "org_org_link"

RELATION_TYPES_VALIDOS = {
    "rivalidade", "alianca", "dissidencia", "fusao", "outra"
}

RELIABILITY_VALIDOS = {"pending", "baixo", "medio", "alto", "validado"}


class SameOrgError(Exception):
    """Tentativa de vincular organização a si mesma."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def create_link(
    db: Session,
    org_a_id: int,
    org_b_id: int,
    relation_type: str,
    source: str,
    user_id: int,
    *,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    reliability_level: str = "pending",
    notes: Optional[str] = None,
) -> OrgOrgLink:
    """Cria relação entre duas organizações distintas e audita."""
    if org_a_id == org_b_id:
        raise SameOrgError("Não é possível vincular uma organização a si mesma.")

    now = _now_iso()
    link = OrgOrgLink(
        org_a_id=org_a_id,
        org_b_id=org_b_id,
        relation_type=relation_type,
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
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise SameOrgError("Constraint violada: organizações devem ser distintas.")

    audit_service.log_action(
        db,
        action="org_org_link_create",
        user_id=user_id,
        entity_type=_ENTITY_TYPE,
        entity_id=link.id,
        description=(
            f"Relação {relation_type!r} criada entre "
            f"org id={org_a_id} e org id={org_b_id}."
        ),
        metadata={
            "org_a_id": org_a_id,
            "org_b_id": org_b_id,
            "relation_type": relation_type,
        },
        manage_transaction=False,
    )
    db.commit()
    db.refresh(link)
    return link


def remove_link(
    db: Session, link_id: int, user_id: int
) -> Optional[OrgOrgLink]:
    """Remove relação por exclusão lógica e audita."""
    link = db.get(OrgOrgLink, link_id)
    if link is None:
        return None
    if link.active == 0:
        return link

    link.active = 0
    db.flush()

    audit_service.log_action(
        db,
        action="org_org_link_remove",
        user_id=user_id,
        entity_type=_ENTITY_TYPE,
        entity_id=link.id,
        description=(
            f"Relação {link.relation_type!r} removida entre "
            f"org id={link.org_a_id} e org id={link.org_b_id}."
        ),
        metadata={
            "org_a_id": link.org_a_id,
            "org_b_id": link.org_b_id,
            "relation_type": link.relation_type,
        },
        manage_transaction=False,
    )
    db.commit()
    db.refresh(link)
    return link


def get_link(db: Session, link_id: int) -> Optional[OrgOrgLink]:
    return db.get(OrgOrgLink, link_id)


def list_links_by_org(
    db: Session, org_id: int, *, include_removed: bool = False
) -> list[OrgOrgLink]:
    """Lista relações onde org_id aparece como org_a OU org_b (CA-006.6)."""
    from sqlalchemy import or_
    stmt = (
        select(OrgOrgLink)
        .where(
            or_(OrgOrgLink.org_a_id == org_id, OrgOrgLink.org_b_id == org_id)
        )
        .order_by(OrgOrgLink.created_at.asc())
    )
    if not include_removed:
        stmt = stmt.where(OrgOrgLink.active == 1)
    return list(db.execute(stmt).scalars().all())