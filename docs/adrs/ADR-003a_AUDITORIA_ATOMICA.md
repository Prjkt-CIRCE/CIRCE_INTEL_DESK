# ADR-003a — Auditoria atômica de operações que criam entidades

- **Status:** Accepted
- **Data:** 2026-05-30
- **Sprint:** 01 (Bloco 8)
- **Supera:** —
- **Complementa:** ADR-003 (imutabilidade do audit log)
- **Superado por:** —
- **Relacionados:** ADR-003 §2.3, §2.4, §2.6; `04_SEGURANCA.md` §7.1; `10_MODELO_DE_AMEACAS.md` §7

---

## 1. Contexto

O ADR-003 §2.4 fixa o princípio de que a ação de domínio e seu registro de
auditoria ocorrem na **mesma transação SQL**: se o log falha, a ação de domínio
é desfeita por rollback. "Não há ação não-logada."

O `audit_service.log_action()` implementado no Bloco 7 cumpre isso para os
eventos da fase de autenticação (login, logout, lock) abrindo a transação por
conta própria, com `db.execute(text("BEGIN IMMEDIATE"))` como primeira operação
(ADR-003 §2.3, garantindo o lock de escrita do SQLite antes de ler o último
hash da cadeia).

Esse desenho funciona para eventos **sem entidade pré-existente**: o login não
insere nada antes de logar. Mas o Bloco 8 (RF-001, criação de Caso) é a primeira
operação que precisa **inserir uma entidade e auditá-la na mesma transação**. E
aqui surge o conflito mecânico:

1. O `entity_id` do caso entra na string canônica do hash (ADR-003 §2.1).
2. Logo, o caso precisa ser inserido e ter seu `id` materializado (`flush`)
   **antes** da chamada a `log_action`.
3. Mas o `flush` do caso já abre a transação implícita do SQLAlchemy.
4. Quando `log_action` então tenta `BEGIN IMMEDIATE`, o SQLite recusa com
   `cannot start a transaction within a transaction`.

Verificado empiricamente com o `session.py` real do projeto (sem
`isolation_level` customizado): a sequência "inserir caso → flush → log_action"
estoura. O Bloco 7 nunca encontrou isso porque só auditou eventos sem inserção
prévia de entidade.

Este conflito vale para **todos** os RFs seguintes que criam entidades
(pessoa, organização, vínculos, BOs, documentos). É um problema de fundação,
não específico do caso.

O próprio ADR-003 §2.6 previu: *"Se até lá surgir necessidade, abre-se
ADR-003a."* É o que este documento faz.

---

## 2. Opções consideradas

### Opção A — Commit do domínio e log em seguida (transações separadas)

Inserir e commitar o caso, depois logar em transação própria.

**Rejeitada.** Viola diretamente o ADR-003 §2.4. Verificado em teste: se o log
falha após o commit do caso, o caso permanece gravado — ação não-logada. É
exatamente o cenário que o modelo de ameaças §7 proíbe ("registro alterável/
ausente é registro inválido").

### Opção B — `log_action` ganha parâmetro `manage_transaction: bool = True`

Quando `True` (padrão), mantém o comportamento atual: `log_action` abre o
`BEGIN IMMEDIATE`. Quando `False`, **não** abre a transação — assume que o
chamador já a abriu e fará o `commit`/`rollback`.

O serviço de domínio (ex.: `case_service.create_case`) passa a ser o dono da
transação: abre `BEGIN IMMEDIATE` como primeira operação, insere a entidade,
faz `flush` para materializar o `id`, chama `log_action(..., manage_transaction=False)`,
e commita uma única vez. Falha em qualquer ponto → `rollback` reverte entidade
e log juntos.

**Aceita.** Mudança mínima e retrocompatível por construção: o default `True`
reproduz exatamente o caminho de código do Bloco 7. Nenhum chamador existente
(login, logout, lock) precisa mudar.

### Opção C — `isolation_level=None` na engine + controle manual global

Desligar o BEGIN implícito do driver SQLite e gerenciar toda transação na mão.

**Rejeitada para esta sprint.** Resolve, mas muda o comportamento transacional
de **todo** o sistema, incluindo código já validado do Bloco 6 e 7. Risco
desproporcional ao problema. Reavaliável na Sprint 10 se houver outro motivo.

---

## 3. Decisão

Adotada a **Opção B**.

`audit_service.log_action()` recebe um parâmetro keyword-only
`manage_transaction: bool = True`:

- `True` (padrão): emite `BEGIN IMMEDIATE` antes de ler o último hash. Caminho
  idêntico ao Bloco 7. Usado por eventos autônomos (login, logout, lock) que
  commitam logo após.
- `False`: pula o `BEGIN IMMEDIATE`. O chamador é responsável por ter aberto a
  transação (com `BEGIN IMMEDIATE`, para preservar o lock de escrita do
  ADR-003 §2.3) e por commitar/rollback. Usado por serviços de domínio que
  inserem entidade e auditam atomicamente.

Contrato para serviços de domínio que criam/alteram entidades:

```
db.execute(text("BEGIN IMMEDIATE"))     # 1. lock de escrita (ADR-003 §2.3)
db.add(entidade); db.flush()            # 2. materializa entity_id
audit_service.log_action(               # 3. log na MESMA transação
    db, ..., entity_id=entidade.id,
    manage_transaction=False,
)
db.commit()                             # 4. commit único; falha -> rollback de tudo
```

A canonicalização do hash, o encadeamento, o cálculo SHA-256 e a verificação
de cadeia permanecem **inalterados** (ADR-003 §2.1, §2.7). Este ADR muda apenas
**quem** abre a transação, não **o que** é gravado.

---

## 4. Consequências

### 4.1 Positivas

- Operações que criam entidades passam a poder auditar atomicamente, cumprindo
  o ADR-003 §2.4 que antes era inalcançável para esse caso.
- Alteração cirúrgica: um parâmetro com default seguro. Zero impacto nos
  chamadores existentes.
- O padrão de transação fica explícito e reutilizável por todos os serviços de
  domínio das próximas sprints.

### 4.2 Negativas / limites

- O serviço de domínio agora carrega a responsabilidade de abrir o
  `BEGIN IMMEDIATE` e de commitar. Esquecer o `BEGIN` faz o log voltar a poder
  encadear errado; esquecer o `commit` deixa a transação pendente. Mitigação:
  padrão documentado aqui e encapsulado em cada função de serviço, mais teste
  de cadeia (`verify_chain`) na suíte.
- Dois caminhos de transação (`True`/`False`) é uma bifurcação a manter. Aceita
  como custo proporcional ao ganho.

### 4.3 Riscos residuais aceitos

- Um futuro serviço que chame `log_action(manage_transaction=False)` sem ter
  aberto transação cairia no comportamento padrão do SQLAlchemy (transação
  implícita no flush) — ainda atômico via `commit`/`rollback` do chamador, mas
  sem o `BEGIN IMMEDIATE` que garante o lock de escrita imediato. Em ambiente
  monousuário loopback (D3), o impacto prático é nulo. Documentado para não
  surpreender em fase multioperador (fora de escopo atual — modelo de ameaças §6).

---

## 5. Revisão

Revisar este ADR ao:

- Iniciar a Sprint 10 (SQLCipher) — reavaliar junto com a Opção C, agora que o
  custo de mexer no comportamento transacional global pode se justificar.
- Introduzir concorrência real (multioperador) — o contrato de quem abre o
  `BEGIN IMMEDIATE` precisará de revisão.
