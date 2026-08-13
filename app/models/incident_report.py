"""
CIRCE Intel Desk — Modelo IncidentReport (Boletim de Ocorrência).

Referência: 05_MODELO_DE_DADOS.md §3.x (RF-009).

Vínculos a pessoas (CA-009.3) ficam em tabela separada
incident_report_person_links, entregue no sub-passo 03-2 junto
com o incident_report_service (D-03-1-01).

Sprint 03 — Sub-passo 03-1.
"""
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IncidentReport(Base):
    """Boletim de Ocorrência cadastrado no CIRCE (RF-009)."""

    __tablename__ = "incident_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identificação do BO
    bo_number: Mapped[str] = mapped_column(String, nullable=False)
    bo_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)   # ISO 8601
    issuing_unit: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Conteúdo
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    criminal_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)    # tipificação penal
    procedural_status: Mapped[Optional[str]] = mapped_column(String, nullable=True) # status processual
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Vínculos opcionais
    case_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("cases.id"), nullable=True
    )
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=True
    )  # PDF do BO anexado (CA-009.4)

    # Ciclo de vida
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
        Index("idx_incident_reports_case_id", "case_id"),
        Index("idx_incident_reports_status", "status"),
        Index("idx_incident_reports_bo_number", "bo_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentReport id={self.id} bo_number={self.bo_number!r} "
            f"case_id={self.case_id}>"
        )
