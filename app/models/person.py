"""
CIRCE Intel Desk — Modelo Person (pessoa qualificada).

Referência: 05_MODELO_DE_DADOS.md §3.3.
CPF é normalizado para apenas dígitos antes da persistência —
normalização fica na camada de serviço (Bloco 9), aqui só o campo.

Sprint 01 — Bloco 2.
"""

from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Person(Base):
    """Pessoa cadastrada no CIRCE."""

    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    aliases: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # ; separado
    cpf: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # só dígitos
    rg: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    birth_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mother_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    father_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reliability_level: Mapped[str] = mapped_column(
        String, default="pending", nullable=False
    )
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)

    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        Index("idx_persons_full_name", "full_name"),
        Index("idx_persons_cpf", "cpf"),
        Index("idx_persons_aliases", "aliases"),
        Index("idx_persons_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Person id={self.id} full_name={self.full_name!r}>"
