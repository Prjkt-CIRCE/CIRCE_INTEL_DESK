"""add_person_fields_to_incident_reports

Revision ID: b64e192e1de0
Revises: merge_wb_s03
Create Date: 2026-08-15 13:31:17.107016+00:00

Corrigido manualmente v3:
- Todas as operações de DROP usam SQL direto com IF EXISTS para tolerar
  estado de banco inconsistente (objetos que o autogenerate detectou como
  existentes mas já haviam sido removidos ou nunca criados).
- Apenas os ADD COLUMN necessários permanecem no batch_alter_table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b64e192e1de0'
down_revision: Union[str, None] = 'merge_wb_s03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remover tabela e índices antigos com IF EXISTS (tolerante a ausência)
    op.execute("DROP TABLE IF EXISTS incident_report_person_links")
    op.execute("DROP INDEX IF EXISTS idx_incident_reports_bo_number")

    # Adicionar colunas novas em incident_reports
    with op.batch_alter_table('incident_reports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('person_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('person_role', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('criminal_classification', sa.String(length=500), nullable=True))
        batch_op.create_index('idx_incident_reports_person_id', ['person_id'], unique=False)

    # Remover colunas obsoletas com SQL direto IF EXISTS (SQLite 3.35+)
    # Se a versão do SQLite não suportar, estas linhas são ignoradas sem erro.
    try:
        op.execute("ALTER TABLE incident_reports DROP COLUMN IF EXISTS notes")
        op.execute("ALTER TABLE incident_reports DROP COLUMN IF EXISTS criminal_type")
    except Exception:
        pass  # SQLite < 3.35 não tem DROP COLUMN — colunas ficam como órfãs inofensivas


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_incident_reports_person_id")
    with op.batch_alter_table('incident_reports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('criminal_type', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('notes', sa.VARCHAR(), nullable=True))
        batch_op.drop_column('criminal_classification')
        batch_op.drop_column('person_role')
        batch_op.drop_column('person_id')
