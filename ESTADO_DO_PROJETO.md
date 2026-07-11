ESTADO DO PROJETO — CIRCE Intel Desk

Última atualização: 2026-07-11
Sprint concluída: 01 — Bloco 10 (RF-003 Vínculo Pessoa-Caso — completo e commitado — 9967520)
Em andamento: Sprint 01 — Bloco 11 (a declarar)
Checkpoint: Blocos 1–10 COMPLETOS. RF-001 (Casos), RF-002 (Pessoas) e RF-003 (Vínculo
Pessoa-Caso) funcionalmente fechados. Próximo: declarar o Bloco 11.


1. Sprint atual e próxima
Campo                   Valor
Sprint em andamento     Sprint 01 — Núcleo MVP-0
Último commit           9967520 — feat(RF-003): vinculo pessoa-caso - servico, endpoints, UI caso e pessoa
Bloco CONCLUÍDO         Bloco 10 — RF-003 Vínculo Pessoa-Caso
Sub-passo atual         10.1 a 10.7 concluídos. Bloco 10 fechado. Próximo: declarar Bloco 11
Status da Sprint 01     Em desenvolvimento — Blocos 1–10 concluídos; RF-001, RF-002, RF-003 fechados.
                        Faltam RF-020 (tela audit), Bloco 11 (logout, settings, fix D35) e demais blocos.


2. Histórico de sprints
Sprint          Nome                                                            Status              Commit(s)
0               Fundação técnica e ambiente                                     ✅ Concluída         d907b17
0.5             Shell visual e design system                                    ✅ Concluída         e285d5f
0.6 Parte A     Git remoto e SSH — Casa                                         ✅ Concluída         incluído em 0.6
0.6 Parte B     Git remoto e SSH — Trabalho                                     ✅ Concluída         incluído em 0.6
01 Bloco 1      Modelos de banco (User, Case, Person, Org, links)               ✅ Concluída         na Sprint 01
01 Bloco 2      AuditLog model                                                  ✅ Concluída         na Sprint 01
01 Bloco 3      Migração Alembic inicial                                        ✅ Concluída         na Sprint 01
01 Bloco 4      Schemas Pydantic                                                ✅ Concluída         na Sprint 01
01 Bloco 5      Auth service + rotas de autenticação + middleware               ✅ Concluída         na Sprint 01
01 Bloco 6      Sessão, expiração, inatividade, bloqueio, bruteforce            ✅ Concluído         5268d0e
01 Bloco 7      Audit log SHA-256 encadeado (ADR-003)                           ✅ Concluído         cc84893
01 Bloco 8      Casos — RF-001 (listar, criar, editar, arquivar, detalhe)       ✅ Concluído         79c8f6a, 1ef6a4f, 048a91f, 316bd6f
01 Bloco 9      Pessoas — RF-002 (listar, criar, editar, arquivar, detalhe)     ✅ Concluído         4b151fa
01 Bloco 10     Vínculo Pessoa-Caso — RF-003                                    ✅ Concluído         9967520
01 Bloco 11     Logout, settings screen, fix D35 (a declarar)                  🔲 Pendente          —
01 Bloco 12     Fechamento Sprint 01 (síntese)                                  🔲 Pendente          —


3. Ambiente de desenvolvimento
Item                    Valor
Sistema operacional     Windows 11 Home
Terminal                PowerShell
Editor                  VS Code
Pasta do projeto        C:\Projetos\CIRCE_INTEL_DESK\
Python principal        3.12.10 (via py -3.12)
Venv                    C:\Projetos\CIRCE_INTEL_DESK\.venv\
Banco real em uso       data\circe.db ← ver D44


4. Comandos de retomada de sessão
# 1. Navegar para a pasta do projeto
cd C:\Projetos\CIRCE_INTEL_DESK

# 2. Ativar o ambiente virtual
.venv\Scripts\Activate.ps1

# 3. Subir o servidor (opcional — só se for testar)
python run.py

# 4. Rodar os testes (verificação rápida — 43 testes)
python -m pytest -v

# 5. Verificar cadeia de auditoria
python -m app.utils.audit_verify


