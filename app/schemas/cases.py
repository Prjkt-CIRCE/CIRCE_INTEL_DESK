"""
CIRCE Intel Desk — Schemas Pydantic do Caso (RF-001).

Referências:
  - 05_MODELO_DE_DADOS.md §3.2 (tabela cases).
  - 06_CRITERIOS_DE_ACEITE.md RF-001 (CA-001.1 a CA-001.7).

Contratos:
  - CaseCreate  : o que o operador envia ao criar. NÃO aceita case_code
                  (gerado pelo serviço) nem status (controlado pelo serviço).
                  name é obrigatório e não pode ser vazio/só-espaços (CA-001.3).
  - CaseUpdate  : edição parcial. case_code é IMUTÁVEL (não aparece aqui).
                  status NÃO é editável por aqui — arquivar é operação própria
                  (archive_case, Bloco 8.5).
  - CaseResponse: o que a API devolve. Espelha o modelo, serializável a
                  partir do objeto ORM (from_attributes=True).

Sprint 01 — Bloco 8, Sub-passo 8.2.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Campos de conteúdo editáveis (comuns a criação e edição)
# ---------------------------------------------------------------------------
# Mantidos como classe-base para não repetir a lista de campos opcionais.
# case_code e status ficam DE FORA de propósito (ver docstring do módulo).


class CaseCreate(BaseModel):
    """Dados que o operador fornece ao criar um caso.

    Apenas `name` é obrigatório (CA-001.1 / CA-001.3). Os demais são
    opcionais. O serviço gera `case_code` e fixa `status='active'`.
    """

    name: str
    description: Optional[str] = None
    procedure_number: Optional[str] = None
    fact_date: Optional[str] = None
    unit: Optional[str] = None
    responsible: Optional[str] = None
    tags: Optional[str] = None  # CSV simples (ver 05_MODELO_DE_DADOS.md §3.2)
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_nao_vazio(cls, v: str) -> str:
        """CA-001.3 (backend): nome obrigatório e não pode ser só espaços."""
        v = v.strip()
        if not v:
            raise ValueError("O nome do caso é obrigatório.")
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
    """Edição parcial de um caso (CA-001.4).

    Todos os campos são opcionais — só os enviados são alterados.
    case_code é IMUTÁVEL (não consta aqui). status NÃO muda por aqui
    (arquivamento é operação dedicada — archive_case, Bloco 8.5).
    """

    name: Optional[str] = None
    description: Optional[str] = None
    procedure_number: Optional[str] = None
    fact_date: Optional[str] = None
    unit: Optional[str] = None
    responsible: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_nao_vazio_se_enviado(cls, v: Optional[str]) -> Optional[str]:
        """Se `name` for enviado, não pode virar vazio (CA-001.3)."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("O nome do caso não pode ficar vazio.")
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
    """Representação de saída de um caso (serializável do ORM)."""

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
    created_at: str
    created_by: Optional[int] = None
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None
