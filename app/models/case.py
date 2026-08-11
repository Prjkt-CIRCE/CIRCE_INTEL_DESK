"""
CIRCE Intel Desk - Modelo Case (caso/operacao).
Referencia: 05_MODELO_DE_DADOS.md §3.2.
Geracao de case_code no padrao {ano}-{sequencial-4d} fica na camada
de servico (Bloco 8). Aqui so o campo, com constraint de unicidade.
Sprint 01 - Bloco 2.
AT-03.6: campo platea_status adicionado (sincronizacao Intel Desk -> Athena).
"""
from typing import Optional
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

# Valores validos para platea_status (D-AT-019 / AT-03.6).
# none          -> caso nao compartilhado (padrao).
# shared        -> caso publicado na Platea com sucesso.
# pending_sync  -> publicacao solicitada, aguardando envio ao Athena.
# error         -> ultima tentativa de sincronizacao falhou.
PLATEA_STATUS_VALUES = ("none", "shared", "pending_sync", "error")


class Case(Base):
    """Caso ou operacao cadastrada no CIRCE."""

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
    platea_status: Mapped[str] = mapped_column(
        String, default="none", nullable=False
    )  # AT-03.6: estado de sincronizacao com a Platea (Athena)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    documents = relationship("Document", back_populates="case", lazy="select")
    incident_reports = relationship("IncidentReport", back_populates="case", lazy="select")

    __table_args__ = (
        Index("idx_cases_case_code", "case_code"),
        Index("idx_cases_status", "status"),
        Index("idx_cases_name", "name"),
        Index("idx_cases_platea_status", "platea_status"),
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} case_code={self.case_code!r} name={self.name!r}>"
