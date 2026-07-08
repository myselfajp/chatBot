"""Add custom_css/custom_js to bots and control to feed_jobs

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bots", sa.Column("custom_css", sa.Text(), nullable=False, server_default=""))
    op.add_column("bots", sa.Column("custom_js", sa.Text(), nullable=False, server_default=""))
    op.add_column("feed_jobs", sa.Column("control", sa.String(length=20), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("feed_jobs", "control")
    op.drop_column("bots", "custom_js")
    op.drop_column("bots", "custom_css")
