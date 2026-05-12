"""
CIRCE Intel Desk — Modelo User (operador do sistema).

Referência: 05_MODELO_DE_DADOS.md §3.1.
Campo area_atuacao reservado para uso futuro (pendência seção 11 do
ESTADO_DO_PROJETO.md — Ideia I3).

Sprint 01 — Bloco 2.
"""

from typing import Optional

from sqlalchemy import Index, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Operador autenticado do CIRCE."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)  # Argon2id
    role: Mapped[str] = mapped_column(String, default="operator", nullable=False)
    active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Reservado para uso futuro (Ideia I3). Não usado nesta sprint.
    area_atuacao: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    last_login_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("idx_users_username", "username"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
