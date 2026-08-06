"""add platea_exclude to case_person_links and documents (AT-03.7)

Revision ID: at0307_platea_exclude
Revises: at0306_platea_status
Create Date: 2026-08-06 10:00:00.000000

AT-03.7: adiciona campo platea_exclude (Boolean, default False) em
case_person_links e documents para suportar marcacao [NAO COMPARTILHAR]
por item individual dentro de um caso compartilhado na Platea.
"""

from alembic import op
import sqlalchemy as sa

revision = "at0307_platea_exclude"
down_revision = "at0306_platea_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("case_person_links") as batch_op:
        batch_op.add_column(
            sa.Column(
                "platea_exclude",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "platea_exclude",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("platea_exclude")

    with op.batch_alter_table("case_person_links") as batch_op:
        batch_op.drop_column("platea_exclude")