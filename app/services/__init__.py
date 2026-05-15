"""
Serviços do CIRCE Intel Desk.

Camada de regra: funções puras de domínio e operações que não pertencem
nem a rotas (`app/api/`, `app/web/`) nem a modelos (`app/models/`).

- `auth_service` — hashing Argon2id e verificação de senha.
- `session_service` — emissão e verificação de tokens HMAC stateless.
- `settings_service` — leitura/escrita dos parâmetros operacionais (D11).

Sem I/O HTTP, sem dependência de FastAPI. Importam de `app.config`,
`app.database`, `app.models` quando precisam.
"""