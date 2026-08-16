"""merge_04_04_and_04_06

Merge de duas branches paralelas do Sprint 04:
  - 04_04_fts_doc_texts  (indexacao OCR FTS5)
  - 04_06_ir_document_id (coluna document_id em incident_reports)

Revision ID: 04_merge_heads
Revises: 04_04_fts_doc_texts, 04_06_ir_document_id
Create Date: 2026-08-16
"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "04_merge_heads"
down_revision: Union[str, tuple[str, ...], None] = (
    "04_04_fts_doc_texts",
    "04_06_ir_document_id",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge migration — sem alterações de schema.
    pass


def downgrade() -> None:
    pass
