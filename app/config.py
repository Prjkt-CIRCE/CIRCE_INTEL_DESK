"""
CIRCE Intel Desk - configurações do sistema.
Lê variáveis de ambiente e do arquivo .env (quando presente).
Defaults garantem operação em loopback (RNF-007) mesmo sem .env.
"""
import os
import secrets
from functools import lru_cache
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
# --------------------------------------------------------------------
# SESSION_COOKIE_NAME (Sprint 01 / Bloco 5 / sub-passo 5.8.2)
# --------------------------------------------------------------------
# Nome do cookie de sessão (HMAC stateless, D17).
# Constante de módulo — não vai na classe Settings porque não é
# ajustável por .env: é um nome fixo do protocolo interno.
# Mora aqui — e não em api/auth.py — porque é transversal: tanto a
# camada de rotas (api/auth.py, que emite/apaga o cookie) quanto o
# middleware de proteção (web/middleware.py, que lê o cookie) precisam
# do mesmo nome. Fonte única da verdade. Decisão 5.8.2, Opção 2.
# --------------------------------------------------------------------
SESSION_COOKIE_NAME: str = "circe_session"
# --------------------------------------------------------------------
# SECRET_KEY (Sprint 01 / Bloco 5 / D18)
# --------------------------------------------------------------------
# Chave usada para assinar (HMAC-SHA256) o cookie de sessão.
# Decisão: arquivo local em data/.secret_key, gerado no primeiro uso.
# - Fora do Git por construção (data/ está no .gitignore).
# - Cada máquina tem sua chave própria (Casa != Trabalho), por desenho.
#   Efeito prático: ao trocar de máquina, o operador refaz login.
# - Lazy: só é criado quando uma rota de auth realmente precisar.
# - Cached em memória após a primeira leitura via lru_cache.
# --------------------------------------------------------------------
SECRET_KEY_FILENAME: str = ".secret_key"
SECRET_KEY_LENGTH_BYTES: int = 32  # 256 bits, alinhado com HMAC-SHA256.
def _secret_key_path() -> Path:
    """Caminho absoluto do arquivo da SECRET_KEY."""
    return settings.DATA_DIR / SECRET_KEY_FILENAME
@lru_cache(maxsize=1)
def get_secret_key() -> bytes:
    """
    Retorna a SECRET_KEY do servidor.
    Comportamento:
    - Se data/.secret_key existir, lê e retorna seu conteúdo.
    - Se não existir, gera 32 bytes aleatórios via secrets.token_bytes,
      grava em data/.secret_key e retorna.
    - Garante que DATA_DIR exista.
    - Aplica permissão 0o600 best-effort (no Windows/NTFS é ignorada).
    O resultado é cacheado para a vida do processo: o disco é lido no
    máximo uma vez por execução do servidor.
    """
    key_path = _secret_key_path()
    # Garante que data/ existe. Não falha se já existe.
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        key = key_path.read_bytes()
        if len(key) != SECRET_KEY_LENGTH_BYTES:
            # Sanidade: arquivo corrompido ou truncado.
            raise RuntimeError(
                f"SECRET_KEY em {key_path} tem tamanho inválido "
                f"({len(key)} bytes; esperado {SECRET_KEY_LENGTH_BYTES})."
            )
        return key
    # Geração inicial.
    key = secrets.token_bytes(SECRET_KEY_LENGTH_BYTES)
    key_path.write_bytes(key)
    # Best-effort em permissões. No Windows isso não faz nada efetivo,
    # mas a chamada é inócua e útil em ambientes POSIX futuros.
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        # Não falha se o SO recusar (Windows costuma aceitar silenciosamente).
        pass
    return key