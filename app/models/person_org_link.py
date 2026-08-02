"""
CIRCE Intel Desk — Modelo PersonOrgLink (vínculo pessoa ↔ organização).

Referência: 05_MODELO_DE_DADOS.md §3.5, RF-005.
Tipos de vínculo: membro, suspeito_membro, simpatizante, ex_membro,
familiar, vitima, rival.

Constraint UNIQUE(person_id, org_id, link_type) impede duplicação
com mesmo tipo entre a mesma pessoa e organização.

Sprint 01-B — Sub-passo B1.
"""
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PersonOrgLink(Base):
    """Vínculo entre pessoa e organização criminosa."""

    __tablename__ = "person_org_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("persons.id"), nullable=False
    )
    org_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )

    # membro | suspeito_membro | simpatizante | ex_membro | familiar | vitima | rival
    link_type: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    period_start: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    period_end: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reliability_level: Mapped[str] = mapped_column(
        String, default="pending", nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "person_id", "org_id", "link_type",
            name="uq_person_org_type"
        ),
        Index("idx_pol_person", "person_id"),
        Index("idx_pol_org", "org_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<PersonOrgLink id={self.id} person_id={self.person_id} "
            f"org_id={self.org_id} link_type={self.link_type!r}>"
        )