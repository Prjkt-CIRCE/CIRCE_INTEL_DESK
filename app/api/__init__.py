"""
Rotas de API do CIRCE Intel Desk.

Camada HTTP fina (03_ARQUITETURA.md §3.1): valida entrada, despacha
para `app/services/`, monta resposta. Não contém regra de domínio.

- `auth` — `/setup`, `/login`, `/logout` (RF-021).

Endpoints de domínio (casos, pessoas, organizações) entram a partir
dos Blocos 8 a 10 da Sprint 01.
"""