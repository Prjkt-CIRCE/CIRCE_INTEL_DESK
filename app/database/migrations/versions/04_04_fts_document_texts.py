"""add_fts5_document_texts_index

Cria a tabela virtual FTS5 para indexação de textos OCR validados (CA-011.6).
Apenas textos com validation_status='validated' são indexados — decisão de
domínio aplicada pelo search_service (não por esta migração).

Revision ID: 04_04_fts_doc_texts
Revises: 04_01_doc_texts
Create Date: 2026-08-16
Sprint 04 — Sub-passo 04-4 (RF-011, CA-011.6)
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "04_04_fts_doc_texts"
down_revision: Union[str, None] = "04_01_doc_texts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # document_id, original_filename e title são UNINDEXED:
    # armazenados para exibição nos resultados, mas não indexados para FTS.
    # Apenas validated_text é indexado (campo de busca full-text).
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_document_texts USING fts5(
            document_id    UNINDEXED,
            original_filename UNINDEXED,
            title          UNINDEXED,
            validated_text,
            tokenize='unicode61'
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fts_document_texts")
