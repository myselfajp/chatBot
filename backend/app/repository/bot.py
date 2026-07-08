from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session, selectinload

from app.model.bot import Bot
from app.model.bot_provider import BotProvider
from app.model.conversation import Conversation
from app.model.message import Message
from app.model.user import User
from .base import BaseRepository


class BotRepository(BaseRepository[Bot]):
    def __init__(self):
        super().__init__(Bot, resource_name="Bot")

    def get_with_providers(self, db: Session, bot_id: int) -> Optional[Bot]:
        stmt = (
            select(Bot)
            .where(Bot.id == bot_id)
            .options(selectinload(Bot.providers))
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_public_key(self, db: Session, public_key: str) -> Optional[Bot]:
        stmt = (
            select(Bot)
            .where(Bot.public_key == public_key)
            .options(selectinload(Bot.providers))
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_user(self, db: Session, user_id: int) -> Sequence[Bot]:
        stmt = (
            select(Bot)
            .where(Bot.user_id == user_id)
            .order_by(desc(Bot.created_at))
        )
        return db.execute(stmt).scalars().all()

    def list_all_with_owner(
        self, db: Session, page: int = 1, limit: int = 50
    ) -> Tuple[List[Tuple[Bot, str]], int]:
        total = db.execute(select(func.count()).select_from(Bot)).scalar_one()
        offset = (page - 1) * limit
        stmt = (
            select(Bot, User.email)
            .join(User, User.id == Bot.user_id)
            .order_by(desc(Bot.created_at))
            .limit(limit)
            .offset(offset)
        )
        rows = db.execute(stmt).all()
        return [(row[0], row[1]) for row in rows], total


class BotProviderRepository(BaseRepository[BotProvider]):
    def __init__(self):
        super().__init__(BotProvider, resource_name="BotProvider")

    def get_for_bot(
        self, db: Session, bot_id: int, provider: str
    ) -> Optional[BotProvider]:
        stmt = select(BotProvider).where(
            BotProvider.bot_id == bot_id, BotProvider.provider == provider
        )
        return db.execute(stmt).scalar_one_or_none()


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self):
        super().__init__(Conversation, resource_name="Conversation")

    def get_or_create(
        self, db: Session, bot_id: int, session_id: str
    ) -> Conversation:
        stmt = select(Conversation).where(
            Conversation.bot_id == bot_id,
            Conversation.session_id == session_id,
        )
        convo = db.execute(stmt).scalar_one_or_none()
        if convo is None:
            convo = Conversation(bot_id=bot_id, session_id=session_id)
            db.add(convo)
            db.commit()
            db.refresh(convo)
        return convo

    def find_by_session(
        self, db: Session, bot_id: int, session_id: str
    ) -> Optional[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.bot_id == bot_id, Conversation.session_id == session_id)
            .options(selectinload(Conversation.messages))
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_detail(self, db: Session, conversation_id: str) -> Optional[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_for_bot(
        self, db: Session, bot_id: int, page: int = 1, limit: int = 30
    ) -> Tuple[List[Conversation], int]:
        total = db.execute(
            select(func.count()).select_from(Conversation).where(Conversation.bot_id == bot_id)
        ).scalar_one()
        offset = (page - 1) * limit
        stmt = (
            select(Conversation)
            .where(Conversation.bot_id == bot_id)
            .options(selectinload(Conversation.messages))
            .order_by(desc(Conversation.created_at))
            .limit(limit)
            .offset(offset)
        )
        convos = list(db.execute(stmt).scalars().all())
        return convos, total

    def recent_messages(
        self, db: Session, conversation_id: str, limit: int
    ) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        rows = db.execute(stmt).scalars().all()
        return list(reversed(rows))

    def add_message(
        self, db: Session, conversation_id: str, role: str, content: str
    ) -> Message:
        msg = Message(conversation_id=conversation_id, role=role, content=content)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    def add_exchange(
        self,
        db: Session,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
    ) -> None:
        """Persist the user message and assistant reply atomically (one commit)
        so a failure can never orphan a user message without its reply."""
        db.add(Message(conversation_id=conversation_id, role="user", content=user_content))
        db.add(
            Message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
            )
        )
        db.commit()
