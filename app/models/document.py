"""
CIRCE Intel Desk — Modelo Document
Sprint 01-B — B8.
Sprint 04 — 04-2: adicionado relationship document_text (RF-011).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc)


class Document(Base):
    """Documento importado e vinculado a um caso."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cases.id"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AT-03.7: marcacao [NAO COMPARTILHAR] - exclui item do payload Platea
    platea_exclude: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # --- Relacionamentos ---
    case = relationship("Case", back_populates="documents")

    # Sprint 04 — RF-011: texto OCR extraído (1:1, cascade delete)
    document_text = relationship(
        "DocumentText",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_documents_case_id", "case_id"),
        Index("idx_documents_sha256", "sha256_hash"),
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} case_id={self.case_id} "
            f"original_filename={self.original_filename!r}>"
        )
