"""add lock and share xlsx paths

Revision ID: 004
Revises: 003
Create Date: 2026-05-25

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contract_files", sa.Column("lock_xlsx_path", sa.Text(), nullable=True))
    op.add_column("contract_files", sa.Column("share_xlsx_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("contract_files", "share_xlsx_path")
    op.drop_column("contract_files", "lock_xlsx_path")
