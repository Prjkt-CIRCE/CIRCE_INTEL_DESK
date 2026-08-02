"""
CIRCE Intel Desk — Modelo OrgOrgLink (vínculo organização ↔ organização).

Referência: 05_MODELO_DE_DADOS.md §3.6, RF-006.
Tipos de relação: rivalidade, alianca, dissidencia, fusao, outra.

Constraint CHECK(org_a_id != org_b_id) impede que uma organização
se vincule a si mesma (CA-006.5).

Sprint 01-B — Sub-passo B1.
"""
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrgOrgLink(Base):
    """Relação entre duas organizações criminosas."""

    __tablename__ = "org_org_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_a_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    org_b_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )

    # rivalidade | alianca | dissidencia | fusao | outra
    relation_type: Mapped[str] = mapped_column(String, nullable=False)

    period_start: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    period_end: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reliability_level: Mapped[str] = mapped_column(
        String, default="pending", nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint("org_a_id != org_b_id", name="ck_org_org_different"),
        Index("idx_ool_org_a", "org_a_id"),
        Index("idx_ool_org_b", "org_b_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<OrgOrgLink id={self.id} org_a={self.org_a_id} "
            f"org_b={self.org_b_id} relation={self.relation_type!r}>"
        )