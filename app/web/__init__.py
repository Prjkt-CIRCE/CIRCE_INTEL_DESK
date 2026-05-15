"""
Camada web do CIRCE Intel Desk.

Rotas que renderizam HTML (Jinja2) e infraestrutura transversal de
requisição/resposta. Distinto de `app/api/`, que devolve JSON ou
redireciona em fluxos de formulário.

- `routes` — rotas GET que renderizam telas (raiz `/`, `/setup`, `/login`).
- `middleware` — `auth_guard`, proteção de rotas (RF-021, sub-passo 5.8).
- `templates/` — templates Jinja2 (base, auth/, partials/).
"""