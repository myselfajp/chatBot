"""Add chatbot tables: bots, bot_providers, conversations, messages

Revision ID: a1b2c3d4e5f6
Revises: bb1acd0f6f91
Create Date: 2026-07-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "bb1acd0f6f91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # bots
    op.create_table(
        "bots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_key", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("site_url", sa.String(length=500), nullable=False),
        sa.Column("display_mode", sa.String(length=20), nullable=False),
        sa.Column("display_paths", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("feed_data", sa.Text(), nullable=False),
        sa.Column("active_provider", sa.String(length=20), nullable=False),
        sa.Column("widget_title", sa.String(length=120), nullable=False),
        sa.Column("welcome_message", sa.Text(), nullable=False),
        sa.Column("accent_color", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bots_id"), "bots", ["id"], unique=False)
    op.create_index(op.f("ix_bots_public_key"), "bots", ["public_key"], unique=True)
    op.create_index(op.f("ix_bots_user_id"), "bots", ["user_id"], unique=False)

    # bot_providers
    op.create_table(
        "bot_providers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id", "provider", name="uq_bot_provider"),
    )
    op.create_index(op.f("ix_bot_providers_id"), "bot_providers", ["id"], unique=False)
    op.create_index(
        op.f("ix_bot_providers_bot_id"), "bot_providers", ["bot_id"], unique=False
    )

    # conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversations_bot_id"), "conversations", ["bot_id"], unique=False
    )
    op.create_index(
        op.f("ix_conversations_session_id"),
        "conversations",
        ["session_id"],
        unique=False,
    )

    # messages
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_id"), "messages", ["id"], unique=False)
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(op.f("ix_conversations_session_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_bot_id"), table_name="conversations")
    op.drop_table("conversations")

    op.drop_index(op.f("ix_bot_providers_bot_id"), table_name="bot_providers")
    op.drop_index(op.f("ix_bot_providers_id"), table_name="bot_providers")
    op.drop_table("bot_providers")

    op.drop_index(op.f("ix_bots_user_id"), table_name="bots")
    op.drop_index(op.f("ix_bots_public_key"), table_name="bots")
    op.drop_index(op.f("ix_bots_id"), table_name="bots")
    op.drop_table("bots")
