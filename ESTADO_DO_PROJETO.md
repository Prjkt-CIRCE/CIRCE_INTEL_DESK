# ESTADO DO PROJETO — CIRCE Intel Desk
> Última atualização: 2026-06-23
> Sprint concluída: 01 — Bloco 8 (Cadastro, listagem, edição, arquivamento e detalhe de Casos — RF-001) — fechado no 8.7
> Em andamento: Sprint 01 — Bloco 9 (a declarar)
> Checkpoint: Bloco 8 COMPLETO (8.1 a 8.7). RF-001 funcionalmente fechado — backend (schemas + case_service + API REST, ADR-003a) e UI completa (listar, criar sem reload, ordenar, editar, arquivar + filtro, tela de detalhe). Fechamento 8.7 fez faxina de repositório, registrou decisões e reconciliou este documento. Próximo: declarar o Bloco 9.

---

## 1. Sprint atual e próxima

| Campo | Valor |
|---|---|
| Sprint em andamento | **Sprint 01 — Núcleo MVP-0** |
| Último commit | **`316bd6f`** — `feat(rf-001): tela de detalhe de caso (8.6) + atalho novo caso Ctrl+Alt+N` (o commit de fechamento 8.7 será criado em seguida) |
| Bloco CONCLUÍDO | **Bloco 8** — Casos (RF-001): listar, criar, editar, arquivar+filtro, detalhe |
| Sub-passo atual | **8.1 a 8.7 concluídos.** Bloco 8 fechado. Próximo: declarar **Bloco 9** |
| Status da Sprint 01 | **Em desenvolvimento** — Blocos 1–8 concluídos; RF-001 fechado. Faltam RF-002 (Pessoas), RF-003 (Vínculo Pessoa-Caso), RF-020 (tela de audit), e demais blocos da sprint |

> **Bloco 8 CONCLUÍDO.** RF-001 está funcionalmente completo: o operador cria,
> lista, ordena, edita, arquiva (com filtro de arquivados) e visualiza o detalhe
> de casos, com auditoria atômica (ADR-003a) em toda operação de escrita. Tudo
> commitado e pushado; repositório são nas duas máquinas (Casa/Trabalho).
>
> **Estado validado:** 13 testes commitados passando (5 audit + 8 case_service).
> Cadeia de auditoria íntegra (`python -m app.utils.audit_verify`). RF-001
> validado manualmente pelo operador no navegador em todos os sub-passos.

---

## 2. Histórico de sprints

| Sprint | Nome | Status | Commit(s) |
|---|---|---|---|
| 0 | Fundação técnica e ambiente | ✅ Concluída | `d907b17` |
| 0.5 | Shell visual e design system | ✅ Concluída | `e285d5f` |
| 0.6 Parte A | Git remoto e SSH — Casa | ✅ Concluída | incluído em 0.6 |
| 0.6 Parte B | Git remoto e SSH — Trabalho | ✅ Concluída | incluído em 0.6 |
| 01 Bloco 1 | Modelos de banco (User, Case, Person, Org, links) | ✅ Concluído | na Sprint 01 |
| 01 Bloco 2 | AuditLog model | ✅ Concluído | na Sprint 01 |
| 01 Bloco 3 | Migração Alembic inicial | ✅ Concluído | na Sprint 01 |
| 01 Bloco 4 | Schemas Pydantic | ✅ Concluído | na Sprint 01 |
| 01 Bloco 5 | Auth service + rotas de autenticação + middleware | ✅ Concluído | na Sprint 01 |
| 01 Bloco 6 | Sessão, expiração, inatividade, bloqueio, bruteforce | ✅ Concluído | `5268d0e` |
| 01 Bloco 7 | Audit log SHA-256 encadeado (ADR-003) | ✅ Concluído | `cc84893` |
| 01 Bloco 8 | Casos — RF-001 (listar, criar, editar, arquivar+filtro, detalhe) | ✅ Concluído (8.1–8.7) | `79c8f6a`, `1ef6a4f`, `048a91f`, `316bd6f` |
| 01 Bloco 9+ | A declarar (candidatos: RF-002 Pessoas, RF-003 Vínculos, RF-020 tela audit) | 🔲 Pendente | — |

---

## 3. Ambiente de desenvolvimento

| Item | Valor |
|---|---|
| Sistema operacional | Windows 11 Home |
| Terminal | PowerShell |
| Editor | VS Code |
| Pasta do projeto | `C:\Projetos\CIRCE_INTEL_DESK\` |
| Python principal | 3.12.10 (via `py -3.12`) |
| Python secundário | 3.14.4 (presente, não usado neste projeto) |
| Venv | `C:\Projetos\CIRCE_INTEL_DESK\.venv\` |
| **Banco real em uso** | **`data\circe.db`** ← ver D44 |

---

## 4. Comandos de retomada de sessão

```powershell
# 1. Navegar para a pasta do projeto
cd C:\Projetos\CIRCE_INTEL_DESK

