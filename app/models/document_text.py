"""
CIRCE Intel Desk — Modelo DocumentText (RF-011)
Sprint 04 — Sub-passo 04-1 (modelo) / 04-2 (relationship document).

Representa o texto extraído por OCR de um Document, incluindo status
do processamento e de validação humana.

Ciclo de vida de ocr_status:
  pending -> processing -> done | failed

Ciclo de vida de validation_status:
  pending -> validated | rejected

CA-011.4: validation_status inicia como "pending".
CA-011.5: Este modelo nao toca stored_path.
CA-011.7: Toda decisao do operador (validate/reject) é auditada pelo ocr_service.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class DocumentText(Base):
    __tablename__ = "document_texts"

    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_texts_document_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Engine que gerou raw_text: "tesseract" | "easyocr"
    engine = Column(String(20), nullable=True)

    # Texto bruto extraido pelo OCR (nunca editado diretamente pelo operador)
    raw_text = Column(Text, nullable=True)

    # Texto corrigido/aprovado pelo operador após validação
    validated_text = Column(Text, nullable=True)

    # "pending" | "processing" | "done" | "failed"
    ocr_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    # "pending" | "validated" | "rejected"
    validation_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    validated_at = Column(DateTime(timezone=True), nullable=True)

    rejection_reason = Column(String(500), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # --- Relacionamentos ---

    # Document pai (CA-011.5: acesso ao stored_path e read-only no ocr_service)
    document = relationship(
        "Document",
        back_populates="document_text",
    )

    # Operador que validou/rejeitou (pode ser None enquanto pendente)
    validated_by_user = relationship(
        "User",
        foreign_keys=[validated_by],
    )

    def __repr__(self):
        return (
            f"<DocumentText id={self.id} document_id={self.document_id} "
            f"ocr_status={self.ocr_status!r} validation_status={self.validation_status!r}>"
        )