5. Máquina de trabalho (segunda máquina)
Item            Valor
Status          Configurada e sincronizada (Sprint 0.6 Parte B)
Chave SSH       id_ed25519_circe_trabalho com passphrase
Fingerprint     SHA256:o0D4ryabgWKhqlUFcLcW87+PgTr1RfZsbPxoL2mjjQQ
Observação      Venv e dependências devem ser reinstalados se não sincronizados desde a Sprint 0.6


6. Identidade Git
Item            Valor
Conta GitHub    Prjkt-CIRCE (dedicada — D2)
Branch padrão   main
Remoto          origin — GitHub privado
2FA             TOTP ativo (Google Authenticator)
Último commit   9967520 — feat(RF-003): vinculo pessoa-caso

Chaves SSH registradas no GitHub
Nome                        Fingerprint                                         Máquina
Casa - 2026-05-09           SHA256:5BCkVPC4Xh5HoscE8q7HQ4g1Yb1KezFgFaoOaJ5tSSo Casa
Trabalho - 2026-05-11       SHA256:o0D4ryabgWKhqlUFcLcW87+PgTr1RfZsbPxoL2mjjQQ Trabalho


7. Estado do código
Estrutura atualizada após o Bloco 10 (commit 9967520):

CIRCE_INTEL_DESK/
├── .gitignore
├── .gitattributes
├── README.md
├── requirements.txt
├── run.py                                      (host="127.0.0.1" hardcoded — D3)
├── app/
│   ├── main.py                                 (registra cases, persons, links routers)
│   ├── api/
│   │   ├── auth.py
│   │   ├── cases.py                            (RF-001 — Bloco 8.3)
│   │   ├── persons.py                          (RF-002 — Bloco 9.4)
│   │   └── links.py                            (RF-003 — Bloco 10.4: GET/POST/DELETE /api/links/person-case)
│   ├── database/
│   │   └── session.py
│   ├── models/
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── case.py
│   │   ├── person.py
│   │   ├── case_person_link.py                 (Bloco 1 — exercitado no Bloco 10)
│   │   ├── audit_log.py
│   │   └── setting.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── cases.py
│   │   ├── persons.py                          (RF-002 — Bloco 9.2)
│   │   └── links.py                            (RF-003 — Bloco 10.4: PersonCaseLinkCreate + PersonCaseLinkResponse)
│   ├── services/
│   │   ├── audit_service.py
│   │   ├── auth_service.py
│   │   ├── bruteforce_service.py
│   │   ├── case_service.py
│   │   ├── person_service.py                   (RF-002 — Bloco 9.2)
│   │   ├── link_service.py                     (RF-003 — Bloco 10.2)
│   │   ├── session_service.py
│   │   └── settings_service.py
│   ├── utils/
│   │   └── audit_verify.py
│   └── web/
│       ├── middleware.py
│       ├── routes.py
│       └── templates/
│           ├── base.html
│           ├── cases/
│           │   ├── list.html                   (RF-001 — Bloco 8.4/8.5)
│           │   └── detail.html                 (RF-001 Bloco 8.6 + RF-003 Bloco 10.5 — seção vínculos + modal)
│           ├── persons/
│           │   ├── list.html                   (RF-002 — Bloco 9.5/9.6... via persons.js)
│           │   └── detail.html                 (RF-002 Bloco 9.6 + RF-003 Bloco 10.6 — seção vínculos + modal)
│           └── placeholders/
│               ├── organizations.html
│               ├── documents.html
│               └── reports.html
├── app/static/js/
│   ├── accent.js
│   ├── case_detail.js                          (RF-001 Bloco 8.6 + RF-003 Bloco 10.5)
│   ├── cases.js                                (RF-001 Bloco 8.4/8.5)
│   ├── command_palette.js
│   ├── first_run.js
│   ├── header_toggles.js
│   ├── inactivity_lock.js
│   ├── person_detail.js                        (RF-002 Bloco 9.6 + RF-003 Bloco 10.6)
│   ├── persons.js                              (RF-002 Bloco 9.5)
│   ├── shortcuts.js
│   ├── status_bar.js
│   ├── theme.js
│   └── toast.js
├── docs/adrs/
│   ├── ADR-003_IMUTABILIDADE_AUDIT_LOG.md
│   └── ADR-003a_AUDITORIA_ATOMICA.md
├── tests/
│   ├── test_audit_chain.py                     (5 testes — Bloco 7)
│   ├── test_case_service.py                    (8 testes — Bloco 8.2)
│   ├── test_person_service.py                  (12 testes — Bloco 9.2)
│   └── test_link_service.py                    (18 testes — Bloco 10.3)
└── data/                                       (NÃO versionado)
    └── circe.db


