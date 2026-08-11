"""
CIRCE Intel Desk - Modelo IncidentReport (Boletim de Ocorrencia).
Referencia: 05_MODELO_DE_DADOS.md, RF-009, CA-009.1 a CA-009.5.
Sprint 03 - Sub-passo 03-1.

Um BO e vinculado obrigatoriamente a um caso (case_id).
Vinculo opcional a pessoa (person_id) e documento anexo (document_id).
Campos de tipificacao penal e status processual sao insumos do RF-023.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IncidentReport(Base):
    """Boletim de Ocorrencia vinculado a caso, com vinculo opcional a pessoa e documento."""

    __tablename__ = "incident_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Vinculo obrigatorio ao caso
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cases.id"), nullable=False
    )

    # Vinculo opcional a pessoa (papel registrado em person_role)
    person_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("persons.id"), nullable=True
    )

    # Papel da pessoa no BO (vitima, autor, comunicante, testemunha, outro)
    person_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Vinculo opcional a documento anexo (PDF do BO)
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=True
    )

    # Dados do BO
    bo_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bo_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    issuing_unit: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Tipificacao penal e status processual (insumos do RF-023)
    criminal_classification: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    procedural_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Resumo narrativo
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Auditoria
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Exclusao logica
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Relacionamentos
    case = relationship("Case", back_populates="incident_reports")
    person = relationship("Person", back_populates="incident_reports")
    document = relationship("Document")

    __table_args__ = (
        Index("idx_incident_reports_case_id", "case_id"),
        Index("idx_incident_reports_person_id", "person_id"),
        Index("idx_incident_reports_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentReport id={self.id} case_id={self.case_id} "
            f"bo_number={self.bo_number!r}>"
        )