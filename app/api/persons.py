"""
CIRCE Intel Desk — Endpoints REST de Pessoas (RF-002).

Camada fina de HTTP sobre o person_service. Nenhuma regra de domínio vive
aqui: validação é dos schemas Pydantic, regra e auditoria são do serviço.
Espelha app/api/cases.py (Bloco 8.3).

Autenticação: estas rotas NÃO estão na allowlist pública do auth_guard
(app/web/middleware.py), portanto são protegidas por padrão (RF-021). O
middleware popula request.state.user_id no caminho autenticado (D30); os
endpoints leem dali quem é o operador, sem reconsultar o banco.

Tratamento de CPF duplicado (CA-002.5, decisão D57): create_person e
update_person podem levantar DuplicateCPFError. Aqui ela vira HTTP 409
Conflict, com o id e nome da pessoa já cadastrada no corpo, para a UI
oferecer "abrir pessoa existente" em vez de um erro genérico. Como o
FastAPI envelopa o `detail` de HTTPException sob a chave "detail", o
corpo de resposta fica:
  {"detail": {"error": "cpf_duplicado", "message": "...",
              "existing_person_id": N, "existing_person_name": "..."}}

Verbos:
  GET    /api/persons        -> lista (filtro de arquivados + ordenação)
  POST   /api/persons        -> cria (409 se CPF duplicado)
  GET    /api/persons/{id}   -> detalhe
  PATCH  /api/persons/{id}   -> edita (409 se CPF duplicado)
  DELETE /api/persons/{id}   -> arquiva (exclusão LÓGICA, nunca física)

Sprint 01 — Bloco 9, Sub-passo 9.4.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.schemas.persons import PersonCreate, PersonResponse, PersonUpdate
from app.services import person_service
from app.services.person_service import DuplicateCPFError

router = APIRouter(prefix="/api/persons", tags=["persons"])


def _current_user_id(request: Request) -> int:
    """Lê o operador autenticado de request.state (populado pelo middleware, D30).

    Duplicado de app/api/cases.py::_current_user_id por enquanto — mesma
    lógica, dois módulos. Candidato a extração para um helper comum quando
    um terceiro módulo de API precisar dele (mesmo critério já usado para
    formatDate/statusBadge no frontend, Bloco 8.6).
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operador não autenticado.",
        )
    return user_id


def _duplicate_cpf_response(exc: DuplicateCPFError) -> HTTPException:
    """Converte DuplicateCPFError em HTTP 409 estruturado (CA-002.5 / D57)."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "cpf_duplicado",
            "message": "CPF já cadastrado para outra pessoa.",
            "existing_person_id": exc.existing_person_id,
            "existing_person_name": exc.existing_person_name,
        },
    )


@router.get("", response_model=list[PersonResponse])
def list_persons(
    request: Request,
    include_archived: bool = False,
    sort_by: Literal["full_name", "created_at", "status"] = "created_at",
    descending: bool = True,
    db: Session = Depends(get_session),
) -> list[PersonResponse]:
    """Lista pessoas (CA-002.4 filtro de arquivadas + ordenação)."""
    _current_user_id(request)  # exige autenticação; listagem não audita (RF-002)
    persons = person_service.list_persons(
        db,
        include_archived=include_archived,
        sort_by=sort_by,
        descending=descending,
    )
    return persons


@router.post("", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_person(
    request: Request,
    data: PersonCreate,
    db: Session = Depends(get_session),
) -> PersonResponse:
    """Cria uma pessoa (CA-002.1 nome via schema; CA-002.2 CPF normalizado;
    CA-002.5 rejeita CPF duplicado com 409; CA-002.7 audita)."""
    user_id = _current_user_id(request)
    try:
        person = person_service.create_person(db, data, user_id=user_id)
    except DuplicateCPFError as exc:
        raise _duplicate_cpf_response(exc) from exc
    return person


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(
    request: Request,
    person_id: int,
    db: Session = Depends(get_session),
) -> PersonResponse:
    """Detalhe de uma pessoa. 404 se não existir."""
    _current_user_id(request)
    person = person_service.get_person(db, person_id)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pessoa {person_id} não encontrada.",
        )
    return person


@router.patch("/{person_id}", response_model=PersonResponse)
def update_person(
    request: Request,
    person_id: int,
    data: PersonUpdate,
    db: Session = Depends(get_session),
) -> PersonResponse:
    """Edita uma pessoa (CA-002.6; CA-002.5 rejeita CPF duplicado com 409;
    CA-002.7 audita). 404 se não existir."""
    user_id = _current_user_id(request)
    try:
        person = person_service.update_person(db, person_id, data, user_id=user_id)
    except DuplicateCPFError as exc:
        raise _duplicate_cpf_response(exc) from exc
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pessoa {person_id} não encontrada.",
        )
    return person


@router.delete("/{person_id}", response_model=PersonResponse)
def archive_person(
    request: Request,
    person_id: int,
    db: Session = Depends(get_session),
) -> PersonResponse:
    """Arquiva uma pessoa — exclusão LÓGICA, nunca física (CA-002.7 audita).

    DELETE aqui significa 'arquivar' (status='archived'), preservando o
    registro. A pessoa desaparece da lista padrão e reaparece com
    include_archived=true. 404 se não existir.
    """
    user_id = _current_user_id(request)
    person = person_service.archive_person(db, person_id, user_id=user_id)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pessoa {person_id} não encontrada.",
        )
    return person
