"""
CIRCE Intel Desk — Endpoints REST de Vínculos.

RF-003: /api/links/person-case  (Bloco 10)
RF-005: /api/links/person-org   (Sprint 01-B, B6)

Arquitetura (D-B10-04): router único /api/links com sub-prefixos por tipo.
Autenticação: protegidas pelo auth_guard (RF-021). user_id via D30.

Sprint 01 — Bloco 10, Sub-passo 10.4.
Sprint 01-B — Sub-passo B6 (RF-005 person-org).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.case import Case
from app.models.case_person_link import CasePersonLink
from app.models.organization import Organization
from app.models.person import Person
from app.models.person_org_link import PersonOrgLink
from app.schemas.links import PersonCaseLinkCreate, PersonCaseLinkResponse
from app.services import link_service
from app.services.link_service import DuplicateLinkError
from app.services import person_org_link_service
from app.services.person_org_link_service import DuplicatePersonOrgLinkError

router = APIRouter(prefix="/api/links", tags=["links"])


def _current_user_id(request: Request) -> int:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operador não autenticado.",
        )
    return user_id


# ---------------------------------------------------------------------------
# Schemas para RF-005 (person-org)
# ---------------------------------------------------------------------------

class PersonOrgLinkCreate(BaseModel):
    person_id: int
    org_id: int
    link_type: str
    source: str
    position: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    reliability_level: str = "pending"
    notes: Optional[str] = None


class PersonOrgLinkResponse(BaseModel):
    id: int
    person_id: int
    org_id: int
    link_type: str
    position: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]
    source: Optional[str]
    reliability_level: str
    notes: Optional[str]
    active: int
    created_at: str
    created_by: Optional[int]
    # Campos enriquecidos
    person_name: Optional[str] = None
    org_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enrich_links(
    db: Session,
    links: list[CasePersonLink],
) -> list[PersonCaseLinkResponse]:
    if not links:
        return []

    person_ids = {lk.person_id for lk in links}
    case_ids = {lk.case_id for lk in links}

    persons_map: dict[int, str] = {}
    rows_p = db.execute(
        select(Person.id, Person.full_name).where(Person.id.in_(person_ids))
    ).fetchall()
    for pid, pname in rows_p:
        persons_map[pid] = pname

    cases_map: dict[int, tuple[str, str]] = {}
    rows_c = db.execute(
        select(Case.id, Case.case_code, Case.name).where(Case.id.in_(case_ids))
    ).fetchall()
    for cid, ccode, cname in rows_c:
        cases_map[cid] = (ccode, cname)

    result = []
    for lk in links:
        case_code, case_name = cases_map.get(lk.case_id, (None, None))
        result.append(
            PersonCaseLinkResponse(
                id=lk.id,
                case_id=lk.case_id,
                person_id=lk.person_id,
                role_in_case=lk.role_in_case,
                source=lk.source,
                reliability_level=lk.reliability_level,
                notes=lk.notes,
                active=lk.active,
                created_at=lk.created_at,
                created_by=lk.created_by,
                person_name=persons_map.get(lk.person_id),
                case_code=case_code,
                case_name=case_name,
            )
        )
    return result


def _enrich_person_org_links(
    db: Session,
    links: list[PersonOrgLink],
) -> list[PersonOrgLinkResponse]:
    if not links:
        return []

    person_ids = {lk.person_id for lk in links}
    org_ids = {lk.org_id for lk in links}

    persons_map: dict[int, str] = {}
    for pid, pname in db.execute(
        select(Person.id, Person.full_name).where(Person.id.in_(person_ids))
    ).fetchall():
        persons_map[pid] = pname

    orgs_map: dict[int, str] = {}
    for oid, oname in db.execute(
        select(Organization.id, Organization.name).where(Organization.id.in_(org_ids))
    ).fetchall():
        orgs_map[oid] = oname

    result = []
    for lk in links:
        result.append(PersonOrgLinkResponse(
            id=lk.id,
            person_id=lk.person_id,
            org_id=lk.org_id,
            link_type=lk.link_type,
            position=lk.position,
            period_start=lk.period_start,
            period_end=lk.period_end,
            source=lk.source,
            reliability_level=lk.reliability_level,
            notes=lk.notes,
            active=lk.active,
            created_at=lk.created_at,
            created_by=lk.created_by,
            person_name=persons_map.get(lk.person_id),
            org_name=orgs_map.get(lk.org_id),
        ))
    return result


# ---------------------------------------------------------------------------
# Vínculo Pessoa ↔ Caso (RF-003)
# ---------------------------------------------------------------------------

@router.get("/person-case", response_model=list[PersonCaseLinkResponse])
def list_person_case_links(
    request: Request,
    case_id: Optional[int] = None,
    person_id: Optional[int] = None,
    db: Session = Depends(get_session),
) -> list[PersonCaseLinkResponse]:
    _current_user_id(request)
    if case_id is None and person_id is None:
        raise HTTPException(status_code=400, detail="Informe case_id ou person_id.")
    if case_id is not None and person_id is not None:
        raise HTTPException(status_code=400, detail="Informe apenas case_id OU person_id.")
    if case_id is not None:
        links = link_service.list_links_by_case(db, case_id)
    else:
        links = link_service.list_links_by_person(db, person_id)  # type: ignore
    return _enrich_links(db, links)


@router.post("/person-case", response_model=PersonCaseLinkResponse, status_code=201)
def create_person_case_link(
    request: Request,
    data: PersonCaseLinkCreate,
    db: Session = Depends(get_session),
) -> PersonCaseLinkResponse:
    user_id = _current_user_id(request)
    caso = db.get(Case, data.case_id)
    if caso is None:
        raise HTTPException(status_code=404, detail=f"Caso {data.case_id} não encontrado.")
    pessoa = db.get(Person, data.person_id)
    if pessoa is None:
        raise HTTPException(status_code=404, detail=f"Pessoa {data.person_id} não encontrada.")
    try:
        link = link_service.create_link(
            db, case_id=data.case_id, person_id=data.person_id,
            role_in_case=data.role_in_case, source=data.source,
            user_id=user_id, reliability_level=data.reliability_level, notes=data.notes,
        )
    except DuplicateLinkError as exc:
        raise HTTPException(status_code=409, detail={
            "error": "vinculo_duplicado",
            "message": f"Já existe vínculo ativo com o papel {exc.role_in_case!r} entre esta pessoa e este caso.",
            "existing_link_id": exc.existing_link_id,
        }) from exc
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"error": "vinculo_duplicado", "message": "Vínculo duplicado."})
    return _enrich_links(db, [link])[0]


@router.delete("/person-case/{link_id}", response_model=PersonCaseLinkResponse)
def remove_person_case_link(
    request: Request, link_id: int, db: Session = Depends(get_session),
) -> PersonCaseLinkResponse:
    user_id = _current_user_id(request)
    link = link_service.remove_link(db, link_id=link_id, user_id=user_id)
    if link is None:
        raise HTTPException(status_code=404, detail=f"Vínculo {link_id} não encontrado.")
    return _enrich_links(db, [link])[0]


# ---------------------------------------------------------------------------
# Vínculo Pessoa ↔ Organização (RF-005) — Sprint 01-B, B6
# ---------------------------------------------------------------------------

@router.get("/person-org", response_model=list[PersonOrgLinkResponse])
def list_person_org_links(
    request: Request,
    org_id: Optional[int] = None,
    person_id: Optional[int] = None,
    db: Session = Depends(get_session),
) -> list[PersonOrgLinkResponse]:
    """Lista vínculos ativos — filtrado por organização OU por pessoa."""
    _current_user_id(request)
    if org_id is None and person_id is None:
        raise HTTPException(status_code=400, detail="Informe org_id ou person_id.")
    if org_id is not None and person_id is not None:
        raise HTTPException(status_code=400, detail="Informe apenas org_id OU person_id.")
    if org_id is not None:
        links = person_org_link_service.list_links_by_org(db, org_id)
    else:
        links = person_org_link_service.list_links_by_person(db, person_id)  # type: ignore
    return _enrich_person_org_links(db, links)


@router.post("/person-org", response_model=PersonOrgLinkResponse, status_code=201)
def create_person_org_link(
    request: Request,
    data: PersonOrgLinkCreate,
    db: Session = Depends(get_session),
) -> PersonOrgLinkResponse:
    """Cria vínculo pessoa↔organização (CA-005.3–CA-005.9)."""
    user_id = _current_user_id(request)
    org = db.get(Organization, data.org_id)
    if org is None:
        raise HTTPException(status_code=404, detail=f"Organização {data.org_id} não encontrada.")
    pessoa = db.get(Person, data.person_id)
    if pessoa is None:
        raise HTTPException(status_code=404, detail=f"Pessoa {data.person_id} não encontrada.")
    try:
        link = person_org_link_service.create_link(
            db, person_id=data.person_id, org_id=data.org_id,
            link_type=data.link_type, source=data.source, user_id=user_id,
            position=data.position, period_start=data.period_start,
            period_end=data.period_end, reliability_level=data.reliability_level,
            notes=data.notes,
        )
    except DuplicatePersonOrgLinkError as exc:
        raise HTTPException(status_code=409, detail={
            "error": "vinculo_duplicado",
            "message": f"Já existe vínculo ativo com o tipo {exc.link_type!r} entre esta pessoa e esta organização.",
            "existing_link_id": exc.existing_link_id,
        }) from exc
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"error": "vinculo_duplicado", "message": "Vínculo duplicado."})
    return _enrich_person_org_links(db, [link])[0]


@router.delete("/person-org/{link_id}", response_model=PersonOrgLinkResponse)
def remove_person_org_link(
    request: Request, link_id: int, db: Session = Depends(get_session),
) -> PersonOrgLinkResponse:
    """Remove vínculo pessoa↔organização por exclusão lógica."""
    user_id = _current_user_id(request)
    link = person_org_link_service.remove_link(db, link_id=link_id, user_id=user_id)
    if link is None:
        raise HTTPException(status_code=404, detail=f"Vínculo {link_id} não encontrado.")
    return _enrich_person_org_links(db, [link])[0]