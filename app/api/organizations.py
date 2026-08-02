"""
CIRCE Intel Desk — API REST de Organizações Criminosas (RF-004).

Endpoints:
  GET    /api/organizations          — lista organizações
  POST   /api/organizations          — cria organização
  GET    /api/organizations/{id}     — detalhe
  PATCH  /api/organizations/{id}     — edita
  DELETE /api/organizations/{id}     — arquiva (lógico)

Sprint 01-B — Sub-passo B3.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.schemas.organizations import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)
from app.services.organization_service import (
    create_organization,
    update_organization,
    archive_organization,
    get_organization,
    list_organizations,
    OrganizationNotFoundError,
)

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationResponse])
def api_list_organizations(
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="name"),
    descending: bool = Query(default=False),
    db: Session = Depends(get_session),
):
    return list_organizations(
        db,
        include_archived=include_archived,
        sort_by=sort_by,
        descending=descending,
    )


@router.post("", response_model=OrganizationResponse, status_code=201)
def api_create_organization(
    payload: OrganizationCreate,
    request_state=Depends(lambda: None),
    db: Session = Depends(get_session),
    # user_id injetado via request.state pelo middleware
):
    from fastapi import Request
    return create_organization(
        db,
        name=payload.name,
        siglas=payload.siglas,
        alcunhas=payload.alcunhas,
        org_type=payload.org_type,
        area_atuacao=payload.area_atuacao,
        source=payload.source,
        reliability_level=payload.reliability_level,
        notes=payload.notes,
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
def api_get_organization(org_id: int, db: Session = Depends(get_session)):
    org = get_organization(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organização não encontrada.")
    return org


@router.patch("/{org_id}", response_model=OrganizationResponse)
def api_update_organization(
    org_id: int,
    payload: OrganizationUpdate,
    db: Session = Depends(get_session),
):
    try:
        return update_organization(
            db,
            org_id,
            **payload.model_dump(exclude_none=True),
        )
    except OrganizationNotFoundError:
        raise HTTPException(status_code=404, detail="Organização não encontrada.")


@router.delete("/{org_id}", status_code=204)
def api_archive_organization(org_id: int, db: Session = Depends(get_session)):
    try:
        archive_organization(db, org_id)
    except OrganizationNotFoundError:
        raise HTTPException(status_code=404, detail="Organização não encontrada.")