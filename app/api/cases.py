"""
CIRCE Intel Desk - Endpoints REST de Casos (RF-001).

Camada fina de HTTP sobre o case_service. Nenhuma regra de dominio vive
aqui: validacao e dos schemas Pydantic, regra e auditoria sao do servico.

Autenticacao: estas rotas NAO estao na allowlist publica do auth_guard
(app/web/middleware.py), portanto sao protegidas por padrao (RF-021). O
middleware popula request.state.user_id no caminho autenticado (D30); os
endpoints leem dali quem e o operador, sem reconsultar o banco.

Verbos:
  GET    /api/cases                                          -> lista
  POST   /api/cases                                         -> cria
  GET    /api/cases/{id}                                    -> detalhe
  PATCH  /api/cases/{id}                                    -> edita
  DELETE /api/cases/{id}                                    -> arquiva (logico)
  PATCH  /api/cases/{id}/items/{item_type}/{item_id}/platea_exclude
                                                            -> toggle [NAO COMPARTILHAR] (AT-03.7)

Sprint 01 - Bloco 8, Sub-passo 8.3.
AT-03.7: endpoint platea_exclude adicionado.
AT-03.8: update_case passa username ao servico para published_by no Athena.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.user import User
from app.schemas.cases import CaseCreate, CaseResponse, CaseUpdate
from app.services import case_service
from app.services import platea_service

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _current_user_id(request: Request) -> int:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operador nao autenticado.",
        )
    return user_id


def _get_username(db: Session, user_id: int) -> Optional[str]:
    """Retorna o username do operador logado, ou None se nao encontrado.

    Usado para popular published_by no payload do Athena (AT-03.8).
    Leitura pura — nao audita, nao abre transacao imediata.
    """
    user = db.get(User, user_id)
    return user.username if user else None


class PlateaExcludeBody(BaseModel):
    exclude: bool


class PlateaExcludeResponse(BaseModel):
    item_type: str
    item_id: int
    platea_exclude: bool
    changed: bool


@router.get("", response_model=list[CaseResponse])
def list_cases(
    request: Request,
    include_archived: bool = False,
    sort_by: Literal["case_code", "name", "created_at", "status"] = "created_at",
    descending: bool = True,
    db: Session = Depends(get_session),
) -> list[CaseResponse]:
    _current_user_id(request)
    cases = case_service.list_cases(
        db,
        include_archived=include_archived,
        sort_by=sort_by,
        descending=descending,
    )
    return cases


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    request: Request,
    data: CaseCreate,
    db: Session = Depends(get_session),
) -> CaseResponse:
    user_id = _current_user_id(request)
    case = case_service.create_case(db, data, user_id=user_id)
    return case


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> CaseResponse:
    _current_user_id(request)
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )
    return case


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    request: Request,
    case_id: int,
    data: CaseUpdate,
    db: Session = Depends(get_session),
) -> CaseResponse:
    user_id = _current_user_id(request)
    # AT-03.8: busca username para published_by no payload do Athena.
    username = _get_username(db, user_id)
    case = case_service.update_case(
        db, case_id, data, user_id=user_id, username=username
    )
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )
    return case


@router.delete("/{case_id}", response_model=CaseResponse)
def archive_case(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> CaseResponse:
    user_id = _current_user_id(request)
    case = case_service.archive_case(db, case_id, user_id=user_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )
    return case


@router.patch(
    "/{case_id}/items/{item_type}/{item_id}/platea_exclude",
    response_model=PlateaExcludeResponse,
)
def set_platea_exclude(
    request: Request,
    case_id: int,
    item_type: Literal["person_link", "document"],
    item_id: int,
    data: PlateaExcludeBody,
    db: Session = Depends(get_session),
) -> PlateaExcludeResponse:
    """
    Marca ou desmarca item individual como [NAO COMPARTILHAR] na Platea (AT-03.7).

    item_type: "person_link" | "document"
    item_id:   id do CasePersonLink ou Document
    body:      {"exclude": true|false}
    """
    user_id = _current_user_id(request)

    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )

    try:
        result = platea_service.toggle_platea_exclude(
            db,
            item_type=item_type,
            item_id=item_id,
            exclude=data.exclude,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return PlateaExcludeResponse(**result)
