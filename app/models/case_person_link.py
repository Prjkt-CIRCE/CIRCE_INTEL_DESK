"""
CIRCE Intel Desk — Modelo CasePersonLink (vínculo pessoa ↔ caso).

Referência: 05_MODELO_DE_DADOS.md §3.4.
Constraint UNIQUE(case_id, person_id, role_in_case) impede duplicação
de vínculo com mesmo papel (CA-003.6).

Sprint 01 — Bloco 2.
"""

from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CasePersonLink(Base):
    """Vínculo entre pessoa e caso."""

    __tablename__ = "case_person_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cases.id"), nullable=False
    )
    person_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("persons.id"), nullable=False
    )
    # suspeito | investigado | vitima | testemunha | envolvido | interlocutor | outro
    role_in_case: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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
            "case_id", "person_id", "role_in_case", name="uq_case_person_role"
        ),
        Index("idx_cpl_case", "case_id"),
        Index("idx_cpl_person", "person_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<CasePersonLink id={self.id} case_id={self.case_id} "
            f"person_id={self.person_id} role_in_case={self.role_in_case!r}>"
        )
