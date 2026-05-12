# ADR-003 — Imutabilidade do Audit Log

- **Status:** Accepted
- **Data:** 2026-05-12
- **Sprint:** 01
- **Supera:** —
- **Superado por:** —
- **Relacionados:** ADR-002 (banco), `04_SEGURANCA.md` §7, `10_MODELO_DE_AMEACAS.md` §7, `05_MODELO_DE_DADOS.md` §3.8

---

## 1. Contexto

O CIRCE Intel Desk precisa registrar ações sensíveis (login, logout, criação/edição/arquivamento de entidades, vínculos, visualizações de log) em uma trilha que possa ser confiada como prova operacional e que resista a:

- **A2** — colega curioso que use a estação enquanto o operador está logado e queira apagar rastro de uma intromissão.
- **A3** — malware oportunista que tente limpar a trilha após exfiltração.

Os requisitos formais já estão dados pela documentação existente:

- `04_SEGURANCA.md` §7.1 exige *append-only operacional* (interface comum não permite editar nem excluir registros) e *hash-encadeamento* a definir nesta sprint.
- `05_MODELO_DE_DADOS.md` §3.8 já reservou as colunas `previous_hash` e `record_hash` na tabela `audit_logs`.
- `06_CRITERIOS_DE_ACEITE.md` CA-020.2 lista os campos obrigatórios do registro.
- `10_MODELO_DE_AMEACAS.md` §7 define o princípio: *registro alterável é registro inválido*.

Este ADR fixa **como** essas exigências viram código.

---

## 2. Decisão

### 2.1 Algoritmo de encadeamento

Cada registro de `audit_logs` carrega um campo `record_hash` calculado como:

```
record_hash = SHA-256(canonical_string)
```

onde `canonical_string` é a concatenação determinística dos campos canônicos do registro, separados por `\x1f` (US — Unit Separator, byte 0x1F), na ordem:

```
previous_hash || timestamp || user_id || action || entity_type || entity_id || description || metadata || status
```

Regras de canonicalização:

- Campos nulos são representados pela string literal `\x00` (NULL byte). Distinguir nulo de string vazia importa: `description=""` ≠ `description=NULL`.
- `timestamp` é serializado em ISO 8601 com sufixo `Z` (UTC), microsegundos opcionais — formato exato fixado: `YYYY-MM-DDTHH:MM:SS.ffffffZ`.
- `user_id` e `entity_id` são serializados como inteiro decimal sem padding (`"42"`, não `"00042"`).
- `metadata` é serializado como JSON canônico: chaves ordenadas alfabeticamente, sem espaços (`separators=(",", ":")`), `ensure_ascii=False`, floats com representação Python padrão. Se `metadata IS NULL`, usa o marcador `\x00`; se for objeto vazio, usa `{}`.
- Todas as strings são codificadas em UTF-8 antes do hash.
- O resultado final é representado em **hexadecimal lowercase de 64 caracteres**, sem prefixo (sem `sha256:`).

### 2.2 Registro gênese

O primeiro registro da tabela tem `previous_hash = NULL` (coluna nullable no banco). Na canonicalização, esse NULL vira o marcador `\x00`, igual a qualquer outro campo nulo. Sem string mágica, sem genesis hash hardcoded.

Justificativa: simplicidade. Não precisamos rastrear "o início da corrente" como evento especial — basta detectar que `previous_hash IS NULL` em qualquer linha que não seja a primeira por `id` para sinalizar inconsistência.

### 2.3 Inserção transacional

A inserção de um registro de audit log obedece à seguinte sequência, **dentro de uma única transação SQL**:

1. `SELECT record_hash, id FROM audit_logs ORDER BY id DESC LIMIT 1;` — captura o último hash e id conhecidos.
2. Monta o novo registro com `previous_hash = <hash capturado ou NULL>`.
3. Calcula `record_hash` segundo §2.1.
4. `INSERT` do registro.
5. `COMMIT`.

