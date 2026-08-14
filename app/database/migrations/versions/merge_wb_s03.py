"""merge_workbench_and_sprint03

Revision ID: merge_wb_s03
Revises: at0307_platea_exclude, 03_02_ir_person_links
Create Date: 2026-08-13 22:00:00.000000

Une os dois heads divergentes:
  - at0307_platea_exclude (WORKBENCH / AT-03.7)
  - 03_02_ir_person_links (Sprint 03 / RF-009)
Nenhuma alteracao de schema — apenas encadeamento.
"""
from typing import Sequence, Union

revision: str = "merge_wb_s03"
down_revision: Union[str, tuple] = ("at0307_platea_exclude", "03_02_ir_person_links")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
