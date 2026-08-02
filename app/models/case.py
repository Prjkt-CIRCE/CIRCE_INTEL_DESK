"""
CIRCE Intel Desk — Modelo Case (caso/operação).

Referência: 05_MODELO_DE_DADOS.md §3.2.
Geração de case_code no padrão {ano}-{sequencial-4d} fica na camada
de serviço (Bloco 8). Aqui só o campo, com constraint de unicidade.

Sprint 01 — Bloco 2.
"""

from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Case(Base):
    """Caso ou operação cadastrada no CIRCE."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    procedure_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fact_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    responsible: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # CSV simples
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    documents = relationship("Document", back_populates="case", lazy="select")

    __table_args__ = (
        Index("idx_cases_case_code", "case_code"),
        Index("idx_cases_status", "status"),
        Index("idx_cases_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} case_code={self.case_code!r} name={self.name!r}>"
