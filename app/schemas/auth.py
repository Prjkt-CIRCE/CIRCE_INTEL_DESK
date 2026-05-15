"""
Schemas Pydantic para o fluxo de autenticação (RF-021).

- SetupRequest: corpo de POST /setup, criação do operador inicial.
- LoginRequest: corpo de POST /login.
- UserPublic: representação segura de usuário em respostas.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.auth_service import (
    WeakPasswordError,
    validate_password_strength,
)


# --------------------------------------------------------------------
# Entrada — criação do operador inicial (CA-021.1)
# --------------------------------------------------------------------

class SetupRequest(BaseModel):
    """
    Corpo do POST /setup.

    Aceito apenas quando a tabela `users` está vazia (regra aplicada
    na rota, não no schema). O schema valida formato e força da senha.
    """

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1)  # tamanho real validado abaixo
    display_name: str = Field(min_length=1, max_length=120)
    area_atuacao: Optional[str] = Field(default=None, max_length=120)

    @field_validator("username", "display_name")
    @classmethod
    def _strip_whitespace(cls, v: str) -> str:
        """Remove espaços nas pontas. Garante que não fica vazio."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Campo não pode ser apenas espaços.")
        return stripped

    @field_validator("area_atuacao")
    @classmethod
    def _normalize_area(cls, v: Optional[str]) -> Optional[str]:
        """String vazia ou só espaços vira None (D19)."""
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None

    @field_validator("password")
    @classmethod
    def _validate_password_strength(cls, v: str) -> str:
        """Aplica a regra de força definida em auth_service (CA-021.3)."""
        try:
            validate_password_strength(v)
        except WeakPasswordError as e:
            raise ValueError(str(e))
        return v


# --------------------------------------------------------------------
# Entrada — login (CA-021.4)
# --------------------------------------------------------------------

class LoginRequest(BaseModel):
    """
    Corpo do POST /login.

    Não aplica validação de força. Qualquer falha (usuário inexistente,
    senha curta, senha errada) deve devolver a mesma mensagem genérica
    "usuário ou senha inválidos" — CA-021.4. Validar força aqui seria
    leak de informação.
    """

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


# --------------------------------------------------------------------
# Saída — representação segura de usuário
# --------------------------------------------------------------------

class UserPublic(BaseModel):
    """
    Representação de um usuário em respostas da API.

    NÃO inclui password_hash. NÃO inclui flags internas. Apenas o
    subconjunto seguro de campos.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    area_atuacao: Optional[str] = None
    created_at: str