"""
CIRCE Intel Desk — Configuração de banco e sessão SQLAlchemy.

A engine usa SQLite no MVP (ADR-002). Caminho do arquivo lido de
app.config.settings.DATA_DIR. Banco fica em <DATA_DIR>/circe.db.

A criação efetiva do banco fica a cargo do Alembic (Bloco 3). Este
módulo apenas configura como conversar com ele uma vez que exista.

NOTAS:
- check_same_thread=False é necessário porque o FastAPI atende
  requisições em threads diferentes (Uvicorn workers).
- foreign_keys=ON é forçado por evento, porque SQLite não habilita
  por padrão. Sem isso, as FKs no schema são puramente cosméticas.

Sprint 01 — Bloco 2.
"""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def _build_database_url() -> str:
    """Monta a URL do SQLite a partir da configuração."""
    data_dir = Path(settings.DATA_DIR).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "circe.db"
    # SQLite com caminho absoluto: sqlite:///<caminho>
    return f"sqlite:///{db_path}"


DATABASE_URL = _build_database_url()

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    """Habilita FKs no SQLite — desligadas por padrão."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_session() -> Generator[Session, None, None]:
    """Dependency para FastAPI: cede uma sessão e garante close."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
