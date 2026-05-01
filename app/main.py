"""
CIRCE Intel Desk - aplicação FastAPI.

Sprint 0: apenas /health para validar a fundação técnica.
Endpoints de domínio (casos, pessoas, organizações) entram a partir da Sprint 01.
"""

from fastapi import FastAPI

from app.config import settings


app = FastAPI(
    title="CIRCE Intel Desk",
    description="Sistema desktop local de inteligência operacional.",
    version="0.0.1-sprint0",
    # Documentação interativa do FastAPI.
    # Útil durante o desenvolvimento; revisaremos exposição na Sprint 10.
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """
    Endpoint de verificacao do sistema.

    Retorna status OK quando o servidor esta no ar.
    Criterio de aceite da Sprint 0.
    """
    return {"status": "ok"}


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Mensagem de boas-vindas para a raiz."""
    return {
        "system": "CIRCE Intel Desk",
        "version": app.version,
        "status": "running",
        "host": settings.HOST,
        "port": str(settings.PORT),
    }
