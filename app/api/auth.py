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
CA-021.5 (Bloco 6): força bruta mitigada via bruteforce_service.
CA-021.6 (Bloco 6): TTL da sessão lido de settings_service ('session_hours').
CA-021.9 (Bloco 7): login, falha, logout e bloqueios são logados via audit_service.

NOTA (Python 3.13 + SQLAlchemy 2.0.36):
  O SQLAlchemy com autocommit=False abre transação implícita assim que
  qualquer operação toca a sessão. log_action com manage_transaction=True
  tentaria executar BEGIN IMMEDIATE sobre transação já aberta, causando
  OperationalError. Todas as chamadas a log_action neste módulo usam
  manage_transaction=False — a transação já está aberta pelo SQLAlchemy.
  O chamador é responsável pelo commit/rollback (D47).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import SESSION_COOKIE_NAME
from app.database.session import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, SetupRequest
from app.services import bruteforce_service, settings_service
from app.services.audit_service import log_action
from app.services.auth_service import hash_password, verify_password
from app.services.session_service import issue_token


router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

GENERIC_LOGIN_ERROR = "usuário ou senha inválidos"

_DUMMY_HASH = hash_password("dummy-password-never-matches-anything")


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _operator_exists(db: Session) -> bool:
    result = db.execute(select(User.id).limit(1)).first()
    return result is not None


def _session_ttl_seconds() -> int:
    hours = int(settings_service.get_value("session_hours", 8))
    return hours * 3600


def _set_session_cookie(response: Response, user_id: int) -> None:
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


# ---------------------------------------------------------------------------
# POST /setup — criação do operador inicial (CA-021.1, CA-021.2)
# ---------------------------------------------------------------------------

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
    operador, redireciona para /login.

    Após criar o usuário, registra action="setup" no audit log
    (CA-021.9). O log e a criação do usuário estão na mesma
    transação: se o log falhar, o usuário não é criado (ADR-003 §2.4).
    """
    if _operator_exists(db):
        return RedirectResponse(url="/login", status_code=303)

    try:
        data = SetupRequest(
            username=username,
            password=password,
            display_name=display_name,
            area_atuacao=area_atuacao,
        )
    except ValidationError:
        return RedirectResponse(url="/setup?error=1", status_code=303)

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
        db.flush()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/setup?error=1", status_code=303)

    log_action(
        db,
        action="setup",
        user_id=user.id,
        user_display_name=user.display_name,
        description=f"Operador inicial '{user.username}' cadastrado.",
        manage_transaction=False,
    )

    db.commit()

    redirect = RedirectResponse(url="/", status_code=303)
    _set_session_cookie(redirect, user_id=user.id)
    return redirect


# ---------------------------------------------------------------------------
# POST /login — autenticação (CA-021.4, CA-021.5, CA-021.9)
# ---------------------------------------------------------------------------

@router.post("/login")
def post_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
):
    """
    Autentica um operador existente.

    Todos os eventos de login são registrados em audit_log (CA-021.9):
    - login_blocked : tentativa durante bloqueio ativo.
    - login_failed  : credencial inválida ou conta desativada.
    - login         : autenticação bem-sucedida.

    Cada log_action usa manage_transaction=False — a transação já está
    aberta pelo SQLAlchemy (autocommit=False). O commit é responsabilidade
    deste chamador (D47).
    """
    try:
        data = LoginRequest(username=username, password=password)
    except ValidationError:
        return RedirectResponse(url="/login?error=1", status_code=303)

    blocked, secs_remaining = bruteforce_service.is_blocked(data.username)
    if blocked:
        log_action(
            db,
            action="login_blocked",
            description=f"Tentativa bloqueada para username '{data.username}'.",
            metadata={"username": data.username, "secs_remaining": secs_remaining},
            status="alert",
            manage_transaction=False,
        )
        db.commit()
        return RedirectResponse(
            url=f"/login?blocked=1&secs={secs_remaining}",
            status_code=303,
        )

    user = db.execute(
        select(User).where(User.username == data.username)
    ).scalar_one_or_none()

    if user is None:
        verify_password(data.password, _DUMMY_HASH)
        log_action(
            db,
            action="login_failed",
            description=f"Username '{data.username}' não encontrado.",
            metadata={"reason": "unknown_user"},
            status="failure",
            manage_transaction=False,
        )
        db.commit()
        return RedirectResponse(url="/login?error=1", status_code=303)

    if not verify_password(data.password, user.password_hash):
        blocked_now, block_secs = bruteforce_service.register_failure(data.username)
        log_action(
            db,
            action="login_failed",
            user_id=user.id,
            user_display_name=user.display_name,
            metadata={"reason": "wrong_password"},
            status="failure",
            manage_transaction=False,
        )
        if blocked_now:
            log_action(
                db,
                action="login_blocked",
                user_id=user.id,
                user_display_name=user.display_name,
                description="Bloqueio ativado após falhas repetidas.",
                metadata={"secs_remaining": block_secs},
                status="alert",
                manage_transaction=False,
            )
            db.commit()
            return RedirectResponse(
                url=f"/login?blocked=1&secs={block_secs}",
                status_code=303,
            )
        db.commit()
        return RedirectResponse(url="/login?error=1", status_code=303)

    if user.active != 1:
        log_action(
            db,
            action="login_failed",
            user_id=user.id,
            user_display_name=user.display_name,
            metadata={"reason": "account_disabled"},
            status="failure",
            manage_transaction=False,
        )
        db.commit()
        return RedirectResponse(url="/login?error=1", status_code=303)

    bruteforce_service.register_success(data.username)
    user.last_login_at = _utc_now_iso()

    log_action(
        db,
        action="login",
        user_id=user.id,
        user_display_name=user.display_name,
        description="Login bem-sucedido.",
        manage_transaction=False,
    )

    db.commit()

    redirect = RedirectResponse(url="/", status_code=303)
    _set_session_cookie(redirect, user_id=user.id)
    return redirect


# ---------------------------------------------------------------------------
# POST /logout — encerramento de sessão (CA-021.9)
# ---------------------------------------------------------------------------

@router.post("/logout")
def post_logout(
    request: Request,
    db: Session = Depends(get_session),
):
    """
    Encerra a sessão: loga o evento, apaga o cookie e redireciona.

    user_id vem de request.state.user_id, populado pelo middleware
    de autenticação (Bloco 5.8). Se por algum motivo não estiver
    presente (sessão expirada, acesso direto), loga sem user_id.
    """
    user_id = getattr(request.state, "user_id", None)

    log_action(
        db,
        action="logout",
        user_id=user_id,
        description="Sessão encerrada pelo operador.",
        manage_transaction=False,
    )
    db.commit()

    redirect = RedirectResponse(url="/login", status_code=303)
    redirect.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="strict",
        secure=False,
    )
    return redirect