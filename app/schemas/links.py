"""
CIRCE Intel Desk - Schemas Pydantic de Vinculos (RF-003).

Referencias:
  - 05_MODELO_DE_DADOS.md S3.4 (tabela case_person_links).
  - 05_MODELO_DE_DADOS.md S6.2 (reliability_level) e S6.4 (roles).
  - 06_CRITERIOS_DE_ACEITE.md RF-003 (CA-003.3 a CA-003.8).

AT-03.7: platea_exclude adicionado em PersonCaseLinkResponse.

Sprint 01 - Bloco 10, Sub-passo 10.4.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

ALLOWED_ROLES = {
    "suspeito",
    "investigado",
    "vitima",
    "testemunha",
    "envolvido",
    "interlocutor",
    "outro",
}

ALLOWED_RELIABILITY = {"pending", "low", "medium", "high", "validated"}


class PersonCaseLinkCreate(BaseModel):
    case_id: int
    person_id: int
    role_in_case: str
    source: str
    reliability_level: str = "pending"
    notes: Optional[str] = None

    @field_validator("role_in_case")
    @classmethod
    def _role_valido(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("O tipo de participacao e obrigatorio.")
        if v not in ALLOWED_ROLES:
            raise ValueError(
                f"Tipo de participacao invalido: {v!r}. "
                f"Valores aceitos: {sorted(ALLOWED_ROLES)}."
            )
        return v

    @field_validator("source")
    @classmethod
    def _source_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("A fonte da informacao e obrigatoria.")
        return v

    @field_validator("reliability_level")
    @classmethod
    def _reliability_valido(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            return "pending"
        if v not in ALLOWED_RELIABILITY:
            raise ValueError(
                f"Grau de confiabilidade invalido: {v!r}. "
                f"Valores aceitos: {sorted(ALLOWED_RELIABILITY)}."
            )
        return v

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class PersonCaseLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: int
    case_id: int
    person_id: int
    role_in_case: Optional[str] = None
    source: Optional[str] = None
    reliability_level: str
    notes: Optional[str] = None
    active: int
    created_at: str
    created_by: Optional[int] = None
    platea_exclude: bool = False

    # Campos enriquecidos por join (D-B10-03)
    person_name: Optional[str] = None
    case_code: Optional[str] = None
    case_name: Optional[str] = None