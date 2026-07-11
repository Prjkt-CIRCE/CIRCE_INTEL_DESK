"""
CIRCE Intel Desk — Endpoints REST de Vínculos (RF-003, e futuros RF-005/006).

Camada fina de HTTP sobre o link_service. Nenhuma regra de domínio vive
aqui: validação é dos schemas Pydantic, regra e auditoria são do serviço.

Arquitetura (D-B10-04): um único router /api/links com sub-prefixos por
tipo de vínculo. Hoje só /person-case; RF-005 (pessoa↔organização) e
RF-006 (organização↔organização) adicionam sub-rotas neste mesmo arquivo.

Enriquecimento de resposta (D-B10-03): os endpoints de listagem devolvem
PersonCaseLinkResponse com person_name + case_code + case_name, resolvidos
via join SQLAlchemy no próprio endpoint (camada de API, não de serviço —
o join é exclusivamente para apresentação, sem regra de domínio). Isso
evita roundtrip adicional da UI para resolver nomes.

Seleção de entidade no modal (D-B10-01): os endpoints de listagem de
pessoas (/api/persons) e casos (/api/cases) já existem e são usados pelo
modal de criação de vínculo via <select> no MVP-0. Quando RF-010 (busca
universal) entregar endpoint de busca textual, o modal migra para
typeahead — sem mudança no backend de vínculos.

Autenticação: estas rotas NÃO estão na allowlist pública do auth_guard,
portanto são protegidas por padrão (RF-021). O middleware popula
request.state.user_id (D30).

Verbos:
  GET    /api/links/person-case?case_id=N   -> vínculos ativos do caso
  GET    /api/links/person-case?person_id=N -> vínculos ativos da pessoa
  POST   /api/links/person-case             -> cria vínculo (409 se dup.)
  DELETE /api/links/person-case/{link_id}   -> remove (exclusão lógica)

Sprint 01 — Bloco 10, Sub-passo 10.4.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.case import Case
from app.models.case_person_link import CasePersonLink
from app.models.person import Person
from app.schemas.links import PersonCaseLinkCreate, PersonCaseLinkResponse
from app.services import link_service
from app.services.link_service import DuplicateLinkError

router = APIRouter(prefix="/api/links", tags=["links"])


def _current_user_id(request: Request) -> int:
    """Lê o operador autenticado de request.state (populado pelo middleware, D30).

    Terceiro módulo de API a duplicar este helper — candidato a extração
    para app/api/_auth.py quando um quarto módulo precisar (mesmo critério
    documentado em app/api/persons.py).
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operador não autenticado.",
        )
    return user_id


def _enrich_links(
    db: Session,
    links: list[CasePersonLink],
) -> list[PersonCaseLinkResponse]:
    """Enriquece lista de vínculos com person_name, case_code e case_name (D-B10-03).

    Busca os nomes em lote (um SELECT por tipo de entidade, não N+1) e
    monta os dicts para PersonCaseLinkResponse.
    """
    if not links:
        return []

    # Coleta ids únicos para fazer buscas em lote
    person_ids = {lk.person_id for lk in links}
    case_ids = {lk.case_id for lk in links}

    # Busca pessoas em lote
    persons_map: dict[int, str] = {}
    rows_p = db.execute(
        select(Person.id, Person.full_name).where(Person.id.in_(person_ids))
    ).fetchall()
    for pid, pname in rows_p:
        persons_map[pid] = pname

    # Busca casos em lote
    cases_map: dict[int, tuple[str, str]] = {}  # id -> (case_code, name)
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
    """Lista vínculos ativos — filtrado por caso OU por pessoa.

    Exige exatamente um dos dois parâmetros: case_id ou person_id.
    Ambos ausentes ou ambos presentes → 400.
    """
    _current_user_id(request)

    if case_id is None and person_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe case_id ou person_id para filtrar os vínculos.",
        )
    if case_id is not None and person_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe apenas case_id OU person_id, não os dois.",
        )

    if case_id is not None:
        links = link_service.list_links_by_case(db, case_id)
    else:
        links = link_service.list_links_by_person(db, person_id)  # type: ignore[arg-type]

    return _enrich_links(db, links)


@router.post(
    "/person-case",
    response_model=PersonCaseLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_person_case_link(
    request: Request,
    data: PersonCaseLinkCreate,
    db: Session = Depends(get_session),
) -> PersonCaseLinkResponse:
    """Cria vínculo pessoa↔caso (CA-003.3–CA-003.6, CA-003.8).

    409 se já existe vínculo ativo com o mesmo case_id + person_id +
    role_in_case (CA-003.6 / DuplicateLinkError).
    404 se caso ou pessoa não existirem.
    """
    user_id = _current_user_id(request)

    # Valida existência de caso e pessoa antes de tentar criar o vínculo,
    # para devolver 404 semântico em vez de IntegrityError de FK.
    caso = db.get(Case, data.case_id)
    if caso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {data.case_id} não encontrado.",
        )
    pessoa = db.get(Person, data.person_id)
    if pessoa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pessoa {data.person_id} não encontrada.",
        )

    try:
        link = link_service.create_link(
            db,
            case_id=data.case_id,
            person_id=data.person_id,
            role_in_case=data.role_in_case,
            source=data.source,
            user_id=user_id,
            reliability_level=data.reliability_level,
            notes=data.notes,
        )
    except DuplicateLinkError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "vinculo_duplicado",
                "message": (
                    f"Já existe vínculo ativo com o papel "
                    f"{exc.role_in_case!r} entre esta pessoa e este caso."
                ),
                "existing_link_id": exc.existing_link_id,
            },
        ) from exc
    except IntegrityError:
        # Segunda linha de defesa (D-B10-02): a constraint UNIQUE do banco
        # bloqueia inserção mesmo com active=0 no registro anterior.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "vinculo_duplicado",
                "message": (
                    f"Já existe um registro com o papel {data.role_in_case!r} "
                    f"entre esta pessoa e este caso (incluindo vínculos removidos). "
                    f"Não é possível recriar o mesmo vínculo no MVP-0."
                ),
            },
        )

    return _enrich_links(db, [link])[0]


@router.delete(
    "/person-case/{link_id}",
    response_model=PersonCaseLinkResponse,
)
def remove_person_case_link(
    request: Request,
    link_id: int,
    db: Session = Depends(get_session),
) -> PersonCaseLinkResponse:
    """Remove vínculo por exclusão lógica (active=0) (CA-003.7, CA-003.8).

    404 se o vínculo não existir.
    Idempotente via serviço: remover já-removido retorna o registro sem
    novo log — mas aqui retornamos 404 se o vínculo não existir de forma
    alguma (nunca criado vs. criado-e-removido são casos distintos do
    ponto de vista da API).
    """
    user_id = _current_user_id(request)
    link = link_service.remove_link(db, link_id=link_id, user_id=user_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vínculo {link_id} não encontrado.",
        )
    return _enrich_links(db, [link])[0]
