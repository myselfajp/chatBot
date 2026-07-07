"""Add bot appearance fields: bot_subtitle, logo_url, quick_replies, footer_text

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-05 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column("bot_subtitle", sa.String(length=120), nullable=False, server_default=""),
    )
    op.add_column(
        "bots",
        sa.Column("logo_url", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "bots",
        sa.Column("quick_replies", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "bots",
        sa.Column("footer_text", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("bots", "footer_text")
    op.drop_column("bots", "quick_replies")
    op.drop_column("bots", "logo_url")
    op.drop_column("bots", "bot_subtitle")