Concorrência: o servidor escuta apenas em loopback (D3) e é monousuário. Mesmo assim, a transação fecha a janela teórica de duas inserções simultâneas com mesmo `previous_hash`. Em SQLite, `BEGIN IMMEDIATE` garante o lock de escrita.

### 2.4 Bloqueio da ação principal em falha de log

Princípio operacional já fixado em `04_SEGURANCA.md` §7.1: **erro de log bloqueia a ação principal**.

Implementação: o serviço de domínio (criar caso, vincular pessoa, etc.) e a chamada a `audit_service.log_action()` ocorrem na **mesma transação SQL**. Se o log falha, a transação faz rollback e a ação de domínio também é desfeita. Não há ação não-logada.

Aplicação inversa: ações que **não modificam estado** (visualizar log, visualizar entidade) também são logadas (CA-020.5), e a falha no log impede a visualização. Exceção: a falha no log do próprio `audit_view` não pode entrar em loop infinito — neste caso, a falha é registrada no log operacional (`data/logs/circe.log`) e a tela exibe erro genérico.

### 2.5 Imutabilidade na camada de aplicação

Nenhuma rota da API exposta ao operador comum permite `UPDATE` ou `DELETE` em `audit_logs`. Concretamente:

- O modelo SQLAlchemy `AuditLog` não tem métodos de update/delete expostos.
- O `audit_service` exporta apenas `log_action(...)` e `verify_chain(...)`. Não exporta `update`, `delete`, `purge` ou similar.
- Não há endpoint REST com verbo `PUT`, `PATCH` ou `DELETE` sobre `/api/audit/*`.

Isso é defesa contra a interface, não contra o banco. Quem acessar o arquivo `.db` diretamente com `sqlite3` pode editar tudo — mas isso é detectável por verificação de cadeia (§2.7).

### 2.6 Imutabilidade na camada de banco — não nesta sprint

Considerei e descartei para o MVP-0:

- **Triggers `BEFORE UPDATE` e `BEFORE DELETE` que abortam** com `RAISE(ABORT, ...)`. Funciona, mas adiciona código de manutenção e cria atrito em migrações futuras (alterar coluna na `audit_logs` exige remover e recriar o trigger).
- **Tabela com restrições de privilégio** — SQLite não tem GRANT/REVOKE de coluna ou linha.
- **SQLite append-only mode** (não existe nativamente).

A imutabilidade reforçada será reavaliada na Sprint 10 (SQLCipher) — quando o banco for cifrado e o atacante perder o acesso direto, o ganho de adicionar triggers cai consideravelmente. Se até lá surgir necessidade, abre-se ADR-003a.

### 2.7 Verificação da cadeia

`audit_service.verify_chain()` percorre `audit_logs` em ordem crescente de `id` e:

1. Para cada registro, recalcula `record_hash` com a mesma função de §2.1.
2. Compara com o `record_hash` armazenado.
3. Compara o `previous_hash` armazenado com o `record_hash` do registro anterior (ou `NULL`/`\x00` para o primeiro).
4. Retorna `{ ok: bool, broken_at_id: int | null, total: int }`.

Esta função **não tem endpoint exposto** no MVP-0. É chamada por:

- Script utilitário em `app/utils/audit_verify.py` rodável manualmente do terminal.
- Suíte de testes da Sprint 01.

Endpoint UI fica para fase posterior (Sprint 10 ou quando houver caso de uso).

### 2.8 Volume operacional

Estimativa: 500 a 2.000 registros por dia de uso intenso. Em 5 anos: 1M a 4M registros. SHA-256 sobre uma string de poucos KB custa microsegundos — não é gargalo. Índices em `timestamp`, `user_id`, `action`, `(entity_type, entity_id)` já estão previstos no DDL.

---

## 3. Consequências

### 3.1 Positivas

