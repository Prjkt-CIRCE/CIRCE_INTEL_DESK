"""
CIRCE Intel Desk — Schemas Pydantic para IncidentReport (RF-009).

Sprint 03 — Sub-passo 03-1.
"""
from typing import Optional

from pydantic import BaseModel, field_validator


class IncidentReportCreate(BaseModel):
    """Payload de criação de BO. Único campo obrigatório: bo_number (CA-009.1)."""

    bo_number: str
    bo_date: Optional[str] = None
    issuing_unit: Optional[str] = None
    summary: Optional[str] = None
    criminal_type: Optional[str] = None
    procedural_status: Optional[str] = None
    notes: Optional[str] = None
    case_id: Optional[int] = None        # vínculo a caso (CA-009.2)
    document_id: Optional[int] = None    # PDF do BO (CA-009.4)

    @field_validator("bo_number")
    @classmethod
    def bo_number_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("bo_number não pode ser vazio")
        return v.strip()


class IncidentReportUpdate(BaseModel):
    """Payload de edição parcial. Todos os campos são opcionais (exclude_unset)."""

    bo_number: Optional[str] = None
    bo_date: Optional[str] = None
    issuing_unit: Optional[str] = None
    summary: Optional[str] = None
    criminal_type: Optional[str] = None
    procedural_status: Optional[str] = None
    notes: Optional[str] = None
    case_id: Optional[int] = None
    document_id: Optional[int] = None

    model_config = {"extra": "forbid"}


class IncidentReportRead(BaseModel):
    """Resposta completa de um BO."""

    id: int
    bo_number: str
    bo_date: Optional[str]
    issuing_unit: Optional[str]
    summary: Optional[str]
    criminal_type: Optional[str]
    procedural_status: Optional[str]
    notes: Optional[str]
    case_id: Optional[int]
    document_id: Optional[int]
    status: str
    created_at: str
    created_by: Optional[int]
    updated_at: Optional[str]
    updated_by: Optional[int]

    model_config = {"from_attributes": True}