8. Dependências instaladas (requirements.txt)
Pacote                  Versão
fastapi                 0.115.6
uvicorn[standard]       0.32.1
sqlalchemy              2.0.36
alembic                 1.14.0
argon2-cffi             23.1.0
jinja2                  3.1.4
pydantic                2.10.3
pydantic-settings       2.7.0
python-multipart        0.0.20
pytest                  8.3.4


9. Endpoints disponíveis
Endpoint                        Verbo           Tipo        Observação
/                               GET             HTML        Shell autenticado
/setup                          GET / POST      HTML        Só na primeira execução
/login                          GET / POST      HTML        Autenticação
/logout                         POST            redirect    Encerra sessão
/lock                           GET             HTML        Tela de bloqueio
/cases                          GET             HTML        Listagem + criação (RF-001)
/cases/{id}                     GET             HTML        Detalhe + vínculos (RF-001, RF-003)
/persons                        GET             HTML        Listagem + criação (RF-002)
/persons/{id}                   GET             HTML        Detalhe + vínculos (RF-002, RF-003)
/organizations                  GET             HTML        Placeholder
/documents                      GET             HTML        Placeholder
/reports                        GET             HTML        Placeholder
/dev/components                 GET             HTML        Showcase design system
/api/cases                      GET             JSON        Lista (include_archived, sort_by, descending)
/api/cases                      POST            JSON        Cria caso; retorna 201
/api/cases/{id}                 GET             JSON        Detalhe; 404 se não existe
/api/cases/{id}                 PATCH           JSON        Edita (CaseUpdate)
/api/cases/{id}                 DELETE          JSON        Arquivamento LÓGICO
/api/persons                    GET             JSON        Lista (include_archived, sort_by, descending)
/api/persons                    POST            JSON        Cria pessoa; retorna 201; 409 se CPF dup.
/api/persons/{id}               GET             JSON        Detalhe; 404 se não existe
/api/persons/{id}               PATCH           JSON        Edita (PersonUpdate); 409 se CPF dup.
/api/persons/{id}               DELETE          JSON        Arquivamento LÓGICO
/api/links/person-case          GET             JSON        Lista vínculos (case_id OU person_id)
/api/links/person-case          POST            JSON        Cria vínculo; 201; 409 se dup.
/api/links/person-case/{id}     DELETE          JSON        Remoção LÓGICA (active=0)
/health                         GET             JSON        {"status":"ok"}
/api/info                       GET             JSON        Info da aplicação


10. Controles de segurança em vigor
Controle                                        Origem                                          Status
Loopback-only 127.0.0.1 (RNF-007 / A3)         run.py hardcoded                                ✅ Ativo desde Sprint 0
Separação código vs. dados operacionais         .gitignore + git ls-tree validado               ✅ Sprint 0.6
2FA TOTP na conta GitHub                        Google Authenticator                            ✅ Sprint 0.6
Chave SSH com passphrase — Casa                 id_ed25519                                      ✅ Sprint 0.6
Chave SSH com passphrase — Trabalho             id_ed25519_circe_trabalho                       ✅ Sprint 0.6
Senha Argon2id (RS-005)                         auth_service.hash_password                      ✅ Sprint 01 Bloco 5
Middleware de autenticação                      app/web/middleware.py                           ✅ Sprint 01 Bloco 5
Bloqueio por inatividade (RS-007)               inactivity_lock.js + /lock                      ✅ Sprint 01 Bloco 6
Bruteforce mitigation (CA-021.5)                bruteforce_service                              ✅ Sprint 01 Bloco 6
Expiração de sessão 8h (CA-021.6)               session_service + settings_service              ✅ Sprint 01 Bloco 6
Audit log SHA-256 encadeado (RS-008 / ADR-003)  audit_service                                   ✅ Sprint 01 Bloco 7
Auditoria atômica de domínio (ADR-003a)         case/person/link_service                        ✅ Sprint 01 Blocos 8–10
Arquivamento lógico (nunca exclusão física)     archive_case, archive_person                    ✅ Sprint 01 Blocos 8–9
Remoção lógica de vínculos (active=0)           link_service.remove_link                        ✅ Sprint 01 Bloco 10
Hash SHA-256 em arquivos importados (RS-001)    —                                               🔲 Sprint 02
SQLCipher (ADR-002)                             —                                               🔲 Sprint 10
Backup criptografado (RS-009)                   —                                               🔲 Sprint 10