- Trilha de auditoria com integridade detectável: qualquer edição manual no `.db` quebra a cadeia em ponto identificável.
- Sem dependência externa: SHA-256 está na biblioteca padrão de Python (`hashlib`).
- Transação compartilhada com a ação de domínio garante completude: não existe ação no banco sem log correspondente.
- Função de canonicalização determinística e documentada — qualquer reimplementação (auditoria externa, análise forense) chega ao mesmo hash.

### 3.2 Negativas / limites reconhecidos

- **Não impede edição via acesso direto ao arquivo `.db`.** Detecta. A barreira contra acesso direto vem na Sprint 10 com SQLCipher.
- **Não impede `DROP TABLE audit_logs`.** Detecta — `verify_chain()` retorna `total = 0` em base previamente populada, o que é sinal claro. Não há defesa real contra "apagar tudo" sem o banco cifrado.
- **Custo de bloquear ação principal em falha de log.** Em prática, falhas de log raras (disco cheio, banco corrompido). Quando acontecerem, o operador percebe e age — o que é o comportamento desejado.
- **Reordenação de campos no enum de `action` é mudança quebrável.** A canonicalização inclui `action` como string — se a string mudar, o hash muda. Logo, **`action` é parte do contrato** e renomear `case_create` para `caso_criar` invalida a cadeia retroativamente. Adicionar novas ações ao enum, sim. Renomear existentes, não — exige ADR e re-canonicalização documentada.

### 3.3 Riscos residuais aceitos

- Operador com acesso shell ao servidor pode alterar o `.db` e recalcular toda a cadeia, refazendo todos os hashes. **Aceito** — `10_MODELO_DE_AMEACAS.md` §6 declara insider hostil dentro da própria agência fora de escopo. Quem tem o servidor tem a base; o objetivo é detectar adulteração casual, não resistir a perícia adversarial competente.

---

## 4. Alternativas consideradas

### 4.1 Apenas controle de aplicação, sem hash

Mais simples. Rejeitado: não detecta edição direta no `.db`. `04_SEGURANCA.md` §7.1 já tinha exigido hash-encadeamento — este ADR existe para *como*, não para *se*.

### 4.2 Hash com chave (HMAC) usando senha do operador

Tentador para A3 (malware sem a senha não consegue forjar). Rejeitado para o MVP-0:

- Sessão multioperador no futuro complicaria o esquema de chave.
- Em A3 com privilégio de usuário, a chave em memória do processo é capturável de qualquer forma.
- Aumenta complexidade sem ganho proporcional na fase atual.

Reavaliar na Sprint 10 junto com SQLCipher.

### 4.3 Merkle tree em vez de chain linear

Mais robusto contra adulteração em massa. Rejeitado: complexidade alta para volume baixo. Chain linear é suficiente para o modelo de ameaça atual.

### 4.4 JSON canônico via biblioteca externa

Considerei `python-json-canonicalization` (RFC 8785). Rejeitado: dependência extra para resolver um problema que `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)` já resolve para o nosso uso. Se um dia o serviço de log precisar interoperar com sistema externo, reabrimos.

---

## 5. Implementação prevista (Bloco 7 da Sprint 01)

- `app/services/audit_service.py` exporta `log_action(...)` e `verify_chain()`.
- Função interna `_canonical_string(record_dict) -> bytes` documentada com docstring.
- Função interna `_compute_hash(canonical_bytes) -> str` retorna hex lowercase.
- Testes em `tests/test_audit_chain.py` cobrindo: registro gênese, encadeamento de N registros, detecção de adulteração em `record_hash`, detecção de adulteração em campo canônico, detecção de remoção de registro do meio.

---

## 6. Revisão

Revisar este ADR ao:

- Iniciar a Sprint 10 (SQLCipher) — avaliar HMAC com chave derivada da senha do operador.
- Qualquer mudança no enum `audit_logs.action` que renomeie ações existentes.
- Qualquer mudança na lista de campos canônicos (§2.1).
