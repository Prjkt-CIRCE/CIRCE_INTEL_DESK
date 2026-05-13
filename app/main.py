"""
CIRCE Intel Desk — aplicação FastAPI.
Sprint 0: fundação técnica (endpoint /health validando o stack).
Sprint 0.5: shell visual (rota raiz / passa a renderizar o shell HTML;
            JSON de informação do sistema migra para /api/info).
Sprint 01 — Bloco 4: lifespan que executa seed dos parâmetros operacionais
            (D11) no startup, idempotente.
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
# Rotas web (HTML) — definidas em app/web/routes.py.
# Inclui pelo menos a raiz /, que renderiza o shell visual.
# ---------------------------------------------------------------------------
app.include_router(web_router)
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
