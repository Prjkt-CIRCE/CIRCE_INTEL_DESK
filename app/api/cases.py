"""
CIRCE Intel Desk — Endpoints REST de Casos (RF-001).

Camada fina de HTTP sobre o case_service. Nenhuma regra de domínio vive
aqui: validação é dos schemas Pydantic, regra e auditoria são do serviço.

Autenticação: estas rotas NÃO estão na allowlist pública do auth_guard
(app/web/middleware.py), portanto são protegidas por padrão (RF-021). O
middleware popula request.state.user_id no caminho autenticado (D30); os
endpoints leem dali quem é o operador, sem reconsultar o banco.

Verbos:
  GET    /api/cases        -> lista (filtro de arquivados + ordenação)
  POST   /api/cases        -> cria
  GET    /api/cases/{id}   -> detalhe
  PATCH  /api/cases/{id}   -> edita
  DELETE /api/cases/{id}   -> arquiva (exclusão LÓGICA, nunca física)

Sprint 01 — Bloco 8, Sub-passo 8.3.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.schemas.cases import CaseCreate, CaseResponse, CaseUpdate
from app.services import case_service

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _current_user_id(request: Request) -> int:
    """Lê o operador autenticado de request.state (populado pelo middleware, D30).

    Se o middleware deixou passar, user_id existe. A checagem defensiva aqui
    cobre o caso de a rota ser chamada fora do fluxo normal (ex.: teste sem
    middleware) — falha explícita é melhor que AttributeError silencioso.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operador não autenticado.",
        )
    return user_id


@router.get("", response_model=list[CaseResponse])
def list_cases(
    request: Request,
    include_archived: bool = False,
    sort_by: Literal["case_code", "name", "created_at", "status"] = "created_at",
    descending: bool = True,
    db: Session = Depends(get_session),
) -> list[CaseResponse]:
    """Lista casos (CA-001.5 filtro de arquivados; CA-001.7 ordenação)."""
    _current_user_id(request)  # exige autenticação; listagem não audita (RF-001)
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
    """Cria um caso (CA-001.1 código gerado; CA-001.3 nome via schema; CA-001.6 audita)."""
    user_id = _current_user_id(request)
    case = case_service.create_case(db, data, user_id=user_id)
    return case


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> CaseResponse:
    """Detalhe de um caso. 404 se não existir."""
    _current_user_id(request)
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} não encontrado.",
        )
    return case


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    request: Request,
    case_id: int,
    data: CaseUpdate,
    db: Session = Depends(get_session),
) -> CaseResponse:
    """Edita um caso (CA-001.4; CA-001.6 audita). 404 se não existir."""
    user_id = _current_user_id(request)
    case = case_service.update_case(db, case_id, data, user_id=user_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} não encontrado.",
        )
    return case


@router.delete("/{case_id}", response_model=CaseResponse)
def archive_case(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> CaseResponse:
    """Arquiva um caso — exclusão LÓGICA, nunca física (CA-001.5; CA-001.6 audita).

    DELETE aqui significa 'arquivar' (status='archived'), preservando o
    registro. O caso desaparece da lista padrão e reaparece com
    include_archived=true. 404 se não existir.
    """
    user_id = _current_user_id(request)
    case = case_service.archive_case(db, case_id, user_id=user_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} não encontrado.",
        )
    return case
