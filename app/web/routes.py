"""
Rotas web (HTML) do CIRCE Intel Desk.

Todas as funções de rota recebem `workspace_id` como parâmetro,
mesmo que na Sprint 0.5 apenas o workspace 'default' seja
exposto. Isso é preparação para ADR-010 (Workspaces nomeados
por caso ativo, status: Proposed em 2026-05-03), de forma
que a promoção da ADR para Accepted nas sprints 03-05 não
exija refatoração da camada de roteamento.

Exceção a esse padrão: as rotas de autenticação (GET /setup,
GET /login, GET /lock), adicionadas no Sprint 01 / Blocos 5.6
e 6.4. Workspace é um conceito que só existe DEPOIS de
autenticado — essas telas são o portão, não um cômodo.
Decisão consciente do operador.

Páginas placeholder de domínio (Organizações, Documentos,
Relatórios) são apenas casca — implementação real de cada uma
entra na sprint correspondente do roadmap.

Bloco 6.8: helper _shell_context centraliza a montagem do
contexto comum a todas as rotas autenticadas (workspace_id,
active_page, page_title, inactivity_minutes). Centraliza a
leitura de settings_service para evitar duplicação em cada
rota e garantir que a injeção de data-inactivity-minutes no
<body> não seja esquecida em rotas futuras.

Sprint 01 / Bloco 8.4: a rota /cases foi despromovida de
placeholder para a tela funcional (cases/list.html). É a
ÚNICA mudança deste sub-passo neste arquivo.

Sprint 01 / Bloco 8.6: adicionada a rota de detalhe
GET /cases/{case_id:int} (cases/detail.html). Renderização
SPA-leve: a rota só serve o esqueleto; o conteúdo é buscado
pelo case_detail.js em GET /api/cases/{id}. O conversor :int
no path casa com case_id: int da API e faz o FastAPI rejeitar
ids não-numéricos com 422, sem colidir com /cases.

Sprint 01 / Bloco 9.5: a rota /persons foi despromovida de
placeholder para a tela funcional (persons/list.html), mesmo
movimento do 8.4. placeholders/persons.html foi removido do
repositório (ficou inerte, nenhuma rota aponta mais para ele).

Sprint 01 / Bloco 9.6: adicionada a rota de detalhe
GET /persons/{person_id:int} (persons/detail.html). Mesmo
padrão SPA-leve do Bloco 8.6: a rota serve apenas o esqueleto;
o conteúdo é buscado pelo person_detail.js em
GET /api/persons/{id}. O conversor :int no path rejeita ids
não-numéricos com 422, sem colidir com /persons. Decisão D58.

NOTA (Python 3.13 + SQLAlchemy 2.0.36):
  log_action em /lock usa manage_transaction=False — a sessão
  já tem transação implícita aberta pelo SQLAlchemy (autocommit=False).
  BEGIN IMMEDIATE dentro de transação aberta causa OperationalError
  no SQLite. Corrigido no Bloco 11.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from pathlib import Path

from app.api.auth import _operator_exists
from app.database.session import get_session
from app.services import settings_service

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["web"])


# ---------------------------------------------------------------------------
# Helper interno — contexto comum a todas as rotas autenticadas (Bloco 6.8).
# ---------------------------------------------------------------------------
def _shell_context(
    workspace_id: str,
    active_page: str | None,
    page_title: str,
) -> dict:
    return {
        "workspace_id": workspace_id,
        "active_page": active_page,
        "page_title": page_title,
        "inactivity_minutes": settings_service.get_value(
            "inactivity_lock_minutes", 0
        ),
    }


# ---------------------------------------------------------------------------
# Helper interno para renderizar páginas placeholder.
# ---------------------------------------------------------------------------
def _render_placeholder(
    request: Request,
    template_name: str,
    active_page: str,
    page_title: str,
    workspace_id: str,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=_shell_context(workspace_id, active_page, page_title),
    )


# ---------------------------------------------------------------------------
# Página raiz — shell vazio.
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def home(request: Request, workspace_id: str = "default") -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context=_shell_context(workspace_id, None, "CIRCE Intel Desk"),
    )


# ---------------------------------------------------------------------------
# Rotas de autenticação (HTML) — RF-021, Sprint 01 / Blocos 5.6 e 6.4.
# ---------------------------------------------------------------------------
@router.get("/setup", response_class=HTMLResponse)
async def setup_page(
    request: Request,
    db: Session = Depends(get_session),
):
    if _operator_exists(db):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="auth/setup.html",
        context={
            "active_page": None,
            "page_title": "CIRCE // Cadastro Inicial",
        },
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: str | None = None,
    blocked: str | None = None,
    secs: int | None = None,
    next: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "active_page": None,
            "page_title": "CIRCE // Acesso",
            "show_error": error is not None,
            "show_blocked": blocked is not None,
            "blocked_secs": secs if secs is not None else 0,
            "next_url": next or "/",
        },
    )


@router.get("/lock", response_class=HTMLResponse)
async def lock_page(
    request: Request,
    db: Session = Depends(get_session),
) -> HTMLResponse:
    """
    Tela de bloqueio (CA-021.7, CA-021.8, CA-021.9).

    log_action usa manage_transaction=False — a sessão já tem transação
    implícita aberta pelo SQLAlchemy (autocommit=False). Corrigido no Bloco 11.
    """
    from urllib.parse import quote
    from app.services.audit_service import log_action

    from_url = request.query_params.get("from", "/")
    reason = request.query_params.get("reason", "manual")
    next_qs = quote(from_url, safe="")

    action = "lock_inactivity" if reason == "auto" else "lock_manual"
    user_id = getattr(request.state, "user_id", None)

    log_action(
        db,
        action=action,
        user_id=user_id,
        description=f"Tela de bloqueio acionada (reason={reason!r}).",
        manage_transaction=False,
    )
    db.commit()

    return templates.TemplateResponse(
        request=request,
        name="auth/lock.html",
        context={
            "active_page": None,
            "page_title": "CIRCE // Bloqueado",
            "from_url": from_url,
            "next_qs": next_qs,
        },
    )


# ---------------------------------------------------------------------------
# Casos — RF-001. Sprint 01 / Bloco 8, Sub-passo 8.4.
# ---------------------------------------------------------------------------
@router.get("/cases", response_class=HTMLResponse)
async def cases_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="cases/list.html",
        context=_shell_context(workspace_id, "cases", "CIRCE // Casos"),
    )


@router.get("/cases/{case_id:int}", response_class=HTMLResponse)
async def case_detail_page(
    request: Request, case_id: int, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="cases/detail.html",
        context=_shell_context(workspace_id, "cases", "CIRCE // Detalhe do caso"),
    )


# ---------------------------------------------------------------------------
# Pessoas — RF-002. Sprint 01 / Bloco 9, Sub-passo 9.5.
# ---------------------------------------------------------------------------
@router.get("/persons", response_class=HTMLResponse)
async def persons_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="persons/list.html",
        context=_shell_context(workspace_id, "persons", "CIRCE // Pessoas"),
    )


@router.get("/persons/{person_id:int}", response_class=HTMLResponse)
async def person_detail_page(
    request: Request, person_id: int, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="persons/detail.html",
        context=_shell_context(workspace_id, "persons", "CIRCE // Detalhe da pessoa"),
    )


# ---------------------------------------------------------------------------
# Placeholders — páginas de domínio ainda não implementadas.
# ---------------------------------------------------------------------------
@router.get("/organizations", response_class=HTMLResponse)
async def organizations_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return _render_placeholder(
        request=request,
        template_name="placeholders/organizations.html",
        active_page="organizations",
        page_title="CIRCE // Organizações",
        workspace_id=workspace_id,
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return _render_placeholder(
        request=request,
        template_name="placeholders/documents.html",
        active_page="documents",
        page_title="CIRCE // Documentos",
        workspace_id=workspace_id,
    )


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return _render_placeholder(
        request=request,
        template_name="placeholders/reports.html",
        active_page="reports",
        page_title="CIRCE // Relatórios",
        workspace_id=workspace_id,
    )


# ---------------------------------------------------------------------------
# Página de desenvolvimento — showcase de componentes.
# ---------------------------------------------------------------------------
@router.get("/dev/components", response_class=HTMLResponse)
async def dev_components(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dev/components.html",
        context=_shell_context(workspace_id, None, "CIRCE // Showcase"),
    )