"""
CIRCE Intel Desk — Schemas Pydantic de Vínculos (RF-003).

Referências:
  - 05_MODELO_DE_DADOS.md §3.4 (tabela case_person_links).
  - 05_MODELO_DE_DADOS.md §6.2 (reliability_level) e §6.4 (roles).
  - 06_CRITERIOS_DE_ACEITE.md RF-003 (CA-003.3 a CA-003.8).

Contratos:
  - PersonCaseLinkCreate  : o que o operador envia ao criar um vínculo.
                            role_in_case, source e reliability_level são
                            obrigatórios por CA-003.3, CA-003.4, CA-003.5.
  - PersonCaseLinkResponse: o que a API devolve. Inclui person_name,
                            case_code e case_name além dos campos do
                            vínculo (D-B10-03), para que a UI não precise
                            de roundtrip adicional para resolver nomes.
                            Não é serializável diretamente do ORM (campos
                            extras vêm de join) — construído explicitamente
                            no endpoint a partir de um dict.

Nota sobre role_in_case: o banco aceita NULL (nullable=True no modelo,
por compatibilidade de schema — Bloco 1); a obrigatoriedade é imposta
pelo schema Pydantic (CA-003.3) e pelo serviço. A constraint UNIQUE do
banco cobre a tripla (case_id, person_id, role_in_case) incluindo NULLs
no SQLite, mas o serviço nunca insere NULL em role_in_case.

Sprint 01 — Bloco 10, Sub-passo 10.4.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Papéis válidos para role_in_case (CA-003.3 / 05_MODELO_DE_DADOS.md §3.4).
# Espelha link_service.ROLES_VALIDOS — fonte canônica está no serviço;
# aqui valida na entrada HTTP antes mesmo de chegar ao serviço.
ALLOWED_ROLES = {
    "suspeito",
    "investigado",
    "vitima",
    "testemunha",
    "envolvido",
    "interlocutor",
    "outro",
}

# Grau de confiabilidade — mesmo enum de persons/cases
# (05_MODELO_DE_DADOS.md §6.2).
ALLOWED_RELIABILITY = {"pending", "low", "medium", "high", "validated"}


class PersonCaseLinkCreate(BaseModel):
    """Dados que o operador fornece ao criar um vínculo pessoa↔caso.

    case_id e person_id chegam no corpo do POST (a UI sabe qual entidade
    está aberta, e envia o par). A alternativa seria ler case_id/person_id
    da URL, mas o endpoint único /api/links/person-case serve os dois
    lados (tela de caso e tela de pessoa), então é mais limpo receber
    ambos no corpo.
    """

    case_id: int
    person_id: int
    role_in_case: str          # obrigatório — CA-003.3
    source: str                # obrigatório — CA-003.4
    reliability_level: str = "pending"   # CA-003.5; default explícito
    notes: Optional[str] = None

    @field_validator("role_in_case")
    @classmethod
    def _role_valido(cls, v: str) -> str:
        """CA-003.3: papel deve ser um dos valores do enum."""
        v = v.strip().lower()
        if not v:
            raise ValueError("O tipo de participação é obrigatório.")
        if v not in ALLOWED_ROLES:
            raise ValueError(
                f"Tipo de participação inválido: {v!r}. "
                f"Valores aceitos: {sorted(ALLOWED_ROLES)}."
            )
        return v

    @field_validator("source")
    @classmethod
    def _source_nao_vazio(cls, v: str) -> str:
        """CA-003.4: fonte da informação obrigatória e não só espaços."""
        v = v.strip()
        if not v:
            raise ValueError("A fonte da informação é obrigatória.")
        return v

    @field_validator("reliability_level")
    @classmethod
    def _reliability_valido(cls, v: str) -> str:
        """CA-003.5: grau de confiabilidade deve ser um dos valores do enum."""
        v = v.strip().lower()
        if not v:
            return "pending"
        if v not in ALLOWED_RELIABILITY:
            raise ValueError(
                f"Grau de confiabilidade inválido: {v!r}. "
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
    """Representação de saída de um vínculo pessoa↔caso.

    Inclui person_name, case_code e case_name além dos campos do link
    (D-B10-03) — construído explicitamente no endpoint via join, não
    diretamente do ORM. Por isso from_attributes=False (padrão).
    """

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

    # Campos enriquecidos por join (D-B10-03) — ausentes nos campos nativos do link.
    person_name: Optional[str] = None   # full_name da pessoa
    case_code: Optional[str] = None     # case_code do caso
    case_name: Optional[str] = None     # name do caso
