"""
CIRCE Intel Desk — Pacote de modelos SQLAlchemy.

Importar este pacote garante que todos os modelos estejam registrados
no metadata da Base, o que é necessário para o Alembic detectá-los
durante a geração de migrações (Bloco 3).

Sprint 01 — Bloco 2.
"""

from app.models.base import Base
from app.models.user import User
from app.models.case import Case
from app.models.person import Person
from app.models.case_person_link import CasePersonLink
from app.models.audit_log import AuditLog
from app.models.setting import Setting

__all__ = [
    "Base",
    "User",
    "Case",
    "Person",
    "CasePersonLink",
    "AuditLog",
    "Setting",
]
