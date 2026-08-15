"""add document_texts table

Sprint 04 — RF-011 (OCR e Documentos)
CA-011.4: validation_status nasce como 'pending'
CA-011.5: arquivo original nunca é alterado (tabela só armazena texto extraído)

Revision ID: 04_01_doc_texts
Revises: b64e192e1de0
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "04_01_doc_texts"
down_revision = "b64e192e1de0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_texts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("engine", sa.String(length=20), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("validated_text", sa.Text(), nullable=True),
        sa.Column(
            "ocr_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "validation_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("validated_by", sa.Integer(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["validated_by"],
            ["users.id"],
        ),
        sa.UniqueConstraint("document_id", name="uq_document_texts_document_id"),
    )
    op.create_index("ix_document_texts_id", "document_texts", ["id"])
    op.create_index(
        "ix_document_texts_document_id", "document_texts", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_document_texts_document_id", table_name="document_texts")
    op.drop_index("ix_document_texts_id", table_name="document_texts")
    op.drop_table("document_texts")
