# Fechamento — Sprint 01 / Bloco 8 (RF-001: Casos)

> Relatório de encerramento conforme template `06_CRITERIOS_DE_ACEITE.md` §5.
> Sem fechamento formal, o bloco não é considerado concluído — mesmo que o código exista.

```
SPRINT: 01 — Núcleo MVP-0 / Bloco 8 (RF-001 — Cadastro de Caso)
STATUS: CONCLUÍDO

CRITÉRIOS DE ACEITE — STATUS POR ITEM:
  CA-001.1 (criar caso com nome; código {ano}-{NNNN} gerado): ✅
  CA-001.2 (caso criado aparece na lista sem reload):          ✅
  CA-001.3 (impede criar sem nome; botão desabilitado + aviso): ✅
  CA-001.4 (editar campos; alterações persistem após reinício): ✅
  CA-001.5 (arquivar some da lista padrão; aparece em filtro):  ✅
  CA-001.6 (criar/editar/arquivar gera registro em audit_logs): ✅
  CA-001.7 (ordenação por código, nome, data de criação, status): ✅
```

## O QUE FOI IMPLEMENTADO

RF-001 completo, em sete sub-passos:

- **8.1** — Verificação do banco e do modelo `Case` (15 colunas, head Alembic `b9387d80d7b1`). Descoberto o banco canônico `data/circe.db` (D44).
- **8.2** — Schemas Pydantic (`CaseCreate`, `CaseUpdate`, `CaseResponse`) + `case_service` (geração de `case_code` `{ano}-{NNNN}`, validações, auditoria atômica via ADR-003a). Commit `79c8f6a`.
- **8.3** — API REST `/api/cases` (GET lista, POST cria, GET/{id}, PATCH, DELETE arquiva). Commit `79c8f6a`.
- **8.4** — Tela `/cases`: listagem, criação sem reload, ordenação por cabeçalho, sistema de toast dinâmico (D53). Commit `1ef6a4f`.
- **8.5** — Edição (modal dual criar/editar), arquivamento lógico com confirmação, filtro "arquivados". Commit `048a91f`.
- **8.6** — Tela de detalhe SPA-leve (`/cases/{id}`), ciclo de edição lista↔detalhe via `?edit=id` (D56), tratamento de 404 na shell, atalho "Novo caso" revisado para Ctrl+Alt+N. Commit `316bd6f`.
- **8.7** — Faxina de repositório, registro de decisões, reconciliação do `ESTADO_DO_PROJETO.md`, este relatório. (Esta sessão.)

## O QUE FOI TESTADO

- 13 testes automatizados commitados, todos passando: 5 de cadeia de auditoria (`test_audit_chain.py`) + 8 unitários do serviço de casos (`test_case_service.py`).
- Cadeia de auditoria verificada íntegra via `python -m app.utils.audit_verify`.
- Validação manual pelo operador no navegador, em cada sub-passo: criação, listagem, ordenação, edição (de caso ativo e arquivado), arquivamento, filtro, tela de detalhe, ciclo de edição via detalhe, 404 tratado, atalho de teclado.

## O QUE FUNCIONOU

- Auditoria atômica (ADR-003a) em todas as operações de escrita — nenhuma ação de domínio sem registro.
- Edição lista↔detalhe sem refatorar o `cases.js` validado (D56), com fallback de busca singular para casos arquivados.
- Tratamento de sessão expirada no fetch (D54) consistente entre `cases.js` e `case_detail.js`.
- Tela de detalhe com zero CSS novo — apenas classes canônicas do design system.

## O QUE FALHOU

- Nenhuma falha funcional bloqueante. Dois pontos de fricção de ambiente, ambos resolvidos ou aceitos:
  - **Atalho Ctrl+N** abria nova janela do navegador (tecla reservada). Resolvido: revisado para **Ctrl+Alt+N** (revisão de D55), validado pelo operador.
  - **`/cases/abc`** (id não-numérico) cai no JSON cru do FastAPI (404 sem shell). Classificado pelo operador como ACEITÁVEL — não é fluxo real (chega-se ao detalhe por clique, sempre id numérico). Registrado como pendência de baixa prioridade.

## CORREÇÕES NECESSÁRIAS

- Nenhuma pendente para considerar o RF-001 entregue.
- Itens de melhoria não-bloqueantes (ver §12 do `ESTADO_DO_PROJETO.md`): handler 404 global com shell; extração de `formatDate`/`statusBadge`/modal para módulo compartilhado (no RF-002); `Ctrl+P` de "Nova pessoa" precisará virar `Ctrl+Alt+P`.

## DOCUMENTOS ATUALIZADOS

- `ESTADO_DO_PROJETO.md` — reconciliado (estava 3 versões atrás): estado, histórico, código, endpoints, decisões D56 + revisão D55, pendências, data.
- `docs/adrs/ADR-003a_AUDITORIA_ATOMICA.md` — copiado para o repositório (D46).
- `.gitattributes` — criado (normalização LF/CRLF).
- Este relatório (`docs/FECHAMENTO_BLOCO8.md`).

## ADRs GERADOS

- Nenhum ADR novo no Bloco 8. O ADR-003a (auditoria atômica) foi criado no 8.2 e apenas copiado para o repo no 8.7.
- Decisões registradas como D-series no `ESTADO_DO_PROJETO.md` §11: D44–D56 + revisão de D55.

## PRÓXIMA SPRINT / PRÓXIMO BLOCO

- Declarar o **Bloco 9** da Sprint 01. Candidatos naturais, em ordem de dependência:
  - **RF-002 — Cadastro de Pessoa** (CA-002.1 a .8). Reaproveita o padrão de tela/serviço do RF-001; é a base para os vínculos.
  - **RF-003 — Vínculo Pessoa-Caso** (depende de RF-002).
  - **RF-020 — Tela de auditoria** `/audit` (CA-020.3, .5) — independente, pode entrar a qualquer momento.
- Recomendação: RF-002, por ser pré-requisito de RF-003 e por exercitar a extração dos utilitários compartilhados (pendência aberta no 8.6).
