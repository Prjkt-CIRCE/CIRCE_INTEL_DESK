"""
CIRCE Intel Desk - ponto de entrada.

Uso:
    python run.py

Sobe o servidor Uvicorn em 127.0.0.1:8765 (loopback only - RNF-007).
Para encerrar: Ctrl+C.
"""

import uvicorn

from app.config import settings


def main() -> None:
    """Sobe o Uvicorn com configuracoes de loopback fixadas."""
    # IMPORTANTE: host e passado explicitamente como "127.0.0.1".
    # Mesmo que settings.HOST seja alterado, esta linha garante loopback.
    # Defesa em profundidade contra A3 (modelo de ameacas).
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=False,  # reload=True so durante desenvolvimento ativo.
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