11. Decisões tomadas
(D1–D56 registradas em versões anteriores — mantidas por referência; novas decisões abaixo)

Sprint 01 Bloco 9 — RF-002 Pessoas (D57–D60)
D57 — DuplicateCPFError carrega id e nome da pessoa existente.
Levantada por create_person e update_person quando o CPF normalizado já pertence a outra
pessoa (CA-002.5). A API converte em HTTP 409 com existing_person_id e existing_person_name,
para a UI oferecer "abrir pessoa existente" em vez de erro genérico. A checagem roda dentro
do BEGIN IMMEDIATE, cobrindo corrida teórica (mesmo raciocínio de generate_case_code).
D58 — "Editar" a partir da tela de detalhe da Pessoa navega para /persons?edit={id}.
Espelho de D56 (Casos). Evita refatorar o persons.js fechado/validado.
D59 — Tela de detalhe de Pessoa: estrutura completa de seções conforme mockup operacional.
Seções cujos dados dependem de módulos futuros exibem "Nenhum registro cadastrado." —
sem dado falso, sem número sem lastro. Score de Ameaça (RF-023) reservado como bloco visual
com texto "módulo pendente".
D60 — Ordem das seções na tela de detalhe de Pessoa (hierarquia operacional):
identificação → score (RF-023) → dados pessoais → sinais particulares → vínculo faccional →
álbum → boletins → processos → prisões → medidas → vínculos → fonte → notas → auditoria.

Sprint 01 Bloco 10 — RF-003 Vínculo Pessoa-Caso (D-B10-01 a D-B10-05)
D-B10-01 — Seleção de entidade no modal de vínculo: <select> no MVP-0.
O modal de criação de vínculo usa <select> com lista completa pré-carregada (GET /api/persons
ou GET /api/cases conforme o lado). Migração para typeahead dinâmico prevista em RF-010
(busca universal com FTS5). Impacto na RF-010: alterar apenas os arquivos de UI do modal:
  - app/static/js/case_detail.js — função loadPersonsIntoSelect()
  - app/static/js/person_detail.js — função loadCasesIntoSelect()
Critério para a troca: endpoints GET /api/persons?q=termo e GET /api/cases?q=termo com FTS5
operacionais (CA-010.2 atendido). Backend do RF-003 não muda.
Aprovado por: operador, sessão 2026-07-08.

D-B10-02 — REVOGADA e substituída por D-B10-05.
Originalmente documentava que a constraint UNIQUE(case_id, person_id, role_in_case) bloqueava
reinserção após remoção lógica. Resolvido em D-B10-05.

D-B10-03 — Endpoints de listagem de vínculos devolvem resposta enriquecida.
GET /api/links/person-case devolve PersonCaseLinkResponse com person_name, case_code e
case_name além dos campos nativos do link. Join resolvido no endpoint via busca em lote
(não N+1). Evita roundtrip adicional da UI para resolver nomes.

D-B10-04 — Router único app/api/links.py com sub-prefixos por tipo de vínculo.
/api/links/person-case hoje; RF-005 (pessoa↔organização) e RF-006 (org↔org) adicionam
sub-rotas no mesmo arquivo. Evita proliferação de routers para o mesmo domínio de vínculos.

D-B10-05 — Reativação silenciosa de vínculo removido.
Quando create_link recebe uma tripla (case_id, person_id, role_in_case) que já existe com
active=0, o serviço REATIVA o registro (active=1) atualizando source, reliability_level e
notes com os novos valores, e gera log case_person_link_create com reactivated=True no
metadata. O modal de vínculo funciona igual em ambos os casos — sem aviso de reativação.
Objetivo: o operador pode incluir, remover e reincluir vínculos livremente, sem restrições
técnicas visíveis. Aprovado por: operador, sessão 2026-07-10.


