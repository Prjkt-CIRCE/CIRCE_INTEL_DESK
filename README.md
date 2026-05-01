# CIRCE Intel Desk

> Case Intelligence, Records, Connections & Evidence.
>
> Sistema desktop local de inteligencia operacional, offline-first, para apoio a atividade licita de analise de inteligencia policial.

## Estado

Sprint 0 - Fundacao tecnica e ambiente.

## Stack

- Python 3.12.x
- FastAPI + Uvicorn
- SQLite (MVP) / SQLCipher (operacional)
- HTML + CSS + JavaScript vanilla
- Argon2id para senhas

Detalhes em `docs/adrs/ADR-001_STACK.md` e `docs/adrs/ADR-002_BANCO.md`.

## Como rodar (apos clone)

```powershell
# Criar e ativar ambiente virtual
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Subir o servidor
python run.py
```

Acessar no navegador: `http://127.0.0.1:8765/health`

## Documentacao do projeto

Ver pasta `docs/` para a especificacao completa, criterios de aceite, arquitetura, modelo de ameacas e ADRs.

## Premissas inegociaveis

- Servidor escuta apenas em loopback (127.0.0.1).
- Arquivo importado nunca e alterado.
- Toda saida automatica de IA e tratada como pendente de validacao humana.
- Toda acao sensivel gera log de auditoria.
- Operacao preferencialmente offline.

## Licenca

A definir.
