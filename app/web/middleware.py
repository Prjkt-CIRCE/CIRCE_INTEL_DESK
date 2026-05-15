"""
CIRCE Intel Desk — middleware de proteção de rotas (RF-021).

Esta é a peça que torna a autenticação OBRIGATÓRIA. Sem ela, as rotas
internas respondem sem checar cookie nenhum — login existiria, mas não
protegeria nada. O middleware fecha essa porta:

    requisição entra
        -> rota é exceção pública?  -> sim: passa direto
        -> tem cookie de sessão válido?  -> sim: passa
        -> não tem operador cadastrado?  -> redireciona p/ /setup
        -> tem operador, mas sem cookie?  -> redireciona p/ /login

Hierarquia de verdade (consulta do sub-passo 5.8.1):
- 10_MODELO_DE_AMEACAS.md §5, contra A2: "autenticação obrigatória de
  operador". O middleware é o que materializa essa mitigação.
- 01_SPEC_MASTER.md RF-021: autenticação "antes de qualquer ação que
  escreva no banco ou acesse dado sensível" — guarda transversal, não
  decorador rota a rota.
- ADR-001: cookie httpOnly + FastAPI. Middleware funcional é uso
  idiomático da stack; nenhum ADR novo necessário.

Decisões de design (validadas pelo operador, sub-passo 5.8.1):
- Middleware FUNCIONAL (@app.middleware("http")), não classe.
- Exceções por LISTA DE PREFIXOS + startswith, não regex — auditável.
- Fluxo B: distingue "sem operador" (-> /setup) de "sem cookie" (-> /login).

NÃO faz parte deste middleware:
- Bloqueio por força bruta, sessão por idade/inatividade (Bloco 6).
- Auditoria de acesso (Bloco 7).
- Qualquer noção de workspace (ADR-010, Proposed) — workspace é problema
  pós-autenticação; o middleware opera uma camada abaixo disso.
"""
import logging

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import SESSION_COOKIE_NAME
from app.database.session import SessionLocal
from app.models.user import User
from app.services.session_service import verify_token, InvalidTokenError

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Exceções públicas — rotas acessíveis SEM autenticação.
# --------------------------------------------------------------------
# Lista de prefixos. Uma requisição cujo caminho começa com qualquer
# um destes passa direto, sem checagem de cookie.
#
# Manter esta lista CURTA e LEGÍVEL é uma decisão de segurança: cada
# item é uma porta deliberadamente destrancada. Auditar = ler a lista.
#
# Exceções ESSENCIAIS — o sistema não funciona sem elas abertas:
_PUBLIC_PREFIXES_ESSENCIAIS = (
    "/health",   # diagnóstico; público desde a Sprint 0 (CA da Sprint 0).
    "/static/",  # CSS/JS/fontes; sem isso, /login renderiza sem estilo.
    "/setup",    # cadastro do operador inicial; é o ovo antes da galinha.
    "/login",    # a própria tela de autenticação.
    "/logout",   # encerrar sessão não pode exigir sessão válida.
)

# Exceções de CONVENIÊNCIA — documentação interativa do FastAPI.
# DÍVIDA TÉCNICA CONSCIENTE: revisar/fechar na Sprint 10.
# Ver SNAPSHOT_SPRINT_01_BLOCO5.md §8 e a consulta do sub-passo 5.8.1.
# Mantidas abertas no MVP-0 porque (a) o servidor é loopback-only
# (RNF-007), (b) o adversário A3 que leria isto já tem código na
# máquina, e (c) o ADR-001 §3 escolheu FastAPI em parte pela doc
# automática como ferramenta de aprendizado do operador.
# Para fechar na Sprint 10: basta apagar este bloco e a linha de união.
_PUBLIC_PREFIXES_DOCS = (
    "/docs",          # Swagger UI.
    "/redoc",         # ReDoc.
    "/openapi.json",  # esquema cru — /docs e /redoc dependem dele.
)

# União das duas: o que o middleware efetivamente trata como público.
_PUBLIC_PREFIXES = _PUBLIC_PREFIXES_ESSENCIAIS + _PUBLIC_PREFIXES_DOCS


def _is_public_path(path: str) -> bool:
    """
    True se o caminho da requisição é uma exceção pública.

    Casamento por prefixo: o caminho PRECISA começar com um dos
    prefixos conhecidos. `/static/app.css` casa com `/static/`;
    `/staticzinho` NÃO casa (o prefixo essencial tem a barra final
    justamente para isso). `/login` e `/setup` não levam barra final
    porque são caminhos exatos — não há nada legítimo "abaixo" deles,
    e `/login?error=1` casa poror `path` não incluir a query string.
    """
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


def _operator_exists() -> bool:
    """
    True se já existe ao menos um operador na tabela `users`.

    Abre a própria sessão de banco (curta, fechada no finally). Query
    mínima: SELECT id ... LIMIT 1 — só interessa existir ou não.

    IMPORTANTE: esta função só é chamada quando NÃO há cookie válido.
    Requisição já autenticada nunca chega aqui — o banco não é tocado
    no caminho quente. Foi a condição da decisão de fluxo B (5.8.1).

    Espelha a lógica de api/auth.py::_operator_exists deliberadamente
    em vez de importá-la: a função de lá é privada (`_`) e pertence à
    camada de rotas. Duplicar uma query de uma linha é mais honesto
    que acoplar o middleware à camada de API. Ver decisão 5.8.2,
    Opção 2.
    """
    db = SessionLocal()
    try:
        return db.execute(select(User.id).limit(1)).first() is not None
    finally:
        db.close()


async def auth_guard(request: Request, call_next):
    """
    Middleware de proteção. Registrado em app/main.py via
    app.middleware("http").

    Contrato:
    - Rota pública  -> segue para a aplicação, sem checagem.
    - Cookie válido -> segue, e expõe o user_id em request.state.user_id
      para uso futuro das rotas internas (sem precisar reverificar).
    - Cookie ausente/inválido + nenhum operador -> 303 para /setup.
    - Cookie ausente/inválido + operador existe  -> 303 para /login.

    Redirect 303 (See Other): o navegador refaz a requisição como GET,
    correto para "vá para a tela de login".
    """
    path = request.url.path

    # 1. Exceção pública: passa direto, nem olha cookie.
    if _is_public_path(path):
        return await call_next(request)

    # 2. Tem cookie de sessão? Está válido?
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is not None:
        try:
            user_id = verify_token(token)
        except InvalidTokenError:
            # Cookie presente mas inválido (expirado, adulterado,
            # malformado). Trata igual a "sem cookie" — cai no passo 3.
            # NÃO logamos a natureza da falha aqui: verify_token já é
            # deliberadamente genérico, e auditoria é o Bloco 7.
            pass
        else:
            # Cookie válido. Expõe o user_id para as rotas internas e
            # segue. ESTE é o caminho quente — nenhum acesso a banco.
            request.state.user_id = user_id
            return await call_next(request)

    # 3. Sem cookie válido. Decide o destino do redirect (fluxo B).
    #    Só agora o banco é consultado.
    if _operator_exists():
        destino = "/login"
    else:
        destino = "/setup"

    return RedirectResponse(url=destino, status_code=303)