12. Pendências conhecidas
Pendência                                               Origem          Sprint para resolver
Declarar o Bloco 11 (logout, settings, fix D35)         Bloco 10        Sprint 01 (próxima sessão)
Migrar modal de vínculo para typeahead (D-B10-01)        RF-010          Sprint 02 (RF-010 + FTS5)
Handler 404 global com a shell                          Bloco 8.6       Quando conveniente
Extrair formatDate/statusBadge para módulo comum        D56/D58         RF-010 ou 3º consumidor
Atalho Ctrl+Alt+P para "Nova pessoa" (RF-002)           Revisão D55     Já resolvido ou Bloco 11
04_SEGURANCA.md §7.2 — adicionar "Bloqueio manual"      D40             Bloco 12
Tela /audit (CA-020.3, CA-020.5) — RF-020               Sprint 01       Bloco 11 ou 12
Endpoint HTTP para verify_chain                         ADR-003 §2.7    Sprint 10 ou posterior
ADR-004 (PDF de relatório)                              Backlog         Sprint 03
ADR-005 (pipeline OCR)                                  Backlog         Sprint 04
ADR-006 (motor de transcrição)                          Backlog         Sprint 05
ADR-007 (reconhecimento facial)                         Backlog         Sprint 08
ADR-008 (backup criptografado)                          Backlog         Sprint 10
ADR novo — motor de mapa offline                        Ideia I1        antes Sprint 03.5
ADR novo — dados sob sigilo judicial                    Ideia I5        antes Sprint 02.5
Iconografia (Phosphor / Lucide)                         Sprint 0.5      Sprint 01
Densidade configurável (seletor UI)                     Sprint 0.5      Sprint 01
Migração localStorage → banco para preferências UI      D6              Sprint 01
SQLCipher (ADR-002) — resolve D35 e D37                 Backlog         Sprint 10


13. Plano do Bloco 10 — RF-003 Vínculo Pessoa-Caso (CONCLUÍDO)
Requisito: RF-003 — Vínculo Pessoa-Caso.
CAs cobertos: CA-003.1 a CA-003.8.
Commit: 9967520

Sub-passos concluídos:
10.1 — Verificação de banco e modelo → ✅ Tabela case_person_links confirmada na migração b9387d80d7b1
10.2 — link_service.py → ✅ create/remove/list/get + DuplicateLinkError + reativação (D-B10-05)
10.3 — test_link_service.py → ✅ 18 testes (43/43 green na suíte completa)
10.4 — app/api/links.py + schemas/links.py + main.py → ✅ GET/POST/DELETE /api/links/person-case
10.5 — UI cases/detail.html + case_detail.js → ✅ seção vínculos + modal + tabela + remoção
10.6 — UI persons/detail.html + person_detail.js → ✅ espelho do 10.5 (eixo invertido: casos)
10.7 — Fechamento + atualização ESTADO_DO_PROJETO.md → ✅ esta sessão

Arquivos criados/alterados no Bloco 10:
- app/services/link_service.py       (NOVO)
- app/schemas/links.py               (NOVO)
- app/api/links.py                   (NOVO)
- tests/test_link_service.py         (NOVO)
- app/main.py                        (ALTERADO — registra links_router)
- app/web/templates/cases/detail.html  (ALTERADO — seção vínculos + modal)
- app/web/templates/persons/detail.html (ALTERADO — seção vínculos + modal)
- app/static/js/case_detail.js       (ALTERADO — vínculos RF-003)
- app/static/js/person_detail.js     (ALTERADO — vínculos RF-003)


14. Próximo bloco — Bloco 11 (a declarar)
Candidatos confirmados para o Bloco 11:
- Botão de logout visível na UI (D37 — pendência conhecida)
- Tela de configurações do sistema (settings screen — D11)
- Fix de isolamento de cache por processo (D35)
- RF-020 — tela de visualização do Audit Log (CA-020.3 a CA-020.5)

O operador decide a composição exata do Bloco 11 no início da próxima sessão.


15. Como atualizar este documento
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