# 2. Ativar o ambiente virtual
.venv\Scripts\Activate.ps1

# 3. Subir o servidor (opcional — só se for testar)
python run.py

# 4. Rodar os testes (verificação rápida — 13 commitados)
python -m pytest -v

# 5. Verificar cadeia de auditoria
python -m app.utils.audit_verify
```

---

## 5. Máquina de trabalho (segunda máquina)

| Item | Valor |
|---|---|
| Status | Configurada e sincronizada (Sprint 0.6 Parte B) |
| Chave SSH | `id_ed25519_circe_trabalho` com passphrase |
| Fingerprint | `SHA256:o0D4ryabgWKhqlUFcLcW87+PgTr1RfZsbPxoL2mjjQQ` |
| Observação | Venv e dependências devem ser reinstalados se não sincronizados desde a Sprint 0.6 |

---

## 6. Identidade Git

| Item | Valor |
|---|---|
| Conta GitHub | `Prjkt-CIRCE` (dedicada — D2) |
| Email Git | associado à conta Prjkt-CIRCE |
| Branch padrão | `main` |
| Remoto | `origin` — GitHub privado |
| 2FA | TOTP ativo (Google Authenticator, iPhone 13 Pro Max) |
| Último commit | `316bd6f` — `feat(rf-001): tela de detalhe de caso (8.6) + atalho novo caso Ctrl+Alt+N` (commit de fechamento 8.7 em seguida) |

### Chaves SSH registradas no GitHub

| Nome | Fingerprint | Máquina |
|---|---|---|
| Casa - 2026-05-09 | `SHA256:5BCkVPC4Xh5HoscE8q7HQ4g1Yb1KezFgFaoOaJ5tSSo` | Casa |
| Trabalho - 2026-05-11 | `SHA256:o0D4ryabgWKhqlUFcLcW87+PgTr1RfZsbPxoL2mjjQQ` | Trabalho |

---

## 7. Estado do código

Estrutura como deixada pelo fechamento do Bloco 8 (8.7). **RF-001 completo:**
backend (`79c8f6a`), tela de listagem+criação (`1ef6a4f`), edição+arquivamento
(`048a91f`), tela de detalhe + atalho Ctrl+Alt+N (`316bd6f`). Faxina de
fechamento no 8.7 (este staging): removidos `check_db.py`, `data/circe_intel.db`
e o placeholder inerte `cases.html`; criado `.gitattributes`; ADR-003a copiado
para `docs/adrs/`; input da command bar com `id`/`name`.

```
CIRCE_INTEL_DESK/
├── .gitignore
├── README.md
├── requirements.txt                        (pytest==8.3.4 adicionado no Bloco 7)
├── run.py                                  (host="127.0.0.1" hardcoded — D3)
├── app/
│   ├── __init__.py
│   ├── config.py                           (Pydantic Settings, SESSION_COOKIE_NAME)
│   ├── main.py                             (FastAPI: /static, Jinja2, /health, /api/info + router de cases — Bloco 8.3)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py                         (POST /setup, /login, /logout — com audit log completo)
│   │   └── cases.py                        (Bloco 8.3 — router REST /api/cases: GET, POST, GET/{id}, PATCH, DELETE)
│   ├── database/
│   │   ├── __init__.py
│   │   └── session.py                      (get_session — gerador SQLAlchemy)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── case.py                         (modelo Case — 15 colunas, VALIDADO no Bloco 8.1)
│   │   ├── person.py
│   │   ├── organization.py
│   │   ├── audit_log.py                    (AuditLog — previous_hash + record_hash)
│   │   └── links.py                        (tabelas de vínculo)
│   ├── modules/__init__.py
│   ├── schemas/
│   │   ├── auth.py                         (LoginRequest, SetupRequest)
│   │   └── cases.py                        (Bloco 8.2 — CaseCreate, CaseUpdate, CaseResponse)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audit_service.py                (Bloco 7 + flag manage_transaction do ADR-003a — Bloco 8.2)
│   │   ├── auth_service.py                 (hash_password, verify_password — Argon2id)
│   │   ├── bruteforce_service.py           (is_blocked, register_failure, register_success)
│   │   ├── case_service.py                 (Bloco 8.2 — generate_case_code, create/update/archive/get/list)
│   │   ├── session_service.py              (issue_token, decode_token)
│   │   └── settings_service.py            (get_value — tabela app_settings/settings)
│   ├── utils/
│   │   ├── __init__.py
│   │   └── audit_verify.py                 (Bloco 7 — CLI de verificação de cadeia)
│   └── web/
│       ├── __init__.py
│       ├── middleware.py                   (AuthMiddleware — protege rotas, popula request.state)
│       ├── routes.py                       (GET / + /cases funcional + placeholders restantes + /lock com log)
│       └── templates/
│           ├── base.html
│           ├── _header.html
│           ├── _status_bar.html
│           ├── _command_palette.html
│           ├── _shortcuts_modal.html
│           ├── _first_run.html
│           ├── auth/
│           │   ├── setup.html
│           │   ├── login.html
│           │   └── lock.html
│           ├── dev/components.html
│           ├── cases/
│           │   ├── list.html              (8.4/8.5 — listagem + modal criar/editar dual + arquivar)
│           │   └── detail.html            (8.6 — tela de detalhe SPA-leve via fetch)
│           └── placeholders/
│               ├── persons.html
│               ├── organizations.html
│               ├── documents.html
│               └── reports.html
│                                          (cases.html REMOVIDO no 8.7 — era inerte)
├── docs/adrs/
│   ├── ADR-003_IMUTABILIDADE_AUDIT_LOG.md
│   └── ADR-003a_AUDITORIA_ATOMICA.md      (copiado para o repo no 8.7 — D46 resolvido)
├── .gitattributes                         (8.7 — normaliza LF/CRLF)
├── tests/
│   ├── test_audit_chain.py                 (Bloco 7 — 5 testes, todos passando)
│   └── test_case_service.py                (Bloco 8.2 — 8 testes unit do service, todos passando)
└── data/                                   (NÃO versionado)
    ├── circe.db                            ← BANCO REAL EM USO (todas as tabelas)
    └── logs/
