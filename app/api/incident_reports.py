"""
CIRCE Intel Desk — Endpoints REST de Boletins de Ocorrência (RF-009).

Camada fina de HTTP sobre o incident_report_service.

Verbos:
  GET    /api/incident_reports                          -> lista (filtro case_id + archived)
  POST   /api/incident_reports                          -> cria BO
  GET    /api/incident_reports/{id}                     -> detalhe
  PATCH  /api/incident_reports/{id}                     -> edita
  DELETE /api/incident_reports/{id}                     -> arquiva (exclusão lógica)

  GET    /api/cases/{case_id}/incident_reports          -> lista BOs de um caso (CA-009.5)

  POST   /api/incident_reports/{id}/persons             -> vincula pessoa ao BO (CA-009.3)
  DELETE /api/incident_reports/{id}/persons/{link_id}   -> remove vínculo

Sprint 03 — Sub-passo 03-3.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.schemas.incident_report import (
    IncidentReportCreate,
    IncidentReportRead,
    IncidentReportUpdate,
)
from app.services import incident_report_service
from app.services.incident_report_service import (
    DuplicateIRPersonLinkError,
    IncidentReportNotFoundError,
)

router = APIRouter(tags=["incident_reports"])
router_cases = APIRouter(tags=["incident_reports"])  # montado sob /api/cases


def _current_user_id(request: Request) -> int:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operador não autenticado.",
        )
    return user_id


# ---------------------------------------------------------------------------
# CRUD principal
# ---------------------------------------------------------------------------

@router.get("/api/incident_reports", response_model=list[IncidentReportRead])
def list_incident_reports(
    request: Request,
    case_id: int | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_session),
):
    """Lista BOs com filtro opcional por caso."""
    _current_user_id(request)
    return incident_report_service.list_incident_reports(
        db, case_id=case_id, include_archived=include_archived
    )


@router.post(
    "/api/incident_reports",
    response_model=IncidentReportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_incident_report(
    request: Request,
    data: IncidentReportCreate,
    db: Session = Depends(get_session),
):
    """Cria um BO (CA-009.1, CA-009.2)."""
    user_id = _current_user_id(request)
    return incident_report_service.create_incident_report(db, data, user_id=user_id)


@router.get("/api/incident_reports/{report_id}", response_model=IncidentReportRead)
def get_incident_report(
    request: Request,
    report_id: int,
    db: Session = Depends(get_session),
):
    """Retorna detalhe de um BO."""
    _current_user_id(request)
    report = incident_report_service.get_incident_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="BO não encontrado.")
    return report


@router.patch("/api/incident_reports/{report_id}", response_model=IncidentReportRead)
def update_incident_report(
    request: Request,
    report_id: int,
    data: IncidentReportUpdate,
    db: Session = Depends(get_session),
):
    """Edita campos de um BO."""
    user_id = _current_user_id(request)
    try:
        return incident_report_service.update_incident_report(
            db, report_id, data, user_id=user_id
        )
    except IncidentReportNotFoundError:
        raise HTTPException(status_code=404, detail="BO não encontrado.")


@router.delete("/api/incident_reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_incident_report(
    request: Request,
    report_id: int,
    db: Session = Depends(get_session),
):
    """Arquiva um BO (exclusão lógica)."""
    user_id = _current_user_id(request)
    try:
        incident_report_service.archive_incident_report(db, report_id, user_id=user_id)
    except IncidentReportNotFoundError:
        raise HTTPException(status_code=404, detail="BO não encontrado.")


# ---------------------------------------------------------------------------
# BOs de um caso (CA-009.5)
# ---------------------------------------------------------------------------

@router_cases.get(
    "/api/cases/{case_id}/incident_reports",
    response_model=list[IncidentReportRead],
)
def list_incident_reports_by_case(
    request: Request,
    case_id: int,
    include_archived: bool = False,
    db: Session = Depends(get_session),
):
    """Lista BOs vinculados a um caso (CA-009.5)."""
    _current_user_id(request)
    return incident_report_service.list_incident_reports(
        db, case_id=case_id, include_archived=include_archived
    )


# ---------------------------------------------------------------------------
# Vínculos BO ↔ Pessoa (CA-009.3)
# ---------------------------------------------------------------------------

class _PersonLinkPayload(IncidentReportCreate.__class__):
    pass


from pydantic import BaseModel


class PersonLinkIn(BaseModel):
    person_id: int
    role_in_report: str
    notes: str | None = None


class PersonLinkOut(BaseModel):
    id: int
    incident_report_id: int
    person_id: int
    role_in_report: str
    notes: str | None
    active: int
    created_at: str
    created_by: int | None

    model_config = {"from_attributes": True}


@router.post(
    "/api/incident_reports/{report_id}/persons",
    response_model=PersonLinkOut,
    status_code=status.HTTP_201_CREATED,
)
def link_person_to_report(
    request: Request,
    report_id: int,
    data: PersonLinkIn,
    db: Session = Depends(get_session),
):
    """Vincula pessoa a BO com papel declarado (CA-009.3)."""
    user_id = _current_user_id(request)
    try:
        return incident_report_service.link_person(
            db,
            incident_report_id=report_id,
            person_id=data.person_id,
            role_in_report=data.role_in_report,
            notes=data.notes,
            user_id=user_id,
        )
    except IncidentReportNotFoundError:
        raise HTTPException(status_code=404, detail="BO não encontrado.")
    except DuplicateIRPersonLinkError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_link",
                "existing_link_id": e.existing_link_id,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete(
    "/api/incident_reports/{report_id}/persons/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unlink_person_from_report(
    request: Request,
    report_id: int,
    link_id: int,
    db: Session = Depends(get_session),
):
    """Remove vínculo pessoa↔BO (exclusão lógica)."""
    user_id = _current_user_id(request)
    result = incident_report_service.unlink_person(db, link_id=link_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")


@router.get(
    "/api/incident_reports/{report_id}/persons",
    response_model=list[PersonLinkOut],
)
def list_persons_of_report(
    request: Request,
    report_id: int,
    include_removed: bool = False,
    db: Session = Depends(get_session),
):
    """Lista pessoas vinculadas a um BO."""
    _current_user_id(request)
    return incident_report_service.list_persons_by_report(
        db, report_id, include_removed=include_removed
    )
