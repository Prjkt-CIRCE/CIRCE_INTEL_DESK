"""
CIRCE Intel Desk — rotas de autenticação (RF-021).

Endpoints:
- POST /setup   : cria o operador inicial (apenas na primeira execução).
- POST /login   : autentica um operador existente.
- POST /logout  : encerra a sessão (apaga o cookie).

Camada HTTP fina: valida entrada, despacha para serviços, monta resposta.
Não contém regra de domínio (03_ARQUITETURA.md §3.1).

CA-021.1: primeira execução exige cadastro de operador inicial.
CA-021.2: senha armazenada como hash Argon2id.
CA-021.4: falha de login devolve mensagem genérica, sem revelar a causa.

Auditoria (CA-021.9) NÃO é tratada aqui — entra no Bloco 7 via refactor.
Os pontos de inserção estão marcados com TODO(bloco-7).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Response
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings, SESSION_COOKIE_NAME
from app.database.session import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, SetupRequest
from app.services.auth_service import hash_password, verify_password
from app.services.session_service import issue_token


router = APIRouter(tags=["auth"])


# --------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------

# SESSION_COOKIE_NAME mudou de casa no sub-passo 5.8.2: agora vive em
# app/config.py (constante de módulo), porque o middleware de proteção
# (app/web/middleware.py) também precisa dela. Fonte única da verdade.
# Importada acima junto de `settings`.

# Mensagem única para qualquer falha de login (CA-021.4).
# Nunca diferenciar "usuário não existe" de "senha errada" de
# "conta desativada" — tudo devolve isto.
GENERIC_LOGIN_ERROR = "usuário ou senha inválidos"

# Hash dummy: usado quando o username não existe, para que o tempo de
# resposta do login seja indistinguível entre "usuário inexistente" e
# "usuário existe, senha errada" (mitigação de enumeração por timing).
# Calculado uma vez no import. A senha de origem é irrelevante e
# descartável — nunca corresponde a nada.
_DUMMY_HASH = hash_password("dummy-password-never-matches-anything")


# --------------------------------------------------------------------
# Helpers internos
# --------------------------------------------------------------------

def _utc_now_iso() -> str:
    """
    Timestamp atual em ISO 8601 UTC.

    Inline aqui por opção consciente: não acoplar a app/utils/time.py
    sem ter inspecionado aquele módulo. Refatorável em sub-passo futuro.
    """
    return datetime.now(timezone.utc).isoformat()


def _operator_exists(db: Session) -> bool:
    """True se já existe ao menos um operador cadastrado."""
    result = db.execute(select(User.id).limit(1)).first()
    return result is not None


def _session_ttl_seconds() -> int:
    """
    TTL do cookie de sessão, em segundos.

    Lê settings.SESSION_HOURS (atributo legado de config.py). A
    migração para settings_service.get_value('session_hours') é
    escopo do Bloco 6.
    """
    return settings.SESSION_HOURS * 3600


def _set_session_cookie(response: Response, user_id: int) -> None:
    """
    Emite o cookie de sessão assinado na resposta dada.

    Atributos (alinhamento A do sub-passo 5.5):
    - HttpOnly : JS do cliente não lê o cookie.
    - SameSite=strict : cookie nunca enviado cross-site.
    - Secure=False : obrigatório para funcionar em http://127.0.0.1.
    - Path=/ : válido para toda a aplicação.
    - Max-Age : alinhado ao TTL do token.
    """
    ttl = _session_ttl_seconds()
    token = issue_token(user_id=user_id, ttl_seconds=ttl)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=ttl,
        httponly=True,
        samesite="strict",
        secure=False,
        path="/",
    )


# --------------------------------------------------------------------
# POST /setup — criação do operador inicial (CA-021.1, CA-021.2)
# --------------------------------------------------------------------

@router.post("/setup")
def post_setup(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    area_atuacao: str = Form(default=""),
    db: Session = Depends(get_session),
):
    """
    Cria o operador inicial do sistema.

    Só funciona quando a tabela `users` está vazia. Se já existe
    operador, redireciona para /login (a rota deixa de existir
    funcionalmente após a primeira execução — CA-021.1).

    Em sucesso: cria o usuário, emite o cookie de sessão e
    redireciona para a raiz já autenticado.
    """
    # Guarda: setup só na primeira execução.
    if _operator_exists(db):
        return RedirectResponse(url="/login", status_code=303)

    # Validação de formato e força da senha (CA-021.3 via schema).
    try:
        data = SetupRequest(
            username=username,
            password=password,
            display_name=display_name,
            area_atuacao=area_atuacao,
        )
    except ValidationError:
        # Entrada inválida (senha curta, campo vazio, etc.).
        # Volta para a tela de setup sinalizando erro genérico.
        return RedirectResponse(url="/setup?error=1", status_code=303)

    # Criação do usuário. Senha vira hash Argon2id aqui (CA-021.2).
    now = _utc_now_iso()
    user = User(
        username=data.username,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        role="operator",
        active=1,
        area_atuacao=data.area_atuacao,
        last_login_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Defensivo: colisão de username. Em teoria impossível aqui
        # (users estava vazia), mas não confiamos — cinto e suspensório.
        db.rollback()
        return RedirectResponse(url="/setup?error=1", status_code=303)

    db.refresh(user)

    # TODO(bloco-7): audit_service.log_action(action="setup", user_id=user.id)

    # Operador criado e já autenticado.
    redirect = RedirectResponse(url="/", status_code=303)
    _set_session_cookie(redirect, user_id=user.id)
    return redirect


# --------------------------------------------------------------------
# POST /login — autenticação (CA-021.4)
# --------------------------------------------------------------------

@router.post("/login")
def post_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
):
    """
    Autentica um operador existente.

    Em sucesso: emite o cookie de sessão e redireciona para a raiz.
    Em qualquer falha (usuário inexistente, senha errada, conta
    desativada, entrada malformada): redireciona para
    /login?error=1 — mensagem genérica, sem revelar a causa
    (CA-021.4).
    """
    # Validação de formato. Falha aqui também é "inválido" genérico.
    try:
        data = LoginRequest(username=username, password=password)
    except ValidationError:
        return RedirectResponse(url="/login?error=1", status_code=303)

    # Busca o usuário.
    user = db.execute(
        select(User).where(User.username == data.username)
    ).scalar_one_or_none()

    if user is None:
        # Usuário não existe. Roda verify contra o hash dummy para
        # gastar o mesmo tempo de CPU que uma verificação real
        # (mitigação de enumeração por timing). Resultado descartado.
        verify_password(data.password, _DUMMY_HASH)
        # TODO(bloco-7): audit_service.log_action(action="login_failed", ...)
        return RedirectResponse(url="/login?error=1", status_code=303)

    # Usuário existe: verifica a senha de verdade.
    if not verify_password(data.password, user.password_hash):
        # TODO(bloco-7): audit_service.log_action(action="login_failed", ...)
        return RedirectResponse(url="/login?error=1", status_code=303)

    # Conta desativada: não loga, mesma mensagem genérica.
    if user.active != 1:
        # TODO(bloco-7): audit_service.log_action(action="login_failed", ...)
        return RedirectResponse(url="/login?error=1", status_code=303)

    # Sucesso. Atualiza last_login_at.
    user.last_login_at = _utc_now_iso()
    db.commit()

    # TODO(bloco-7): audit_service.log_action(action="login", user_id=user.id)

    redirect = RedirectResponse(url="/", status_code=303)
    _set_session_cookie(redirect, user_id=user.id)
    return redirect


# --------------------------------------------------------------------
# POST /logout — encerramento de sessão
# --------------------------------------------------------------------

@router.post("/logout")
def post_logout():
    """
    Encerra a sessão: apaga o cookie e redireciona para /login.

    O token em si ainda seria válido até expirar se reapresentado,
    mas o cookie foi removido do cliente. Invalidação server-side
    real (blocklist) é desnecessária para single-user local (D17).
    """
    # TODO(bloco-7): audit_service.log_action(action="logout", ...)

    redirect = RedirectResponse(url="/login", status_code=303)
    redirect.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="strict",
        secure=False,
    )
    return redirect