```

**Não versionado (correto):** `data/`, `.venv/`, `__pycache__/`, `*.db`, `*.log`, `.env`.

**Arquivos do Bloco 8 — UI de Casos** (commits `1ef6a4f`, `048a91f`, `316bd6f`):
- `app/web/templates/cases/list.html` — listagem + modal dual criar/editar + arquivar + filtro "arquivados" (8.4/8.5).
- `app/web/templates/cases/detail.html` — tela de detalhe SPA-leve (8.6): esqueleto §10.2, populado por fetch; zero CSS novo.
- `app/static/js/cases.js` — IIFE `window.CIRCE.cases`: lista (GET), cria/edita/arquiva sem reload, valida nome inline, ordena por cabeçalho, guarda de sessão expirada (401 **e** redirect/HTML→/login, D54). 8.6: botão "Abrir" navega ao detalhe; `loadCases(onLoaded?)`; `maybeOpenEditFromUrl` lê `?edit=id` (D56). Atalho "Novo caso" = **Ctrl+Alt+N** (revisão de D55).
- `app/static/js/case_detail.js` — IIFE de detalhe (8.6): busca `GET /api/cases/{id}`, popula slots `[data-field]`, trata 404 na shell, guarda D54, Esc volta, badge de status. Replica `formatDate`/`statusBadge` de cases.js (extração para util comum é pendência do RF-002).
- `app/static/js/toast.js` — IIFE `window.CIRCE.toast`: toast dinâmico (resolve pendência da 0.5), reusa classes `toast--*`.
- `app/web/routes.py` — `/cases` funcional + `GET /cases/{case_id:int}` (detalhe, 8.6).

### Tabela `cases` — confirmada no Bloco 8.1 (banco `data\circe.db`)

15 colunas, batendo com `05_MODELO_DE_DADOS.md` §3.2:

| # | Coluna | Tipo | NOT NULL |
|---|---|---|---|
| 0 | `id` | INTEGER | sim (PK autoincrement) |
| 1 | `case_code` | VARCHAR | sim (UNIQUE) |
| 2 | `name` | VARCHAR | sim |
| 3 | `description` | VARCHAR | não |
| 4 | `procedure_number` | VARCHAR | não |
| 5 | `fact_date` | VARCHAR | não |
| 6 | `unit` | VARCHAR | não |
| 7 | `responsible` | VARCHAR | não |
| 8 | `status` | VARCHAR | sim (default 'active' aplicado no modelo SQLAlchemy, não no schema do banco — ver D45) |
| 9 | `tags` | VARCHAR | não |
| 10 | `notes` | VARCHAR | não |
| 11 | `created_at` | VARCHAR | sim |
| 12 | `created_by` | INTEGER | não |
| 13 | `updated_at` | VARCHAR | não |
| 14 | `updated_by` | INTEGER | não |

Tabelas presentes em `circe.db`: `alembic_version`, `audit_logs`, `case_person_links`, `cases`, `persons`, `settings`, `users`.
Revisão Alembic atual (head): `b9387d80d7b1`.

---

## 8. Dependências instaladas (`requirements.txt`)

| Pacote | Versão |
|---|---|
| fastapi | 0.115.6 |
| uvicorn[standard] | 0.32.1 |
| sqlalchemy | 2.0.36 |
| alembic | 1.14.0 |
| argon2-cffi | 23.1.0 |
| jinja2 | 3.1.4 |
| pydantic | 2.10.3 |
| pydantic-settings | 2.7.0 |
| python-multipart | 0.0.20 |
| pytest | 8.3.4 |

---

## 9. Endpoints disponíveis

| Endpoint | Verbo | Tipo | Observação |
|---|---|---|---|
| `/` | GET | HTML | Shell autenticado |
| `/setup` | GET / POST | HTML / redirect | Só na primeira execução |
| `/login` | GET / POST | HTML / redirect | Autenticação |
| `/logout` | POST | redirect | Encerra sessão, loga evento |
| `/lock` | GET | HTML | Tela de bloqueio — loga lock_manual ou lock_inactivity |
| `/cases` | GET | HTML | Tela funcional (listagem + criação via /api/cases) — Bloco 8.4 |
| `/cases/{id}` | GET | HTML | Tela de detalhe (esqueleto + fetch /api/cases/{id}) — Bloco 8.6 |
| `/persons` | GET | HTML | Placeholder Sprint 01 |
| `/organizations` | GET | HTML | Placeholder Sprint 01-B |
| `/documents` | GET | HTML | Placeholder Sprint 02 |
| `/reports` | GET | HTML | Placeholder Sprint 03 |
| `/dev/components` | GET | HTML | Showcase design system |
| `/api/cases` | GET | JSON | Lista (query: include_archived, sort_by, descending) — Bloco 8.3 |
| `/api/cases` | POST | JSON | Cria caso; retorna 201 + case_code gerado — Bloco 8.3 |
| `/api/cases/{id}` | GET | JSON | Detalhe; 404 se não existe — Bloco 8.3 |
| `/api/cases/{id}` | PATCH | JSON | Edita (CaseUpdate) — Bloco 8.3 |
| `/api/cases/{id}` | DELETE | JSON | Arquivamento LÓGICO (status='archived') — Bloco 8.3 |
| `/health` | GET | JSON | `{"status":"ok"}` |
| `/api/info` | GET | JSON | Info da aplicação |
| `/static/*` | GET | — | CSS, JS, fontes |

> Todos os `/api/cases*` são protegidos pelo auth_guard (RF-021): não estão na
> allowlist pública, então exigem cookie de sessão válido. user_id vem de
> request.state.user_id (D30).

---

## 10. Controles de segurança em vigor

| Controle | Origem | Status |
|---|---|---|
| Loopback-only `127.0.0.1` (RNF-007 / A3) | `run.py` hardcoded | ✅ Ativo desde Sprint 0 |
| Separação código vs. dados operacionais | `.gitignore` + `git ls-tree` validado | ✅ Sprint 0.6 |
| 2FA TOTP na conta GitHub | Google Authenticator | ✅ Sprint 0.6 |
| Chave SSH com passphrase — Casa | `id_ed25519` | ✅ Sprint 0.6 |
| Chave SSH com passphrase — Trabalho | `id_ed25519_circe_trabalho` | ✅ Sprint 0.6 |
| Senha Argon2id (RS-005) | `auth_service.hash_password` | ✅ Sprint 01 Bloco 5 |
| Middleware de autenticação | `app/web/middleware.py` | ✅ Sprint 01 Bloco 5 |
| Bloqueio por inatividade (RS-007) | `inactivity_lock.js` + `/lock` | ✅ Sprint 01 Bloco 6 |
| Bruteforce mitigation (CA-021.5) | `bruteforce_service` | ✅ Sprint 01 Bloco 6 |
| Expiração de sessão 8h (CA-021.6) | `session_service` + `settings_service` | ✅ Sprint 01 Bloco 6 |
| Audit log SHA-256 encadeado (RS-008 / ADR-003) | `audit_service` | ✅ Sprint 01 Bloco 7 |
| Auditoria atômica de operações de domínio (ADR-003a) | `case_service` + `log_action(manage_transaction=False)` | ✅ Sprint 01 Bloco 8.2 |
| Arquivamento lógico de casos (nunca exclusão física) | `case_service.archive_case` | ✅ Sprint 01 Bloco 8.2 |
| Hash SHA-256 em arquivos importados (RS-001) | — | 🔲 Sprint 02 |
| SQLCipher (ADR-002) | — | 🔲 Sprint 10 |
| Backup criptografado (RS-009) | — | 🔲 Sprint 10 |

---

## 11. Decisões tomadas

### Sprint 0 (D1–D5)

**D1 — Python 3.12 em vez de 3.14.**
3.12.10 instalado lado-a-lado. Razão: cobertura de wheels para bibliotecas pesadas das Sprints 04, 05, 08.

**D2 — Conta GitHub dedicada `Prjkt-CIRCE`.**
Compartimentação operacional (premissa 8 do `01_SPEC_MASTER.md`).

**D3 — `host="127.0.0.1"` hardcoded em `run.py`.**
RNF-007 / A3. Não configurável via UI ou variável de ambiente.

**D4 — Documentos de fundação fora do Git.**
Resolvida como D7.

**D5 — `--global` para identidade Git.**
Aceitável para operador único com projetos próprios na mesma máquina.

### Sprint 0.5 (D6)

**D6 — Preferências de UI em `localStorage` na Sprint 0.5.**
Migração para banco (`users.preferences`) prevista na Sprint 01, mantendo `localStorage` como cache.

### Sprint 0.6 (D7–D10)

**D7 — Documentos de fundação fora do Git.**
Vivem nos arquivos do Project do Claude. Não versionados.

**D8 — Branch `main` como padrão.**
Padrão GitHub atual.

**D9 — `config.py` como fonte única do `SESSION_COOKIE_NAME`.**
Middleware e auth precisam do mesmo valor — constante de módulo em `config.py`.

**D10 — BOM em arquivos `~\.ssh\config` no Windows.**
Usar `New-Object System.Text.UTF8Encoding $false` em PowerShell para evitar BOM silencioso.

### Sprint 01 Blocos 1–6 (D11–D37)

*(Registrados em versões anteriores — resumo dos mais relevantes para o próximo bloco):*

**D11 — `settings_service.get_value()` como fonte de configurações operacionais.**
`session_hours`, `inactivity_lock_minutes` lidos daí. Editáveis via UI no Bloco 11.

**D17 — Invalidação de token server-side desnecessária no MVP-0.**
Single-user local. Cookie apagado é suficiente. Blocklist entra só se multi-usuário vier.

**D30 — `request.state.user_id` populado pelo middleware.**
Todas as rotas autenticadas têm acesso a `user_id` sem consulta extra ao banco.

**D33 — Timer de inatividade: valor 0 = "nunca bloquear".**
JS trata 0 como flag de desligado.

**D34 — Mensagem de bloqueio por bruteforce só para usernames que existem.**
Não vaza enumeração porque confirmar existência não agrega informação ao atacante neste ponto.

**D36 — Rota `/lock` protegida pelo middleware.**
Operador sem sessão válida não acessa `/lock` diretamente.

### Sprint 01 Bloco 7 (D38–D43)

**D38 — `login_failed` com `metadata={"reason": "unknown_user"|"wrong_password"|"account_disabled"}`.**
Ação única para todos os tipos de falha; motivo técnico vai no metadata, não na mensagem ao usuário.

**D39 — JS adiciona `?reason=auto|manual` ao redirect para `/lock`.**
Servidor lê e registra `lock_inactivity` ou `lock_manual` conforme o valor.

**D40 — `lock_manual` entra no Bloco 7.**
CA-021.9 fala em "bloqueios" plural. `04_SEGURANCA.md` §7.2 precisa ser atualizado no Bloco 12 para listar "Bloqueio manual".

**D41 — Chamada `log_action()` para locks fica direto em `routes.py` (rota `/lock`).**
Middleware já expõe `request.state.user_id` (D30).

**D42 — Escopo do Bloco 7 fechado:**
DENTRO: `audit_service`, `audit_verify.py`, refactor dos TODO(bloco-7) em `api/auth.py`, eventos setup/login/login_failed/login_blocked/logout/lock_inactivity/lock_manual.
FORA: tela `/audit` (Bloco 11), `audit_view` recursivo (Bloco 11), endpoint HTTP para `verify_chain` (ADR-003 §2.7 explícito).

**D43 — `pytest==8.3.4` adicionado ao `requirements.txt`.**
Executado via `python -m pytest` (não `pytest` direto — PATH do Windows não inclui o binário do venv).

### Sprint 01 Bloco 8 — Sub-passo 8.1 (D44–D45)

**D44 — Nome real do banco é `data\circe.db`, não `circe_intel.db`.**
Descoberto no 8.1: existiam dois arquivos `.db` em `data/`. O banco real, com todas as tabelas e migrações aplicadas (head `b9387d80d7b1`), é `circe.db`. O arquivo `circe_intel.db` estava VAZIO (zero tabelas) e era órfão — provável resíduo de teste ou tentativa antiga. RESOLVIDO no 8.7: `data\circe_intel.db` apagado. As versões anteriores deste documento registravam o nome errado.

**D45 — Default de `status` em `cases` vive na camada SQLAlchemy, não no schema do banco.**
A coluna `status` tem `NOT NULL` no banco mas sem `DEFAULT` no DDL aplicado. O default `'active'` é aplicado pelo modelo Python. Sem risco prático: o `case_service` sempre passará `status='active'` explicitamente na criação. Registrado para não surpreender em depuração futura.

### Sprint 01 Bloco 8 — Sub-passos 8.2 e 8.3 (D46–D50)

**D46 — ADR-003a (auditoria atômica de operações que criam entidades).**
`audit_service.log_action` ganhou o parâmetro keyword-only `manage_transaction: bool = True`.
Com `True` (padrão), abre `BEGIN IMMEDIATE` como no Bloco 7 (comportamento intacto para login/logout/lock).
Com `False`, não abre a transação — o chamador (serviço de domínio) controla. Motivo: criar entidade
e auditar na mesma transação era impossível com o log abrindo o BEGIN por dentro, porque o `flush` da
entidade (necessário para materializar `entity_id`, que entra no hash) já abria transação implícita →
erro "cannot start a transaction within a transaction". Retrocompatível por construção (default preserva
o Bloco 7; os 5 testes de audit seguem verdes). ADR-003a vive nos arquivos do Project; cópia para
`docs/adrs/` é pendência de fechamento do bloco.

**D47 — Contrato de transação dos serviços de domínio.**
Padrão obrigatório para operações que criam/alteram entidades (vale para todos os RFs seguintes —
pessoa, organização, vínculos):
`db.execute(text("BEGIN IMMEDIATE"))` → `db.add(obj); db.flush()` →
`audit_service.log_action(..., manage_transaction=False)` → `db.commit()`.
Falha em qualquer ponto → rollback de entidade e log juntos. Não há ação não-logada.

**D48 — `case_code` imutável; `status` fora do update genérico.**
`CaseUpdate` não aceita `case_code` (imutável após criação) nem `status` (muda apenas via `archive_case`).

**D49 — Idempotência em update/archive não gera log.**
Editar com valores idênticos aos atuais, ou arquivar um caso já arquivado, NÃO gera registro de
auditoria — não há mudança real a auditar. Evita poluir a cadeia com eventos vazios.

**D50 — Strings de `action` canônicas para casos.**
`case_create`, `case_update`, `case_archive` — confirmadas contra o enum oficial do
`05_MODELO_DE_DADOS.md` §6.4. Contrato do hash (ADR-003 §3.2): não renomear depois de gravadas na cadeia.

### Sprint 01 Bloco 8 — Sub-passo 8.4 (D51–D55)

**D51 — Coluna de data exibida na lista de casos: `created_at` ("Criado em").**
Decisão do operador. `updated_at` fica reservado para a tela de detalhe/edição (8.5/8.6).
A ordenação por cabeçalho ainda permite ordenar por qualquer um dos campos aceitos pela API
(`case_code`, `name`, `created_at`, `status`).

**D52 — Escopo do 8.4 = listar + criar (sem reload). Editar e arquivar+filtro ficam no 8.5.**
Decisão do operador, alinhada ao plano §13. Resolve conflito da nota de retomada (que dizia
"criar+listar+arquivar"): vale o §13. CA-001.1/.2/.3/.6/.7 fechados no 8.4; CA-001.4 (editar)
e CA-001.5 (arquivar+filtro) reservados para o 8.5.

**D53 — Helper de toast dinâmico criado agora (`app/static/js/toast.js`, `window.CIRCE.toast`).**
Resolve a pendência da Sprint 0.5 (showcase só tinha markup estático). Reusa as classes
`toast--{success,warning,error,info}` de components.css — zero CSS novo. Erros não expiram
sozinhos (§8.7); demais variantes somem em 4s. Carregado por tela via `extra_body`, não no shell global.

**D54 — Guarda de sessão expirada no fetch trata DOIS caminhos.**
O `cases.js` detecta tanto `401 JSON` (rede de segurança do endpoint, D30) quanto
`redirect/HTML` (middleware auth_guard → /login). Em qualquer um, redireciona para
`/login?next=<rota-atual>`. Defensivo por construção: não quebra se o comportamento da
camada mudar. (Atende ao ponto de atenção técnico mapeado para o 8.4.)

**D55 — Ação `cases.new` ("Novo caso") registrada na command palette + atalho Ctrl+N.**
`cases.js` chama `window.CIRCE.palette.register(...)` no setup. Ctrl+N abre o modal "Novo caso"
quando na tela de casos e o palette não está aberto — ativa o atalho que estava marcado como
pendente no modal de atalhos da 0.5.
**REVISÃO (8.6): Ctrl+N → Ctrl+Alt+N.** Ctrl+N é reservado pelo navegador (nova janela) e
disparado antes do JS; `preventDefault()` não o segura numa aba normal. Alt+N puro não dispara
em teclado ABNT2/pt-BR (AltGr). Ctrl+Alt+N funciona e foi validado pelo operador. O handler usa
a condição `(e.altKey && !e.metaKey && tecla==='n')`. Textos atualizados em `list.html` (estado
vazio) e `_shortcuts_modal.html` (tabela de atalhos). ALERTA: o Ctrl+P previsto para "Nova pessoa"
(RF-002) terá o mesmo problema (é o "imprimir" do navegador) — usar Ctrl+Alt+P por coerência.

### Sprint 01 Bloco 8 — Sub-passos 8.5 e 8.6 (D56)

**D56 — "Editar" a partir da tela de detalhe navega para `/cases?edit={id}`.**
Em vez de refatorar o `cases.js` fechado/validado no 8.5 para reusar o modal de edição na tela
de detalhe, o botão "Editar" do detalhe leva à lista com o parâmetro `?edit={id}`. O `cases.js`
detecta esse parâmetro no `setup()` (após `loadCases`), abre o modal de edição já no caso certo,
e limpa o parâmetro da URL via `history.replaceState` (evita reabrir no F5). Caso fora da lista
carregada (ex.: arquivado com filtro desligado) é buscado por `GET /api/cases/{id}` como fallback.
Decisão de menor risco: não reabre código validado para ganho marginal. A extração do modal e dos
utilitários (`formatDate`, `statusBadge`) para um módulo compartilhado fica para quando o RF-002
(Pessoas) pedir o mesmo padrão — aí a abstração se paga por servir a vários consumidores.

Decisões de design do 8.6 (a):(c):(d), registradas: (a) detalhe renderizado por fetch SPA-leve,
coerente com 8.4/8.5; (c) "Reativar" caso arquivado fica FORA do escopo — conflita com D48
(status fora do CaseUpdate; não há endpoint de reativação); deve ser desenhado em sub-passo/ADR
próprio antes de implementar; (d) Esc volta à lista, link "< CASOS" no topo do detalhe.

---

## 12. Pendências conhecidas

| Pendência | Origem | Sprint para resolver |
|---|---|---|
| Declarar o Bloco 9 da Sprint 01 (candidatos: RF-002 Pessoas, RF-003 Vínculos, RF-020 tela audit) | Bloco 8 fechado | Sprint 01 (próxima sessão) |
| Handler 404 global com a shell (hoje `/cases/abc` cai no JSON cru do FastAPI) — operador classificou como ACEITÁVEL; não é fluxo real | Bloco 8.6 | Quando conveniente |
| Extrair `formatDate`/`statusBadge` + modal de caso para módulo compartilhado | Bloco 8.6 (D56) | RF-002 (quando pedir o mesmo padrão) |
| Atalho `Ctrl+P` para "Nova pessoa" terá o mesmo problema do Ctrl+N — usar `Ctrl+Alt+P` | Revisão D55 | RF-002 (Pessoas) |
| Decidir se versiona teste de API definitivo (TestClient) | Bloco 8.3 | Quando conveniente |
| `04_SEGURANCA.md` §7.2 — adicionar "Bloqueio manual" à lista | D40 | Bloco 12 da Sprint 01 |
| ADR-004 (PDF de relatório) | Backlog | 03 |
| ADR-005 (pipeline OCR) | Backlog | 04 |
| ADR-006 (motor de transcrição) | Backlog | 05 |
| ADR-007 (reconhecimento facial) | Backlog | 08 |
| ADR-008 (backup criptografado) | Backlog | 10 |
| ADR-009 (workbench com tiling) — Proposed | Inspiração externa | 03–05 |
| ADR-010 (workspaces nomeados) — Proposed | Inspiração externa | 03–05 |
| ADR novo — motor de mapa offline | Ideia I1 | antes da Sprint 03.5 |
| ADR novo — dados sob sigilo judicial | Ideia I5 | antes da Sprint 02.5 |
| Tela `/audit` (CA-020.3, CA-020.5) | Sprint 01 | Bloco 11 |
| Endpoint HTTP para `verify_chain` | ADR-003 §2.7 — explicitamente fora do MVP-0 | Sprint 10 ou posterior |
| Iconografia (Phosphor / Lucide) | Sprint 0.5 | Sprint 01 |
| Densidade configurável (seletor UI) | Sprint 0.5 | Sprint 01 |
| Migração `localStorage` → banco para preferências UI | D6 | Sprint 01 |

**Resolvidas no fechamento do Bloco 8 (8.7):** apagado `check_db.py`; apagado
`data/circe_intel.db` órfão (D44); criado `.gitattributes` (warnings LF/CRLF);
ADR-003a copiado para `docs/adrs/` (D46); removido placeholder inerte
`cases.html`; input da command bar com `id`/`name`; toasts dinâmicos resolvidos
no 8.4 (D53).

### Novas sprints propostas

| Sprint | Conteúdo | Posição |
|---|---|---|
| Sprint 02.5 | Dados financeiros estruturados (RIF, quebra de sigilo) | após Sprint 02 |
| Sprint 03.5 | Georreferenciamento operacional | após Sprint 03 |
| Sprint 03.6 | Denúncia anônima georreferenciada | após Sprint 03.5 |

---

## 13. Plano do Bloco 8 (aprovado, em execução)

**Requisito:** RF-001 — Cadastro de Caso.
**CAs alvo:** CA-001.1 a CA-001.7.

**Arquivos a criar:**
- `app/api/cases.py` — endpoints REST (GET lista, POST cria, PATCH edita, DELETE arquiva)
- `app/services/case_service.py` — regras: geração de `case_code` `{ano}-{NNNN}`, validações, auditoria
- `app/schemas/cases.py` — `CaseCreate`, `CaseUpdate`, `CaseResponse`
- `app/web/templates/cases/list.html` — listagem
- `app/web/templates/cases/detail.html` — detalhe
- `app/web/templates/cases/_modal_form.html` — modal criar/editar
- `app/static/js/cases.js` — chamadas à API, atualização sem reload, validação inline

**Arquivos a alterar:**
- `app/main.py` — registrar router de cases
- `app/web/routes.py` — `/cases` aponta para tela funcional
- `app/models/__init__.py` — garantir export de `Case`

**Sub-passos (um por vez, com confirmação entre eles):**
- **8.1 — Verificação de banco e modelo** → ✅ CONCLUÍDO
- **8.2 — Schemas Pydantic + `case_service`** (geração de código, validações, auditoria atômica via ADR-003a) → ✅ CONCLUÍDO E COMMITADO (`79c8f6a`)
- **8.3 — Endpoints REST + registro no `main.py`** → ✅ CONCLUÍDO E COMMITADO (`79c8f6a`)
- 8.4 — Tela de listagem + modal de criação (criação funcional sem reload) → ✅ CONCLUÍDO E COMMITADO (`1ef6a4f`)
- 8.5 — Edição + arquivamento + filtro "arquivados" → ✅ CONCLUÍDO E COMMITADO (`048a91f`)
- 8.6 — Tela de detalhe (SPA-leve via fetch) + atalho Ctrl+Alt+N → ✅ CONCLUÍDO E COMMITADO (`316bd6f`)
- 8.7 — Faxina de repositório + registro de decisões + reconciliação deste documento + fechamento → ✅ EM CONCLUSÃO (esta sessão)

**BLOCO 8 CONCLUÍDO.** RF-001 funcionalmente completo e validado. Ver §5 (relatório
de fechamento) abaixo.

**Antes de escrever o 8.4, o próximo Claude DEVE pedir ao operador o conteúdo de:**
- `app/web/routes.py` (a rota `/cases` que será despromovida de placeholder)
- `app/web/templates/base.html` (shell — herança Jinja, blocks)
- `app/web/templates/placeholders/cases.html` (placeholder atual — padrão de cabeçalho)
- `app/web/templates/dev/components.html` (showcase — classes canônicas do design system)
- `app/web/templates/_command_palette.html` OU `_shortcuts_modal.html` (ÚNICO ainda não visto — necessário para o modal "Novo caso" seguir o padrão `data-open`)
- `app/static/js/command_palette.js` e `first_run.js` (padrão de JS da casa)

Não inventar classes CSS, estrutura de template nem padrão de JS. Os componentes
(btn, input, field, table, badge, toast) já existem no showcase — reusar, não recriar.
Ler antes de escrever.

**Ponto de atenção do 8.4:** o auth_guard responde sessão expirada com redirect 303 → /login
(desenhado para navegador). O `cases.js` consome `/api/cases` por fetch e PRECISA detectar quando
recebeu redirect/HTML de login em vez de JSON, e mandar o operador para /login em vez de quebrar.

---

## 14. Como atualizar este documento

Ao final de cada bloco significativo ou sprint:

1. Atualizar seção 1 (sprint/bloco atual e próximo).
2. Adicionar linha à seção 2 (histórico).
3. Atualizar seções 3–5 se houve mudança de ambiente ou máquina.
4. Atualizar seção 6 (identidade Git — último commit).
5. Atualizar seção 7 (estado do código — arquivos novos).
6. Atualizar seção 8 (dependências) se versão mudou.
7. Atualizar seção 9 (endpoints) se foi adicionado/alterado.
8. Atualizar seção 10 (controles de segurança).
9. Adicionar decisões à seção 11 (numeração contínua).
10. Atualizar seção 12 (pendências — remover resolvidas, adicionar novas).
11. Mudar data no topo.
12. Baixar e substituir nos arquivos do Project do Claude.
