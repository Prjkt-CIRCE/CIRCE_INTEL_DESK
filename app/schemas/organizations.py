"""
CIRCE Intel Desk — Schemas Pydantic para Organização (RF-004).

Sprint 01-B — Sub-passo B3.
"""
from typing import Optional
from pydantic import BaseModel, field_validator


ORG_TYPES = {
    "faccao_prisional", "milicia", "orcrim_trafico",
    "orcrim_patrimonial", "outra",
}

RELIABILITY_LEVELS = {"pending", "baixo", "medio", "alto", "validado"}


class OrganizationCreate(BaseModel):
    name: str
    siglas: Optional[str] = None
    alcunhas: Optional[str] = None
    org_type: Optional[str] = None
    area_atuacao: Optional[str] = None
    source: Optional[str] = None
    reliability_level: str = "pending"
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name não pode ser vazio.")
        return v.strip()

    @field_validator("org_type")
    @classmethod
    def org_type_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ORG_TYPES:
            raise ValueError(f"org_type inválido. Valores aceitos: {sorted(ORG_TYPES)}")
        return v

    @field_validator("reliability_level")
    @classmethod
    def reliability_valido(cls, v: str) -> str:
        if v not in RELIABILITY_LEVELS:
            raise ValueError(f"reliability_level inválido. Valores aceitos: {sorted(RELIABILITY_LEVELS)}")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    siglas: Optional[str] = None
    alcunhas: Optional[str] = None
    org_type: Optional[str] = None
    area_atuacao: Optional[str] = None
    source: Optional[str] = None
    reliability_level: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("org_type")
    @classmethod
    def org_type_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ORG_TYPES:
            raise ValueError(f"org_type inválido.")
        return v

    @field_validator("reliability_level")
    @classmethod
    def reliability_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in RELIABILITY_LEVELS:
            raise ValueError(f"reliability_level inválido.")
        return v


class OrganizationResponse(BaseModel):
    id: int
    name: str
    siglas: Optional[str]
    alcunhas: Optional[str]
    org_type: Optional[str]
    area_atuacao: Optional[str]
    source: Optional[str]
    reliability_level: str
    notes: Optional[str]
    status: str
    created_at: str
    created_by: Optional[int]
    updated_at: Optional[str]
    updated_by: Optional[int]

    model_config = {"from_attributes": True}