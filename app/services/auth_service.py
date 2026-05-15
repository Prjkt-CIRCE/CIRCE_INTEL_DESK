"""
CIRCE Intel Desk - serviço de autenticação (Argon2id).

Funções puras de hashing/verificação de senha e validação de força.
Sem I/O em banco. Sem dependência de FastAPI. Sem efeito colateral.

Implementa:
- CA-021.2: senha armazenada como Argon2id, nunca em claro.
- CA-021.3: senha exige no mínimo 12 caracteres.

Honra:
- ADR-001: Argon2id como derivação de senha.
- RS-005 (04_SEGURANCA.md §16).
"""
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


# --------------------------------------------------------------------
# Parâmetros do Argon2id
# --------------------------------------------------------------------
# Usamos os defaults do argon2-cffi, calibrados pelo time da lib.
# Razões em sub-passo 5.2 (não viram ADR — apenas honram ADR-001):
# - Defaults são revisados a cada release da lib.
# - Single-user local, sem pressão de concorrência.
# - Cada hash carrega seus parâmetros embutidos (formato PHC), então
#   mudar defaults no futuro NÃO invalida hashes antigos.
# --------------------------------------------------------------------

_hasher = PasswordHasher()


# --------------------------------------------------------------------
# Validação de força (CA-021.3)
# --------------------------------------------------------------------

MIN_PASSWORD_LENGTH: int = 12


class WeakPasswordError(ValueError):
    """Senha não atende ao requisito mínimo de força."""


def validate_password_strength(plain: str) -> None:
    """
    Valida que a senha atende ao requisito mínimo do CA-021.3.

    Regra (apenas): senha tem no mínimo MIN_PASSWORD_LENGTH caracteres.
    Sem requisitos adicionais de complexidade — fora do escopo do CA.

    Lança:
        WeakPasswordError: se a senha for None, vazia, ou curta demais.

    Retorna:
        None em caso de senha válida.
    """
    if plain is None or len(plain) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres."
        )


# --------------------------------------------------------------------
# Hashing e verificação (CA-021.2)
# --------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """
    Gera hash Argon2id da senha em claro.

    A senha NÃO é validada para força aqui — chame
    validate_password_strength antes, se aplicável. Esta função
    aceita qualquer string e produz um hash determinístico-em-formato
    mas com salt aleatório a cada chamada (mesmo input → hashes
    diferentes, todos válidos).

    Retorna:
        String no formato PHC:
            $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
    """
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica se uma senha em claro bate com um hash Argon2id.

    Retorna:
        True  se a senha corresponde ao hash.
        False se a senha não corresponde, OU se o hash estiver
              corrompido / em formato inválido.

    Nota: esta função nunca lança em "senha errada" — converte a
    exceção da lib em False. Isso simplifica as rotas (CA-021.4:
    mensagem genérica em qualquer falha).
    """
    try:
        _hasher.verify(hashed, plain)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False