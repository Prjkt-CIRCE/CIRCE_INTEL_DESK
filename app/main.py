"""
CIRCE Intel Desk — aplicação FastAPI.

Sprint 0: fundação técnica (endpoint /health validando o stack).
Sprint 0.5: shell visual (rota raiz / passa a renderizar o shell HTML;
            JSON de informação do sistema migra para /api/info).
Endpoints de domínio (casos, pessoas, organizações) entram a partir da
Sprint 01.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.web.routes import router as web_router


app = FastAPI(
    title="CIRCE Intel Desk",
    description="Sistema desktop local de inteligência operacional.",
    version="0.0.2-sprint0.5",
    # Documentação interativa do FastAPI.
    # Útil durante o desenvolvimento; revisaremos exposição na Sprint 10.
    docs_url="/docs",
    redoc_url="/redoc",
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