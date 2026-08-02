"""
CIRCE Intel Desk — Modelo Organization (organização criminosa).

Referência: 05_MODELO_DE_DADOS.md §3.3, RF-004.
Tipos válidos: faccao_prisional, milicia, orcrim_trafico,
orcrim_patrimonial, outra.

Sprint 01-B — Sub-passo B1.
"""
from typing import Optional

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Organization(Base):
    """Organização criminosa ou facção."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    siglas: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    alcunhas: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # faccao_prisional | milicia | orcrim_trafico | orcrim_patrimonial | outra
    org_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    area_atuacao: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reliability_level: Mapped[str] = mapped_column(
        String, default="pending", nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # active | archived
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)

    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_org_name", "name"),
        Index("idx_org_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name!r}>"