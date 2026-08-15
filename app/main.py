"""
CIRCE Intel Desk — aplicação FastAPI.

Sprint 0: fundação técnica (endpoint /health validando o stack).
Sprint 0.5: shell visual (rota raiz / passa a renderizar o shell HTML;
            JSON de informação do sistema migra para /api/info).
Sprint 01 — Bloco 4: lifespan que executa seed dos parâmetros operacionais
            (D11) no startup, idempotente.
Sprint 01 — Bloco 5 (5.8): middleware auth_guard protege todas as rotas
            exceto as exceções públicas (ver app/web/middleware.py).
Sprint 01 — Bloco 9 (9.4): registrado o router de Pessoas (RF-002).
Sprint 01 — Bloco 10 (10.4): registrado o router de Vínculos (RF-003).
Sprint 01 — Bloco 11.4: registrado o router de Auditoria (RF-020).
Sprint 03 — Sub-passo 03-3: registrado o router de BOs (RF-009).
Sprint 03 — Sub-passo 03-7: registrado o router de Backup (RF-022).
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
from app.api.links import router as links_router
from app.api.audit import router as audit_router
from app.api.organizations import router as organizations_router
from app.api.documents import router as documents_router
from app.api.search import router as search_router
from app.api.incident_reports import router as incident_reports_router
from app.api.incident_reports import router_cases as incident_reports_cases_router
from app.api.backup import router as backup_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executa setup no startup e teardown no shutdown."""
    created = seed_defaults()
    if created > 0:
        logger.info("Settings seed: %d parametro(s) criado(s).", created)
    else:
        logger.info("Settings seed: todos os parametros ja existiam.")
    yield


app = FastAPI(
    title="CIRCE Intel Desk",
    description="Sistema desktop local de inteligência operacional.",
    version="0.1.0-sprint03",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.middleware("http")(auth_guard)

app.include_router(web_router)
app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(persons_router)
app.include_router(links_router)
app.include_router(audit_router)
app.include_router(organizations_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(incident_reports_router)
app.include_router(incident_reports_cases_router)
app.include_router(backup_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Endpoint de verificacao do sistema."""
    return {"status": "ok"}


@app.get("/api/info", tags=["system"])
def api_info() -> dict[str, str]:
    """Informações básicas da aplicação."""
    return {
        "system": "CIRCE Intel Desk",
        "version": app.version,
        "status": "running",
        "host": settings.HOST,
        "port": str(settings.PORT),
    }
