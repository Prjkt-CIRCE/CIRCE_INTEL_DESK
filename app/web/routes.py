"""
Rotas web (HTML) do CIRCE Intel Desk.

Todas as funções de rota recebem `workspace_id` como parâmetro,
mesmo que na Sprint 0.5 apenas o workspace 'default' seja
exposto. Isso é preparação para ADR-010 (Workspaces nomeados
por caso ativo, status: Proposed em 2026-05-03), de forma
que a promoção da ADR para Accepted nas sprints 03–05 não
exija refatoração da camada de roteamento.

Exceção a esse padrão: as rotas de autenticação (GET /setup e
GET /login), adicionadas no Sprint 01 / Bloco 5.6. Workspace é
um conceito que só existe DEPOIS de autenticado — essas telas
são o portão, não um cômodo. Decisão consciente do operador.

Páginas placeholder de domínio (Casos, Pessoas, Organizações,
Documentos, Relatórios) são apenas casca — implementação real
de cada uma entra na sprint correspondente do roadmap.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from pathlib import Path

from app.api.auth import _operator_exists
from app.database.session import get_session

# Diretório de templates relativo a este arquivo:
# app/web/routes.py -> app/web/templates/
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["web"])


# ---------------------------------------------------------------------------
# Helper interno para renderizar páginas placeholder.
# Reduz repetição entre as 5 rotas placeholder.
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
        context={
            "workspace_id": workspace_id,
            "active_page": active_page,
            "page_title": page_title,
        },
    )


# ---------------------------------------------------------------------------
# Página raiz — shell vazio.
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def home(request: Request, workspace_id: str = "default") -> HTMLResponse:
    """
    Página raiz do shell.

    Na Sprint 0.5 mostra apenas a casca do design system.
    A proteção por autenticação (redirecionar não-autenticado para
    /login ou /setup) é feita pelo middleware do Bloco 5.8 — esta
    função não precisa ser alterada para isso.
    """
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context={
            "workspace_id": workspace_id,
            "active_page": None,
            "page_title": "CIRCE Intel Desk",
        },
    )


# ---------------------------------------------------------------------------
# Rotas de autenticação (HTML) — RF-021, Sprint 01 / Bloco 5.6.
# Fora do padrão workspace_id por decisão consciente (ver docstring
# do módulo). O processamento dos formulários (POST) está em
# app/api/auth.py — estas rotas apenas SERVEM as páginas.
# ---------------------------------------------------------------------------
@router.get("/setup", response_class=HTMLResponse)
async def setup_page(
    request: Request,
    db: Session = Depends(get_session),
):
    """
    Tela de cadastro do operador inicial (CA-021.1).

    Só existe na primeira execução: se já há ao menos um operador
    cadastrado, esta rota redireciona para /login — a tela de setup
    deixa de existir funcionalmente.
    """
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
) -> HTMLResponse:
    """
    Tela de login.

    Aceita ?error=1 na query string. Quando presente, o template
    exibe a mensagem genérica de falha de autenticação (CA-021.4).
    A rota não conhece a mensagem em si — só sinaliza ao template
    se deve ou não exibi-la.
    """
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "active_page": None,
            "page_title": "CIRCE // Acesso",
            "show_error": error is not None,
        },
    )


# ---------------------------------------------------------------------------
# Placeholders — 5 páginas de domínio.
# ---------------------------------------------------------------------------
@router.get("/cases", response_class=HTMLResponse)
async def cases_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    """Placeholder da tela de Casos. Implementação: Sprint 01."""
    return _render_placeholder(
        request=request,
        template_name="placeholders/cases.html",
        active_page="cases",
        page_title="CIRCE // Casos",
        workspace_id=workspace_id,
    )


@router.get("/persons", response_class=HTMLResponse)
async def persons_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    """Placeholder da tela de Pessoas. Implementação: Sprint 01."""
    return _render_placeholder(
        request=request,
        template_name="placeholders/persons.html",
        active_page="persons",
        page_title="CIRCE // Pessoas",
        workspace_id=workspace_id,
    )


@router.get("/organizations", response_class=HTMLResponse)
async def organizations_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    """Placeholder da tela de Organizações Criminosas. Implementação: Sprint 01-B."""
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
    """Placeholder da tela de Documentos. Implementação: Sprint 02."""
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
    """Placeholder da tela de Relatórios. Implementação: Sprint 03."""
    return _render_placeholder(
        request=request,
        template_name="placeholders/reports.html",
        active_page="reports",
        page_title="CIRCE // Relatórios",
        workspace_id=workspace_id,
    )


# ---------------------------------------------------------------------------
# Página de desenvolvimento — showcase de componentes.
# Não exposta no menu. Usada para validação visual e regressão.
# Critério de aceite CA-0.5.6.
# ---------------------------------------------------------------------------
@router.get("/dev/components", response_class=HTMLResponse)
async def dev_components(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dev/components.html",
        context={
            "workspace_id": workspace_id,
            "active_page": None,
            "page_title": "CIRCE // Showcase",
        },
    )