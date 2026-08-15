"""
app/schemas/document_text.py
Sprint 04 — RF-011 (OCR e Documentos)

Schemas Pydantic para leitura e validação de resultados OCR.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


class DocumentTextRead(BaseModel):
    """Retorno completo de um registro DocumentText (GET)."""

    id: int
    document_id: int
    engine: Optional[str] = None
    raw_text: Optional[str] = None
    validated_text: Optional[str] = None
    ocr_status: str
    validation_status: str
    validated_by: Optional[int] = None
    validated_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Operações do operador
# ---------------------------------------------------------------------------


class DocumentTextValidate(BaseModel):
    """
    PATCH /api/documents/{doc_id}/ocr/validate

    action = "validate":
      - validated_text obrigatório
      - seta validation_status = "validated", validated_by, validated_at
      - indexa o texto no FTS5 (feito no service — 04-4)

    action = "reject":
      - rejection_reason obrigatório
      - seta validation_status = "rejected"
      - texto NÃO é indexado no FTS5
    """

    action: Literal["validate", "reject"] = Field(
        ...,
        description="'validate' para aprovar o texto; 'reject' para rejeitar.",
    )
    validated_text: Optional[str] = Field(
        None,
        description=(
            "Texto corrigido/aprovado pelo operador. "
            "Obrigatório quando action='validate'."
        ),
    )
    rejection_reason: Optional[str] = Field(
        None,
        max_length=500,
        description=(
            "Motivo da rejeição. "
            "Obrigatório quando action='reject'."
        ),
    )

    @model_validator(mode="after")
    def check_fields_by_action(self) -> DocumentTextValidate:
        if self.action == "validate" and not self.validated_text:
            raise ValueError(
                "validated_text é obrigatório quando action='validate'."
            )
        if self.action == "reject" and not self.rejection_reason:
            raise ValueError(
                "rejection_reason é obrigatório quando action='reject'."
            )
        return self


# ---------------------------------------------------------------------------
# Resumo compacto (para exibição no card de documento na UI)
# ---------------------------------------------------------------------------


class DocumentTextSummary(BaseModel):
    """
    Versão compacta usada no card de documento —
    não inclui o texto completo para não sobrecarregar a listagem.
    """

    id: int
    document_id: int
    ocr_status: str
    validation_status: str
    engine: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
