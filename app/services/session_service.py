"""
CIRCE Intel Desk - emissão e verificação de tokens de sessão.

Sessão materializada como cookie HMAC stateless (D17).
- Sem tabela `sessions` no banco.
- Token = "<payload_b64>.<assinatura_b64>".
- payload = JSON compacto {"uid": int, "iat": int, "exp": int}.
- assinatura = HMAC-SHA256(SECRET_KEY, payload_b64_bytes).
- Codificação: base64 url-safe sem padding.

Honra:
- 03_ARQUITETURA.md §8: "cookie httpOnly assinado".
- ADR-001: autenticação via cookie httpOnly.

Funções puras: sem I/O, sem dependência de FastAPI/banco.
O componente HTTP (rotas) é responsável por `Set-Cookie` / `Cookie`.
"""
import base64
import hashlib
import hmac
import json
import time

from app.config import get_secret_key


# --------------------------------------------------------------------
# Exceções
# --------------------------------------------------------------------

class InvalidTokenError(ValueError):
    """
    Token inválido por qualquer motivo: formato quebrado, assinatura
    incorreta, payload corrompido, ou expirado.

    A mensagem externa é deliberadamente genérica para não vazar a
    natureza exata da falha. Diferenciação fica em log (Bloco 7).
    """


# --------------------------------------------------------------------
# Codificação base64 url-safe sem padding
# --------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    """Codifica bytes em base64 url-safe, sem padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    """Decodifica base64 url-safe sem padding. Repõe o padding antes."""
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


# --------------------------------------------------------------------
# Assinatura HMAC-SHA256
# --------------------------------------------------------------------

def _sign(payload_b64: str) -> str:
    """
    Calcula a assinatura HMAC-SHA256 sobre o payload já codificado.
    Retorna a assinatura em base64 url-safe sem padding.
    """
    mac = hmac.new(
        key=get_secret_key(),
        msg=payload_b64.encode("ascii"),
        digestmod=hashlib.sha256,
    ).digest()
    return _b64url_encode(mac)


# --------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------

def issue_token(user_id: int, ttl_seconds: int) -> str:
    """
    Emite um token de sessão assinado, válido por `ttl_seconds`.

    Args:
        user_id: ID do operador autenticado (linha em `users`).
        ttl_seconds: validade do token a partir de agora, em segundos.

    Returns:
        String no formato "<payload_b64>.<assinatura_b64>".
    """
    now = int(time.time())
    payload = {
        "uid": user_id,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))
    signature_b64 = _sign(payload_b64)
    return f"{payload_b64}.{signature_b64}"


def verify_token(token: str) -> int:
    """
    Verifica um token de sessão e retorna o user_id se válido.

    Args:
        token: string recebida do cookie.

    Returns:
        user_id (int) do operador autenticado.

    Raises:
        InvalidTokenError: token malformado, com assinatura inválida,
            ou expirado. A mensagem é deliberadamente genérica.
    """
    if not isinstance(token, str) or "." not in token:
        raise InvalidTokenError("Token inválido.")

    try:
        payload_b64, signature_b64 = token.split(".", 1)
    except ValueError:
        raise InvalidTokenError("Token inválido.")

    if not payload_b64 or not signature_b64:
        raise InvalidTokenError("Token inválido.")

    # Verifica assinatura ANTES de tentar interpretar o payload.
    # Resistente a timing attack via compare_digest.
    expected = _sign(payload_b64)
    if not hmac.compare_digest(expected, signature_b64):
        raise InvalidTokenError("Token inválido.")

    # Assinatura ok. Agora pode decodificar o payload com segurança.
    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise InvalidTokenError("Token inválido.")

    # Validação de estrutura.
    if not isinstance(payload, dict):
        raise InvalidTokenError("Token inválido.")
    uid = payload.get("uid")
    exp = payload.get("exp")
    if not isinstance(uid, int) or not isinstance(exp, int):
        raise InvalidTokenError("Token inválido.")

    # Expiração.
    if int(time.time()) >= exp:
        raise InvalidTokenError("Token inválido.")

    return uid