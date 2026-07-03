"""
CIRCE Intel Desk — Schemas Pydantic de Pessoa (RF-002).

Referências:
  - 05_MODELO_DE_DADOS.md §3.3 (tabela persons).
  - 06_CRITERIOS_DE_ACEITE.md RF-002 (CA-002.1 a CA-002.8).

Contratos:
  - PersonCreate  : o que o operador envia ao criar. full_name é obrigatório
                    e não pode ser vazio/só-espaços (CA-002.1). cpf chega
                    como o operador digitou (com ou sem máscara) — a
                    normalização para apenas dígitos acontece no
                    person_service (ver docstring de app/models/person.py),
                    não aqui: o schema só faz strip de espaços, igual aos
                    demais campos opcionais.
  - PersonUpdate  : edição parcial (CA-002.6). status NÃO é editável por
                    aqui — arquivar é operação própria (archive_person,
                    espelhando archive_case do Bloco 8.5).
  - PersonResponse: o que a API devolve. Espelha o modelo, serializável a
                    partir do objeto ORM (from_attributes=True).

Sprint 01 — Bloco 9, Sub-passo 9.2.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Grau de confiabilidade — mesmo enum usado em cases/case_person_links
# (05_MODELO_DE_DADOS.md §3.3). Validado aqui porque, diferente de
# `status` (controlado pelo serviço), `reliability_level` é informado
# livremente pelo operador.
ALLOWED_RELIABILITY = {"pending", "low", "medium", "high", "validated"}


# ---------------------------------------------------------------------------
# Campos de conteúdo editáveis (comuns a criação e edição)
# ---------------------------------------------------------------------------
# Mantidos como classe-base para não repetir a lista de campos opcionais.
# status fica DE FORA de propósito (ver docstring do módulo).
class PersonCreate(BaseModel):
    """Dados que o operador fornece ao criar uma pessoa.

    Apenas `full_name` é obrigatório (CA-002.1). Os demais são opcionais.
    O serviço normaliza `cpf` para apenas dígitos e fixa `status='active'`.
    """

    full_name: str
    aliases: Optional[str] = None  # ; separado (CA-002.3)
    cpf: Optional[str] = None  # normalizado no service (CA-002.2)
    rg: Optional[str] = None
    birth_date: Optional[str] = None
    mother_name: Optional[str] = None
    father_name: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    reliability_level: Optional[str] = None  # default 'pending' no service

    @field_validator("full_name")
    @classmethod
    def _full_name_nao_vazio(cls, v: str) -> str:
        """CA-002.1 (backend): nome completo obrigatório e não só espaços."""
        v = v.strip()
        if not v:
            raise ValueError("O nome completo da pessoa é obrigatório.")
        return v

    @field_validator(
        "aliases",
        "cpf",
        "rg",
        "birth_date",
        "mother_name",
        "father_name",
        "notes",
        "source",
    )
    @classmethod
    def _strip_opcionais(cls, v: Optional[str]) -> Optional[str]:
        """Normaliza opcionais: strip; string vazia vira None."""
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("reliability_level")
    @classmethod
    def _reliability_valido(cls, v: Optional[str]) -> Optional[str]:
        """Se enviado, precisa ser um dos valores do enum de confiabilidade."""
        if v is None:
            return None
        v = v.strip().lower()
        if v and v not in ALLOWED_RELIABILITY:
            raise ValueError(
                f"grau de confiabilidade inválido: {v!r}. "
                f"Valores aceitos: {sorted(ALLOWED_RELIABILITY)}."
            )
        return v or None


class PersonUpdate(BaseModel):
    """Edição parcial de uma pessoa (CA-002.6).

    Todos os campos são opcionais — só os enviados são alterados.
    status NÃO muda por aqui (arquivamento é operação dedicada —
    archive_person, espelhando o Bloco 8.5).
    """

    full_name: Optional[str] = None
    aliases: Optional[str] = None
    cpf: Optional[str] = None
    rg: Optional[str] = None
    birth_date: Optional[str] = None
    mother_name: Optional[str] = None
    father_name: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    reliability_level: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def _full_name_nao_vazio_se_enviado(cls, v: Optional[str]) -> Optional[str]:
        """Se `full_name` for enviado, não pode virar vazio (CA-002.1)."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("O nome completo da pessoa não pode ficar vazio.")
        return v

    @field_validator(
        "aliases",
        "cpf",
        "rg",
        "birth_date",
        "mother_name",
        "father_name",
        "notes",
        "source",
    )
    @classmethod
    def _strip_opcionais(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("reliability_level")
    @classmethod
    def _reliability_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if v and v not in ALLOWED_RELIABILITY:
            raise ValueError(
                f"grau de confiabilidade inválido: {v!r}. "
                f"Valores aceitos: {sorted(ALLOWED_RELIABILITY)}."
            )
        return v or None


class PersonResponse(BaseModel):
    """Representação de saída de uma pessoa (serializável do ORM)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    aliases: Optional[str] = None
    cpf: Optional[str] = None
    rg: Optional[str] = None
    birth_date: Optional[str] = None
    mother_name: Optional[str] = None
    father_name: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    reliability_level: str
    status: str
    created_at: str
    created_by: Optional[int] = None
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None
