"""
CIRCE Intel Desk — Pacote de modelos SQLAlchemy.

Importar este pacote garante que todos os modelos estejam registrados
no metadata da Base, necessário para o Alembic detectá-los
durante a geração de migrações (Bloco 3).

Sprint 01 — Bloco 2.
Sprint 01-B — B8: Document.
Sprint 03 — 03-1: IncidentReport.
Sprint 04 — 04-2: DocumentText (RF-011).
"""

from app.models.base import Base
from app.models.user import User
from app.models.case import Case
from app.models.person import Person
from app.models.case_person_link import CasePersonLink
from app.models.organization import Organization
from app.models.person_org_link import PersonOrgLink
from app.models.org_org_link import OrgOrgLink
from app.models.audit_log import AuditLog
from app.models.setting import Setting
from app.models.document import Document
from app.models.document_text import DocumentText
from app.models.incident_report import IncidentReport

__all__ = [
    "Base",
    "User",
    "Case",
    "Person",
    "CasePersonLink",
    "Organization",
    "PersonOrgLink",
    "OrgOrgLink",
    "AuditLog",
    "Setting",
    "Document",
    "DocumentText",
    "IncidentReport",
]
