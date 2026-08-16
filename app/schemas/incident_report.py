"""
CIRCE Intel Desk — Schemas Pydantic para IncidentReport (RF-009).
Sprint 03 — Sub-passo 03-1.
Correcoes Sprint 04-6:
  - IncidentReportRead: model_validator(mode='before') remapeia campos ORM
    antes da validacao Pydantic:
      * criminal_classification (modelo) -> criminal_type (schema/API)
      * notes: None fixo (coluna nao existe no modelo; pendente sprint futura)
      * created_at / updated_at: datetime -> str ISO 8601 (schema espera str)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _dt_to_iso(dt: object) -> Optional[str]:
    """Converte datetime em string ISO 8601 com sufixo Z; None se nulo."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    return str(dt)


# ---------------------------------------------------------------------------
# Schemas de entrada
# ---------------------------------------------------------------------------

class IncidentReportCreate(BaseModel):
    """Payload de criacao de BO. Unico campo obrigatorio: bo_number (CA-009.1)."""
    bo_number: str
    bo_date: Optional[str] = None
    issuing_unit: Optional[str] = None
    summary: Optional[str] = None
    criminal_type: Optional[str] = None
    procedural_status: Optional[str] = None
    notes: Optional[str] = None
    case_id: Optional[int] = None        # vinculo a caso (CA-009.2)
    document_id: Optional[int] = None    # PDF do BO (CA-009.4)

    @field_validator("bo_number")
    @classmethod
    def bo_number_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("bo_number nao pode ser vazio")
        return v.strip()


class IncidentReportUpdate(BaseModel):
    """Payload de edicao parcial. Todos os campos sao opcionais (exclude_unset)."""
    bo_number: Optional[str] = None
    bo_date: Optional[str] = None
    issuing_unit: Optional[str] = None
    summary: Optional[str] = None
    criminal_type: Optional[str] = None
    procedural_status: Optional[str] = None
    notes: Optional[str] = None
    case_id: Optional[int] = None
    document_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Schema de resposta
# ---------------------------------------------------------------------------

class IncidentReportRead(BaseModel):
    """Resposta completa de um BO.

    O model_validator intercepta o objeto ORM (IncidentReport) antes que
    o Pydantic tente acessar os atributos diretamente, resolvendo tres
    incompatibilidades entre modelo SQLAlchemy e schema da API:

      modelo.criminal_classification  ->  schema.criminal_type
      (sem atributo notes)            ->  schema.notes = None
      modelo.created_at (datetime)    ->  schema.created_at (str ISO)
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    bo_number: str
    bo_date: Optional[str] = None
    issuing_unit: Optional[str] = None
    summary: Optional[str] = None
    criminal_type: Optional[str] = None
    procedural_status: Optional[str] = None
    notes: Optional[str] = None
    case_id: Optional[int] = None
    document_id: Optional[int] = None
    status: str
    created_at: Optional[str] = None
    created_by: Optional[int] = None
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def remap_from_orm(cls, values: object) -> dict:
        """
        Se values for um objeto ORM (nao dict), extrai os atributos
        manualmente aplicando o mapeamento de nomes e conversoes de tipo.
        Se for dict (ex.: testes), aplica apenas o remap de nomes.
        """
        if isinstance(values, dict):
            # Remap criminal_classification -> criminal_type se vier como dict
            if "criminal_classification" in values and "criminal_type" not in values:
                values["criminal_type"] = values.pop("criminal_classification")
            values.setdefault("notes", None)
            for f in ("created_at", "updated_at"):
                if isinstance(values.get(f), datetime):
                    values[f] = _dt_to_iso(values[f])
            return values

        # Objeto ORM — extrai atributos explicitamente
        return {
            "id": getattr(values, "id", None),
            "bo_number": getattr(values, "bo_number", None),
            "bo_date": getattr(values, "bo_date", None),
            "issuing_unit": getattr(values, "issuing_unit", None),
            "summary": getattr(values, "summary", None),
            # criminal_classification no modelo -> criminal_type na API
            "criminal_type": getattr(values, "criminal_classification", None),
            "procedural_status": getattr(values, "procedural_status", None),
            # notes nao existe no modelo; sempre None ate sprint futura
            "notes": None,
            "case_id": getattr(values, "case_id", None),
            "document_id": getattr(values, "document_id", None),
            "status": getattr(values, "status", None),
            # datetime -> str ISO 8601
            "created_at": _dt_to_iso(getattr(values, "created_at", None)),
            "created_by": getattr(values, "created_by", None),
            "updated_at": _dt_to_iso(getattr(values, "updated_at", None)),
            "updated_by": getattr(values, "updated_by", None),
        }
