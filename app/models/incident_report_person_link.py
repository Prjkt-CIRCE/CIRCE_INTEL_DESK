"""
CIRCE Intel Desk — Modelo IncidentReportPersonLink.

Vínculo entre Boletim de Ocorrência e Pessoa, com papel declarado (CA-009.3).

Sprint 03 — Sub-passo 03-2.
"""
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IncidentReportPersonLink(Base):
    """Vínculo entre BO e Pessoa com papel declarado (CA-009.3)."""

    __tablename__ = "incident_report_person_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    incident_report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("incident_reports.id"), nullable=False
    )
    person_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("persons.id"), nullable=False
    )
    role_in_report: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=ativo, 0=removido

    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "incident_report_id", "person_id", "role_in_report",
            name="uq_ir_person_role",
        ),
        Index("idx_ir_person_links_report_id", "incident_report_id"),
        Index("idx_ir_person_links_person_id", "person_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentReportPersonLink id={self.id} "
            f"report={self.incident_report_id} person={self.person_id} "
            f"role={self.role_in_report!r} active={self.active}>"
        )
