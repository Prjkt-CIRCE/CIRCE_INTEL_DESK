"""
app/models/document_text.py
Sprint 04 — RF-011 (OCR e Documentos)

Armazena o resultado de OCR aplicado a um documento.
Cada documento tem no máximo um registro DocumentText (UNIQUE em document_id).

Ciclo de vida do OCR:
  ocr_status:        pending → processing → done
                                          ↘ failed

Ciclo de validação do operador (CA-011.4):
  validation_status: pending → validated
                             → rejected

Invariante: o arquivo original (documents.file_path) NUNCA é alterado (CA-011.5).
"""

from __future__ import annotations

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

from app.database.base import Base


class DocumentText(Base):
    __tablename__ = "document_texts"

    id = Column(Integer, primary_key=True, index=True)

    # FK para documents.id — CASCADE: deletar doc apaga o resultado OCR junto
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Engine que processou: "tesseract" (PDFs via PyMuPDF) ou "easyocr" (imagens)
    engine = Column(String(20), nullable=True)

    # Texto bruto extraído pelo OCR (gerado automaticamente — imutável após criação)
    raw_text = Column(Text, nullable=True)

    # Texto após revisão/correção do operador (pode diferir do raw_text)
    validated_text = Column(Text, nullable=True)

    # Status do processo OCR
    # Valores: "pending" | "processing" | "done" | "failed"
    ocr_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    # Status de validação pelo operador (CA-011.4 — nasce como "pending")
    # Valores: "pending" | "validated" | "rejected"
    validation_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    # Quem validou/rejeitou e quando (preenchido pelo service em 04-2)
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)

    # Motivo de rejeição (obrigatório se validation_status = "rejected")
    rejection_reason = Column(String(500), nullable=True)

    # Timestamps
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

    # Relacionamento com o operador que validou
    validated_by_user = relationship("User", foreign_keys=[validated_by])

    # Nota: relationship com Document será adicionado em 04-2 (ocr_service)
    # via back_populates no modelo Document.
    # Por ora, acesso via document_id diretamente nos services.

    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_texts_document_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentText id={self.id} document_id={self.document_id} "
            f"ocr_status={self.ocr_status!r} validation_status={self.validation_status!r}>"
        )
