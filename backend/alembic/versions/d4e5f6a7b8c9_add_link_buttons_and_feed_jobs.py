"""Add link_buttons to bots and the feed_jobs table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column("link_buttons", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "feed_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=False),
        sa.Column("sitemap_url", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("pages_total", sa.Integer(), nullable=False),
        sa.Column("pages_done", sa.Integer(), nullable=False),
        sa.Column("items_added", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feed_jobs_bot_id"), "feed_jobs", ["bot_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_feed_jobs_bot_id"), table_name="feed_jobs")
    op.drop_table("feed_jobs")
    op.drop_column("bots", "link_buttons")
