"""
Rotas web (HTML) do CIRCE Intel Desk.

Todas as funções de rota recebem `workspace_id` como parâmetro,
mesmo que na Sprint 0.5 apenas o workspace 'default' seja
exposto. Isso é preparação para ADR-010 (Workspaces nomeados
por caso ativo, status: Proposed em 2026-05-03), de forma
que a promoção da ADR para Accepted nas sprints 03–05 não
exija refatoração da camada de roteamento.

Exceção a esse padrão: as rotas de autenticação (GET /setup,
GET /login, GET /lock), adicionadas no Sprint 01 / Blocos 5.6
e 6.4. Workspace é um conceito que só existe DEPOIS de
autenticado — essas telas são o portão, não um cômodo.
Decisão consciente do operador.

Páginas placeholder de domínio (Casos, Pessoas, Organizações,
Documentos, Relatórios) são apenas casca — implementação real
de cada uma entra na sprint correspondente do roadmap.

Bloco 6.8: helper _shell_context centraliza a montagem do
contexto comum a todas as rotas autenticadas (workspace_id,
active_page, page_title, inactivity_minutes). Centraliza a
leitura de settings_service para evitar duplicação em cada
rota e garantir que a injeção de data-inactivity-minutes no
<body> não seja esquecida em rotas futuras.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from pathlib import Path

from app.api.auth import _operator_exists
from app.database.session import get_session
from app.services import settings_service

# Diretório de templates relativo a este arquivo:
# app/web/routes.py -> app/web/templates/
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
    """
    Monta o dict de contexto comum às rotas que renderizam a shell
    autenticada (base.html). Centraliza a leitura de configurações
    operacionais (inactivity_lock_minutes) para garantir consistência
    entre todas as telas.

    Por que centralizar: o template base.html injeta o valor de
    inactivity_minutes em data-inactivity-minutes do <body>, que é
    lido pelo inactivity_lock.js. Se uma rota nova esquecer de
    passar inactivity_minutes, o JS lê NaN e desativa o timer (fail-
    safe da D33), mas isso é falha silenciosa. Helper único garante
    que todas as rotas paguem o mesmo preço de inclusão.

    inactivity_minutes pode ser 0 (D33: "nunca bloquear"). O JS
    trata 0 como flag de desligado.
    """
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
        context=_shell_context(workspace_id, active_page, page_title),
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
        context=_shell_context(workspace_id, None, "CIRCE Intel Desk"),
    )


# ---------------------------------------------------------------------------
# Rotas de autenticação (HTML) — RF-021, Sprint 01 / Blocos 5.6 e 6.4.
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
    blocked: str | None = None,
    secs: int | None = None,
    next: str | None = None,
) -> HTMLResponse:
    """
    Tela de login.

    Querystring suportada:
    - ?error=1   : exibe mensagem genérica de falha (CA-021.4).
    - ?blocked=1 : exibe mensagem de bloqueio por força bruta (CA-021.5,
                   D34). Acompanhado de ?secs=N indicando segundos
                   restantes.
    - ?next=<url>: para onde redirecionar após login bem-sucedido.
                   Usado pela tela /lock para preservar estado
                   (CA-021.7). O POST /login NÃO consome isto ainda
                   na Sprint 01 — é apenas exibido no form como
                   hidden field para iteração futura (Bloco 11+).

    A rota não conhece as mensagens em si — só sinaliza ao template
    se deve ou não exibi-las.
    """
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
    from_: str | None = None,
) -> HTMLResponse:
    """
    Tela de bloqueio (CA-021.7, CA-021.8).

    Estado intermediário: o operador ainda tem cookie de sessão
    válido, mas a UI se comporta como se ele precisasse reautenticar.
    Acionada por:
    - Timer de inatividade no cliente (CA-021.7).
    - Atalho Ctrl+L manual (CA-021.8).

    Querystring:
    - ?from=<url> : URL em que o operador estava quando o lock
                    disparou. Repassada ao template para construir
                    o link de "voltar após desbloquear". Default '/'.

    NOTA 1: o parâmetro de função se chama `from_` porque `from` é
    palavra reservada em Python. Extração via query_params direto
    é mais simples que importar Query e alias.

    NOTA 2: o URL-encoding do from_url é feito AQUI, na rota, com
    urllib.parse.quote, e passado pronto ao template (next_qs).
    Decisão consciente: o filtro |urlencode do Jinja2 deu problema
    de renderização no Bloco 6.6 (a tag <a> saiu escapada). Manter
    a transformação no Python é mais previsível.

    A rota é PROTEGIDA pelo middleware (D36, sub-passo 6.5).
    """
    from urllib.parse import quote

    from_url = request.query_params.get("from", "/")
    # Querystring para o link de reautenticação. quote() escapa
    # caracteres especiais (?, &, =, espaço, /, etc) com codificação
    # segura para uso dentro de URLs.
    next_qs = quote(from_url, safe="")

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
        context=_shell_context(workspace_id, None, "CIRCE // Showcase"),
    )