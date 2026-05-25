"""add export xlsx paths

Revision ID: 003
Revises: 002
Create Date: 2026-05-25

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contract_files", sa.Column("product_xlsx_path", sa.Text(), nullable=True))
    op.add_column("contract_files", sa.Column("fee_xlsx_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("contract_files", "fee_xlsx_path")
    op.drop_column("contract_files", "product_xlsx_path")
