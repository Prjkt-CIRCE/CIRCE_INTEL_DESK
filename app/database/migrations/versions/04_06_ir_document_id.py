"""add_missing_columns_to_incident_reports

Adiciona colunas que estao no modelo SQLAlchemy mas podem estar ausentes no
banco, dependendo da versao da migracao 03_01_incident_reports aplicada:

  - document_id            INTEGER  (CA-009.4 — vinculo BO → documento)
  - criminal_classification TEXT     (tipificacao penal, RF-023)
  - procedural_status       TEXT     (status processual, RF-023)

Cada ADD COLUMN e condicional (checa se ja existe): a migracao e idempotente.

Revision ID: 04_06_ir_document_id
Revises: b64e192e1de0
Create Date: 2026-08-16
Sprint 04 — Sub-passo 04-6 (CA-009.4)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "04_06_ir_document_id"
down_revision: Union[str, None] = "b64e192e1de0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Retorna True se a coluna ja existe na tabela (SQLite-safe)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    tbl = "incident_reports"

    if not _column_exists(tbl, "document_id"):
        op.add_column(tbl, sa.Column("document_id", sa.Integer(), nullable=True))

    if not _column_exists(tbl, "criminal_classification"):
        op.add_column(tbl, sa.Column("criminal_classification", sa.String(500), nullable=True))

    if not _column_exists(tbl, "procedural_status"):
        op.add_column(tbl, sa.Column("procedural_status", sa.String(100), nullable=True))


def downgrade() -> None:
    # SQLite: usa batch_alter_table para DROP COLUMN (requer SQLite >= 3.35 ou
    # recreacao da tabela via Alembic batch mode).
    with op.batch_alter_table("incident_reports") as batch_op:
        for col in ("document_id", "criminal_classification", "procedural_status"):
            try:
                batch_op.drop_column(col)
            except Exception:
                pass  # ja removida ou nao existia
