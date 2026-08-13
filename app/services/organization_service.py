"""
CIRCE Intel Desk — Serviço de Organizações Criminosas (RF-004).

Operações: create, update, archive, get, list.
Auditoria atômica conforme ADR-003a e D47:
  BEGIN IMMEDIATE (implícito pelo SQLAlchemy) → add/flush →
  search_service.index_organization (FTS5, Sprint 03-0) →
  log_action(manage_transaction=False) → commit().

NOTA (D-03-0-01): este serviço não implementa BEGIN IMMEDIATE explícito
nem try/except/rollback — dívida técnica pré-existente ao Sprint 03-0.
Registrado para sprint de hardening futura. Não corrigido aqui para
manter escopo cirúrgico do 03-0.

Sprint 01-B — Sub-passo B2.
Sprint 03 — Sub-passo 03-0: integração FTS5 (index_organization).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.audit_service import log_action
from app.services import search_service


# ---------------------------------------------------------------------------
# Exceções de domínio
# ---------------------------------------------------------------------------

class OrganizationNotFoundError(Exception):
    """Organização não encontrada pelo id informado."""


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


# ---------------------------------------------------------------------------
# Operações públicas
# ---------------------------------------------------------------------------

def create_organization(
    db: Session,
    *,
    name: str,
    siglas: Optional[str] = None,
    alcunhas: Optional[str] = None,
    org_type: Optional[str] = None,
    area_atuacao: Optional[str] = None,
    source: Optional[str] = None,
    reliability_level: str = "pending",
    notes: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Organization:
    """Cria uma organização criminosa e loga o evento."""
    if not name or not name.strip():
        raise ValueError("name não pode ser vazio.")

    now = _now()
    org = Organization(
        name=name.strip(),
        siglas=siglas,
        alcunhas=alcunhas,
        org_type=org_type,
        area_atuacao=area_atuacao,
        source=source,
        reliability_level=reliability_level,
        notes=notes,
        status="active",
        created_at=now,
        created_by=created_by,
        updated_at=now,
        updated_by=created_by,
    )
    db.add(org)
    db.flush()

    search_service.index_organization(db, org)  # Sprint 03-0: mantém FTS5 sincronizado

    log_action(
        db,
        action="org_create",
        user_id=created_by,
        entity_type="organization",
        entity_id=org.id,
        description=f"Organização '{org.name}' cadastrada.",
        manage_transaction=False,
    )
    db.commit()
    return org


def update_organization(
    db: Session,
    org_id: int,
    *,
    updated_by: Optional[int] = None,
    **fields: Any,
) -> Organization:
    """Atualiza campos de uma organização. Não loga se nada mudou."""
    org = db.get(Organization, org_id)
    if org is None:
        raise OrganizationNotFoundError(org_id)

    updatable = {
        "name", "siglas", "alcunhas", "org_type",
        "area_atuacao", "source", "reliability_level", "notes",
    }
    changed = {}
    for key, value in fields.items():
        if key not in updatable:
            continue
        if getattr(org, key) != value:
            changed[key] = value

    if not changed:
        return org

    for key, value in changed.items():
        setattr(org, key, value)
    org.updated_at = _now()
    org.updated_by = updated_by
    db.flush()

    search_service.index_organization(db, org)  # Sprint 03-0: mantém FTS5 sincronizado

    log_action(
        db,
        action="org_update",
        user_id=updated_by,
        entity_type="organization",
        entity_id=org.id,
        description=f"Organização '{org.name}' atualizada.",
        metadata={"changed_fields": list(changed.keys())},
        manage_transaction=False,
    )
    db.commit()
    return org


def archive_organization(
    db: Session,
    org_id: int,
    *,
    updated_by: Optional[int] = None,
) -> Organization:
    """Arquivamento lógico. Idempotente — não loga se já arquivada."""
    org = db.get(Organization, org_id)
    if org is None:
        raise OrganizationNotFoundError(org_id)

    if org.status == "archived":
        return org

    org.status = "archived"
    org.updated_at = _now()
    org.updated_by = updated_by
    db.flush()

    search_service.index_organization(db, org)  # Sprint 03-0: remove do FTS5 (status=archived)

    log_action(
        db,
        action="org_archive",
        user_id=updated_by,
        entity_type="organization",
        entity_id=org.id,
        description=f"Organização '{org.name}' arquivada.",
        manage_transaction=False,
    )
    db.commit()
    return org


def get_organization(db: Session, org_id: int) -> Optional[Organization]:
    """Retorna organização por id ou None."""
    return db.get(Organization, org_id)


def list_organizations(
    db: Session,
    *,
    include_archived: bool = False,
    sort_by: str = "name",
    descending: bool = False,
) -> list[Organization]:
    """Lista organizações com filtro e ordenação."""
    stmt = select(Organization)
    if not include_archived:
        stmt = stmt.where(Organization.status == "active")

    col = getattr(Organization, sort_by, Organization.name)
    stmt = stmt.order_by(col.desc() if descending else col.asc())
    return list(db.execute(stmt).scalars().all())
