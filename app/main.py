"""
CIRCE Intel Desk — aplicação FastAPI.

Sprint 0: fundação técnica (endpoint /health validando o stack).
Sprint 0.5: shell visual (rota raiz / passa a renderizar o shell HTML;
            JSON de informação do sistema migra para /api/info).
Sprint 01 — Bloco 4: lifespan que executa seed dos parâmetros operacionais
            (D11) no startup, idempotente.
Sprint 01 — Bloco 5 (5.8): middleware auth_guard protege todas as rotas
            exceto as exceções públicas (ver app/web/middleware.py).
Sprint 01 — Bloco 9 (9.4): registrado o router de Pessoas (RF-002),
            espelhando o registro do router de Casos do Bloco 8.3.

Endpoints de domínio (casos, pessoas, organizações) entram a partir da
Sprint 01.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.services.settings_service import seed_defaults
from app.web.routes import router as web_router
from app.web.middleware import auth_guard
from app.api.auth import router as auth_router
from app.api.cases import router as cases_router
from app.api.persons import router as persons_router

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — eventos de startup/shutdown da aplicação.
#
# No startup, garante que a tabela `settings` tem todos os parâmetros
# operacionais (D11) com defaults aplicados. Idempotente: rodar várias
# vezes não duplica nem sobrescreve.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executa setup no startup e teardown no shutdown."""
    # Startup
    created = seed_defaults()
    if created > 0:
        logger.info("Settings seed: %d parametro(s) criado(s).", created)
    else:
        logger.info("Settings seed: todos os parametros ja existiam.")
    yield
    # Shutdown — nada a fazer por enquanto.


app = FastAPI(
    title="CIRCE Intel Desk",
    description="Sistema desktop local de inteligência operacional.",
    version="0.1.0-sprint01",
    # Documentação interativa do FastAPI.
    # Útil durante o desenvolvimento; revisaremos exposição na Sprint 10.
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Arquivos estáticos — CSS, JS, fontes.
#
# Caminho calculado a partir deste arquivo:
#   app/main.py -> app/static/
# Isso evita dependência de cwd na hora de iniciar o servidor.
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Middleware de proteção de rotas (RF-021) — sub-passo 5.8.
#
# auth_guard intercepta TODA requisição: deixa passar as exceções
# públicas (/health, /static/, /setup, /login, /logout, /docs e afins),
# exige cookie de sessão válido para o resto, e redireciona para /login
# ou /setup quando não há. Detalhes e justificativa em
# app/web/middleware.py.
#
# Registrado via app.middleware("http")(...) — forma funcional. FastAPI
# aplica os middlewares numa pilha; como este é o único, a ordem em
# relação aos include_router abaixo é indiferente.
# ---------------------------------------------------------------------------
app.middleware("http")(auth_guard)


# ---------------------------------------------------------------------------
# Rotas web (HTML) — definidas em app/web/routes.py.
# Inclui pelo menos a raiz /, que renderiza o shell visual.
# ---------------------------------------------------------------------------
app.include_router(web_router)
app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(persons_router)


# ---------------------------------------------------------------------------
# Rotas de sistema — diagnóstico e informação operacional.
# /health continua exatamente como na Sprint 0 (critério de aceite preservado).
# /api/info passa a ser o endpoint JSON de boas-vindas (era a raiz na Sprint 0).
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """
    Endpoint de verificacao do sistema.
    Retorna status OK quando o servidor esta no ar.
    Criterio de aceite da Sprint 0.
    """
    return {"status": "ok"}


@app.get("/api/info", tags=["system"])
def api_info() -> dict[str, str]:
    """Informações básicas da aplicação. Substitui o JSON antigo da raiz."""
    return {
        "system": "CIRCE Intel Desk",
        "version": app.version,
        "status": "running",
        "host": settings.HOST,
        "port": str(settings.PORT),
    }
