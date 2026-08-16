"""
CIRCE Intel Desk — Schemas Pydantic para DocumentText (RF-011).
Sprint 04 — Sub-passo 04-3.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


class DocumentTextRead(BaseModel):
    """Resposta completa de um registro de OCR."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    engine: Optional[str]
    raw_text: Optional[str]
    validated_text: Optional[str]
    ocr_status: str
    validation_status: str
    validated_by: Optional[int]
    validated_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


class DocumentTextValidate(BaseModel):
    """
    Payload para validar ou rejeitar um texto OCR (CA-011.7).

    action='validate': validated_text obrigatório.
    action='reject':   rejection_reason obrigatório.
    """

    action: Literal["validate", "reject"]
    validated_text: Optional[str] = None
    rejection_reason: Optional[str] = None

    @model_validator(mode="after")
    def check_action_fields(self) -> "DocumentTextValidate":
        if self.action == "validate" and not self.validated_text:
            raise ValueError(
                "validated_text é obrigatório quando action='validate'."
            )
        if self.action == "reject" and not self.rejection_reason:
            raise ValueError(
                "rejection_reason é obrigatório quando action='reject'."
            )
        return self


class OCRTriggerResponse(BaseModel):
    """Resposta 202 ao disparar OCR em background."""

    message: str
    document_id: int
    ocr_status: str
