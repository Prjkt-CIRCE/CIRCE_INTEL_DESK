"""
CIRCE Intel Desk — Modelo AuditLog (trilha de auditoria).

Referência: 05_MODELO_DE_DADOS.md §3.8, ADR-003.
A geração de record_hash e previous_hash é responsabilidade do
audit_service (Bloco 7), conforme ADR-003 §2.

NOTA SOBRE 'metadata':
A coluna no banco é 'metadata' (conforme DDL e ADR-003 §2.1).
No modelo Python, o atributo é 'metadata_json' para evitar conflito
com Base.metadata (atributo reservado do DeclarativeBase do SQLAlchemy).
O mapeamento name='metadata' preserva o nome real da coluna no SQL.
A canonicalização do ADR-003 trabalha com o nome 'metadata' do campo
canônico, então a leitura do registro para hash usa o valor desta
coluna independente do nome do atributo Python.

Sprint 01 — Bloco 2.
"""

from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """Registro imutável de ação sensível no CIRCE."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)  # ISO 8601 UTC
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    user_display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Coluna 'metadata' no banco; atributo 'metadata_json' no modelo Python
    # para evitar conflito com Base.metadata.
    metadata_json: Mapped[Optional[str]] = mapped_column(
        "metadata", String, nullable=True
    )

    status: Mapped[str] = mapped_column(String, default="success", nullable=False)
    previous_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    record_hash: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action!r} "
            f"timestamp={self.timestamp!r}>"
        )
