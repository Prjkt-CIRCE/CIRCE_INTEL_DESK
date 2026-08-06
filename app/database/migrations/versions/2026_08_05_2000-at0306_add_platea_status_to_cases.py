"""add platea_status to cases (AT-03.6)

Revision ID: at0306_platea_status
Revises: 9bb3a278675f
Create Date: 2026-08-05 20:00:00.000000

Adiciona campo platea_status a tabela cases para rastrear o estado de
sincronizacao Intel Desk -> Athena (Platea).

Valores possiveis:
  none         -> caso nao compartilhado (padrao para todos os existentes)
  shared       -> caso publicado na Platea com sucesso
  pending_sync -> publicacao solicitada, aguardando envio ao Athena
  error        -> ultima tentativa de sincronizacao falhou

Referencia: AT-03.6, D-AT-019.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "at0306_platea_status"
down_revision = "9bb3a278675f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adiciona coluna com DEFAULT 'none' — todos os casos existentes
    # nascem como nao compartilhados, o que e correto operacionalmente.
    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "platea_status",
                sa.String(),
                nullable=False,
                server_default="none",
            )
        )
        batch_op.create_index(
            "idx_cases_platea_status",
            ["platea_status"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.drop_index("idx_cases_platea_status")
        batch_op.drop_column("platea_status")