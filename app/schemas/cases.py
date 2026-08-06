"""
CIRCE Intel Desk - Schemas Pydantic do Caso (RF-001).

Referencias:
  - 05_MODELO_DE_DADOS.md §3.2 (tabela cases).
  - 06_CRITERIOS_DE_ACEITE.md RF-001 (CA-001.1 a CA-001.7).

Contratos:
  - CaseCreate  : o que o operador envia ao criar. NAO aceita case_code
                  (gerado pelo servico) nem status (controlado pelo servico).
                  name e obrigatorio e nao pode ser vazio/so-espacos (CA-001.3).
  - CaseUpdate  : edicao parcial. case_code e IMUTAVEL (nao aparece aqui).
                  status NAO e editavel por aqui - arquivar e operacao propria
                  (archive_case, Bloco 8.5).
                  platea_status: aceito aqui para o toggle de compartilhar
                  na Platea (AT-03.6). Valores: none | shared | pending_sync | error.
  - CaseResponse: o que a API devolve. Espelha o modelo, serializavel a
                  partir do objeto ORM (from_attributes=True).

Sprint 01 - Bloco 8, Sub-passo 8.2.
AT-03.6: platea_status adicionado em CaseUpdate e CaseResponse.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Tipo literal para platea_status - garante validacao no schema (AT-03.6).
PlateaStatus = Literal["none", "shared", "pending_sync", "error"]


class CaseCreate(BaseModel):
    """Dados que o operador fornece ao criar um caso.

    Apenas `name` e obrigatorio (CA-001.1 / CA-001.3). Os demais sao
    opcionais. O servico gera `case_code` e fixa `status='active'`.
    platea_status nao entra na criacao - nasce sempre como 'none'.
    """

    name: str
    description: Optional[str] = None
    procedure_number: Optional[str] = None
    fact_date: Optional[str] = None
    unit: Optional[str] = None
    responsible: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_nao_vazio(cls, v: str) -> str:
        """CA-001.3 (backend): nome obrigatorio e nao pode ser so espacos."""
        v = v.strip()
        if not v:
            raise ValueError("O nome do caso e obrigatorio.")
        return v

    @field_validator(
        "description",
        "procedure_number",
        "fact_date",
        "unit",
        "responsible",
        "tags",
        "notes",
    )
    @classmethod
    def _strip_opcionais(cls, v: Optional[str]) -> Optional[str]:
        """Normaliza opcionais: strip; string vazia vira None."""
        if v is None:
            return None
        v = v.strip()
        return v or None


class CaseUpdate(BaseModel):
    """Edicao parcial de um caso (CA-001.4).

    Todos os campos sao opcionais - so os enviados sao alterados.
    case_code e IMUTAVEL (nao consta aqui). status NAO muda por aqui
    (arquivamento e operacao dedicada - archive_case, Bloco 8.5).
    platea_status aceito para toggle de compartilhamento na Platea (AT-03.6).
    """

    name: Optional[str] = None
    description: Optional[str] = None
    procedure_number: Optional[str] = None
    fact_date: Optional[str] = None
    unit: Optional[str] = None
    responsible: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    platea_status: Optional[PlateaStatus] = None  # AT-03.6

    @field_validator("name")
    @classmethod
    def _name_nao_vazio_se_enviado(cls, v: Optional[str]) -> Optional[str]:
        """Se `name` for enviado, nao pode virar vazio (CA-001.3)."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("O nome do caso nao pode ficar vazio.")
        return v

    @field_validator(
        "description",
        "procedure_number",
        "fact_date",
        "unit",
        "responsible",
        "tags",
        "notes",
    )
    @classmethod
    def _strip_opcionais(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class CaseResponse(BaseModel):
    """Representacao de saida de um caso (serializavel do ORM)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    case_code: str
    name: str
    description: Optional[str] = None
    procedure_number: Optional[str] = None
    fact_date: Optional[str] = None
    unit: Optional[str] = None
    responsible: Optional[str] = None
    status: str
    tags: Optional[str] = None
    notes: Optional[str] = None
    platea_status: str = "none"  # AT-03.6
    created_at: str
    created_by: Optional[int] = None
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None