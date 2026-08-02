"""add_fts5_search_index

Revision ID: 9bb3a278675f
Revises: b3234f16d129
Create Date: 2026-08-02 22:34:47.326659+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bb3a278675f'
down_revision: Union[str, None] = 'b3234f16d129'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_cases USING fts5(
            case_id UNINDEXED,
            name,
            case_code,
            description,
            unit,
            responsible,
            tokenize='unicode61'
        )
    """)
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_persons USING fts5(
            person_id UNINDEXED,
            full_name,
            aliases,
            notes,
            tokenize='unicode61'
        )
    """)
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_organizations USING fts5(
            org_id UNINDEXED,
            name,
            aliases,
            description,
            tokenize='unicode61'
        )
    """)
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(
            document_id UNINDEXED,
            original_filename,
            title,
            tokenize='unicode61'
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fts_cases")
    op.execute("DROP TABLE IF EXISTS fts_persons")
    op.execute("DROP TABLE IF EXISTS fts_organizations")
    op.execute("DROP TABLE IF EXISTS fts_documents")
