"""add_incident_report_person_links_table

Revision ID: 03_02_ir_person_links
Revises: 03_01_incident_reports
Create Date: 2026-08-13 00:01:00.000000

Cria a tabela incident_report_person_links (RF-009 CA-009.3).
Sprint 03 — Sub-passo 03-2.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "03_02_ir_person_links"
down_revision: Union[str, None] = "03_01_incident_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_report_person_links",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "incident_report_id",
            sa.Integer,
            sa.ForeignKey("incident_reports.id"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            sa.Integer,
            sa.ForeignKey("persons.id"),
            nullable=False,
        ),
        sa.Column("role_in_report", sa.String, nullable=False),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("active", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.String, nullable=False),
        sa.Column(
            "created_by",
            sa.Integer,
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "incident_report_id", "person_id", "role_in_report",
            name="uq_ir_person_role",
        ),
    )

    op.create_index(
        "idx_ir_person_links_report_id",
        "incident_report_person_links",
        ["incident_report_id"],
    )
    op.create_index(
        "idx_ir_person_links_person_id",
        "incident_report_person_links",
        ["person_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_ir_person_links_person_id", table_name="incident_report_person_links")
    op.drop_index("idx_ir_person_links_report_id", table_name="incident_report_person_links")
    op.drop_table("incident_report_person_links")
