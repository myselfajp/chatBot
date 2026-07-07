"""Add launcher fields: launcher_style, launcher_icon_url

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column(
            "launcher_style",
            sa.String(length=20),
            nullable=False,
            server_default="circle",
        ),
    )
    op.add_column(
        "bots",
        sa.Column(
            "launcher_icon_url",
            sa.String(length=500),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("bots", "launcher_icon_url")
    op.drop_column("bots", "launcher_style")
