"""add extraction columns

Revision ID: 002
Revises: 001
Create Date: 2026-05-25

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contract_files",
        sa.Column("extraction_result", sa.JSON(), nullable=True),
    )
    op.add_column(
        "contract_files",
        sa.Column("extraction_warnings", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contract_files", "extraction_warnings")
    op.drop_column("contract_files", "extraction_result")
