"""
CIRCE Intel Desk - configurações do sistema.

Lê variáveis de ambiente e do arquivo .env (quando presente).
Defaults garantem operação em loopback (RNF-007) mesmo sem .env.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Raiz do projeto = pasta que contém este arquivo subindo dois níveis:
# este arquivo está em app/config.py, raiz é o pai do "app".
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configurações do CIRCE, com defaults seguros."""

    # Rede - ver 10_MODELO_DE_AMEACAS.md (A3) e RNF-007.
    # Default fixo em loopback. Alterar exige novo ADR.
    HOST: str = "127.0.0.1"
    PORT: int = 8765

    # Paths.
    DATA_DIR: Path = PROJECT_ROOT / "data"

    # Sessão (utilizado a partir da Sprint 01).
    SESSION_HOURS: int = 8
    INACTIVITY_LOCK_MINUTES: int = 5

    # Logging.
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Instância única, importável por outros módulos como:
#     from app.config import settings
settings = Settings()
