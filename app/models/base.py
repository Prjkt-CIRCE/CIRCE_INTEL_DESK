"""
CIRCE Intel Desk — Base declarativa do SQLAlchemy.

Todos os modelos herdam de Base. A criação do banco e a configuração
de engine ficam em app/database/session.py.

Sprint 01 — Bloco 2.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos do CIRCE."""

    pass
