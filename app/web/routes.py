"""
Rotas web (HTML) do CIRCE Intel Desk.

Todas as funções de rota recebem `workspace_id` como parâmetro,
mesmo que na Sprint 0.5 apenas o workspace 'default' seja
exposto. Isso é preparação para ADR-010 (Workspaces nomeados
por caso ativo, status: Proposed em 2026-05-03), de forma
que a promoção da ADR para Accepted nas sprints 03–05 não
exija refatoração da camada de roteamento.

Páginas placeholder de domínio (Casos, Pessoas, Organizações,
Documentos, Relatórios) são apenas casca — implementação real
de cada uma entra na sprint correspondente do roadmap.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from pathlib import Path

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
    A partir da Sprint 01 redireciona para a tela de login (RF-021)
    ou para a primeira execução.
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