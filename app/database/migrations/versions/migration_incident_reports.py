"""add_incident_reports_table

Revision ID: 03_01_incident_reports
Revises: at0306_platea_status
Create Date: 2026-08-13 00:00:00.000000

Cria a tabela incident_reports (RF-009 — Boletim de Ocorrência).
Sprint 03 — Sub-passo 03-1.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "03_01_incident_reports"
down_revision: Union[str, None] = "at0306_platea_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),

        # Identificação do BO
        sa.Column("bo_number", sa.String, nullable=False),
        sa.Column("bo_date", sa.String, nullable=True),
        sa.Column("issuing_unit", sa.String, nullable=True),

        # Conteúdo
        sa.Column("summary", sa.String, nullable=True),
        sa.Column("criminal_type", sa.String, nullable=True),
        sa.Column("procedural_status", sa.String, nullable=True),
        sa.Column("notes", sa.String, nullable=True),

        # Vínculos opcionais
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True),

        # Ciclo de vida
        sa.Column("status", sa.String, nullable=False, server_default="active"),
        sa.Column("created_at", sa.String, nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.String, nullable=True),
        sa.Column("updated_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )

    op.create_index("idx_incident_reports_case_id", "incident_reports", ["case_id"])
    op.create_index("idx_incident_reports_status", "incident_reports", ["status"])
    op.create_index("idx_incident_reports_bo_number", "incident_reports", ["bo_number"])


def downgrade() -> None:
    op.drop_index("idx_incident_reports_bo_number", table_name="incident_reports")
    op.drop_index("idx_incident_reports_status", table_name="incident_reports")
    op.drop_index("idx_incident_reports_case_id", table_name="incident_reports")
    op.drop_table("incident_reports")
