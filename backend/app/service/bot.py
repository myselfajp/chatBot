from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt, encrypt, mask_key
from app.model.bot import Bot
from app.model.bot_provider import BotProvider
from app.model.user import User
from app.repository.bot import (
    BotProviderRepository,
    BotRepository,
    ConversationRepository,
)
from app.schema.bot import (
    BotOut,
    BotUpdate,
    ChatOutput,
    ProviderConfigOut,
    PublicBotConfig,
)
from app.service import llm

CANONICAL_PROVIDERS = ("openai", "anthropic", "deepseek")


def paths_to_text(paths: Optional[List[str]]) -> str:
    if not paths:
        return ""
    cleaned = [p.strip() for p in paths if p and p.strip()]
    return "\n".join(cleaned)


def text_to_paths(text: str) -> List[str]:
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def host_of(value: str) -> str:
    """Normalized hostname (lowercase, no leading 'www.') from a URL or origin."""
    if not value:
        return ""
    s = value.strip()
    if not re.match(r"^https?://", s, re.IGNORECASE):
        s = "https://" + s
    try:
        host = urlparse(s).hostname or ""
    except ValueError:
        host = ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def domain_allows(site_url: str, request_host: str) -> bool:
    """Whether ``request_host`` is the configured domain or a subdomain of it."""
    want = host_of(site_url)
    if not want:  # no domain configured -> unrestricted
        return True
    have = request_host.lower()
    if have.startswith("www."):
        have = have[4:]
    return have == want or have.endswith("." + want)


class BotService:
    def __init__(
        self,
        bot_repo: Optional[BotRepository] = None,
        provider_repo: Optional[BotProviderRepository] = None,
        conversation_repo: Optional[ConversationRepository] = None,
    ):
        self.bot_repo = bot_repo or BotRepository()
        self.provider_repo = provider_repo or BotProviderRepository()
        self.conversation_repo = conversation_repo or ConversationRepository()

    # ----------------------------------------------------------------- #
    # CRUD
    # ----------------------------------------------------------------- #
    def create_bot(
        self, db: Session, user_id: int, name: str, site_url: str = ""
    ) -> Bot:
        bot = Bot(user_id=user_id, name=name or "My Chatbot", site_url=site_url or "")
        db.add(bot)
        db.flush()  # assign bot.id before creating provider rows
        for provider in CANONICAL_PROVIDERS:
            db.add(BotProvider(bot_id=bot.id, provider=provider, enabled=False))
        db.commit()
        db.refresh(bot)
        return bot

    def get_owned_bot(
        self, db: Session, bot_id: int, user: User
    ) -> Bot:
        """Fetch a bot, enforcing ownership (admins may access any bot)."""
        bot = self.bot_repo.get_with_providers(db, bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if not user.is_admin() and bot.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        return bot

    def list_bots(self, db: Session, user_id: int) -> List[Bot]:
        return list(self.bot_repo.list_by_user(db, user_id))

    def update_bot(self, db: Session, bot: Bot, payload: BotUpdate) -> Bot:
        # exclude_unset tells us which fields the client actually sent.
        provided = payload.model_dump(exclude_unset=True)

        # list fields come in as arrays -> store as newline text
        if "display_paths" in provided:
            bot.display_paths = paths_to_text(payload.display_paths)
        if "quick_replies" in provided:
            bot.quick_replies = paths_to_text(payload.quick_replies)

        simple_fields = {
            "name",
            "site_url",
            "display_mode",
            "system_prompt",
            "feed_data",
            "active_provider",
            "widget_title",
            "bot_subtitle",
            "logo_url",
            "welcome_message",
            "footer_text",
            "accent_color",
            "launcher_style",
            "launcher_icon_url",
            "is_active",
        }
        for field in simple_fields:
            if field in provided:
                value = getattr(payload, field)
                if value is not None:
                    setattr(bot, field, value)

        # Use the validated pydantic objects (not dumped dicts) for providers.
        if "providers" in provided and payload.providers is not None:
            self._apply_provider_updates(db, bot, payload.providers)

        db.add(bot)
        db.commit()
        db.refresh(bot)
        return bot

    def _apply_provider_updates(self, db: Session, bot: Bot, updates) -> None:
        existing = {p.provider: p for p in bot.providers}
        for upd in updates:
            provider = upd.provider  # already validated/lowercased by schema
            row = existing.get(provider)
            if row is None:
                row = BotProvider(bot_id=bot.id, provider=provider)
                db.add(row)
                existing[provider] = row
            row.enabled = upd.enabled
            row.model = (upd.model or "").strip()
            # api_key handling: None -> keep, "" -> clear, value -> set
            if upd.api_key is not None:
                row.api_key_encrypted = encrypt(upd.api_key.strip()) if upd.api_key.strip() else ""

    def delete_bot(self, db: Session, bot: Bot) -> None:
        db.delete(bot)
        db.commit()

    # ----------------------------------------------------------------- #
    # Serialization
    # ----------------------------------------------------------------- #
    def embed_snippet(self, public_key: str) -> str:
        base = settings.BASE_URL.rstrip("/")
        return (
            f'<script src="{base}/widget/chatbot-widget.js" '
            f'data-bot-key="{public_key}" defer></script>'
        )

    def to_out(self, bot: Bot) -> BotOut:
        by_provider = {p.provider: p for p in bot.providers}
        providers_out: List[ProviderConfigOut] = []
        for provider in CANONICAL_PROVIDERS:
            row = by_provider.get(provider)
            if row is None:
                providers_out.append(
                    ProviderConfigOut(
                        provider=provider,
                        enabled=False,
                        model="",
                        has_key=False,
                        key_hint="",
                    )
                )
            else:
                providers_out.append(
                    ProviderConfigOut(
                        provider=provider,
                        enabled=row.enabled,
                        model=row.model,
                        has_key=bool(row.api_key_encrypted),
                        key_hint=mask_key(row.api_key_encrypted),
                    )
                )

        return BotOut(
            id=bot.id,
            public_key=bot.public_key,
            name=bot.name,
            site_url=bot.site_url,
            display_mode=bot.display_mode,
            display_paths=text_to_paths(bot.display_paths),
            system_prompt=bot.system_prompt,
            feed_data=bot.feed_data,
            active_provider=bot.active_provider,
            widget_title=bot.widget_title,
            bot_subtitle=bot.bot_subtitle,
            logo_url=bot.logo_url,
            welcome_message=bot.welcome_message,
            quick_replies=text_to_paths(bot.quick_replies),
            footer_text=bot.footer_text,
            accent_color=bot.accent_color,
            launcher_style=bot.launcher_style,
            launcher_icon_url=bot.launcher_icon_url,
            is_active=bot.is_active,
            providers=providers_out,
            embed_snippet=self.embed_snippet(bot.public_key),
            created_at=bot.created_at,
            updated_at=bot.updated_at,
        )

    def public_config(self, bot: Bot) -> PublicBotConfig:
        return PublicBotConfig(
            public_key=bot.public_key,
            name=bot.name,
            site_url=bot.site_url,
            display_mode=bot.display_mode,
            display_paths=text_to_paths(bot.display_paths),
            widget_title=bot.widget_title,
            bot_subtitle=bot.bot_subtitle,
            logo_url=bot.logo_url,
            welcome_message=bot.welcome_message,
            quick_replies=text_to_paths(bot.quick_replies),
            footer_text=bot.footer_text,
            accent_color=bot.accent_color,
            launcher_style=bot.launcher_style,
            launcher_icon_url=bot.launcher_icon_url,
            is_active=bot.is_active,
        )

    # ----------------------------------------------------------------- #
    # Chat
    # ----------------------------------------------------------------- #
    def _build_system_prompt(self, bot: Bot) -> str:
        parts: List[str] = []
        base_prompt = (bot.system_prompt or "").strip()
        parts.append(
            base_prompt or "You are a helpful assistant embedded on a website."
        )
        if bot.site_url:
            parts.append(f"You are the assistant for the website: {bot.site_url}.")

        feed = (bot.feed_data or "").strip()[: settings.FEED_DATA_MAX_CHARS]
        if feed:
            parts.append(
                "Use the following source data as your primary knowledge base. "
                "Prefer it over any prior knowledge. If the answer is not contained "
                "in this data, say that you don't have that information.\n"
                "--- SOURCE DATA ---\n"
                f"{feed}\n"
                "--- END SOURCE DATA ---"
            )
        return "\n\n".join(parts)

    def _origin_allowed(self, bot: Bot, origin: Optional[str]) -> bool:
        """Enforce that chat requests come from the bot's configured domain.

        - No site_url configured -> allowed (unrestricted).
        - No browser Origin/Referer (e.g. curl, server-side, same-origin panel
          tester) -> allowed; domain-locking targets browser embedding on other
          sites, which always sends an Origin header.
        - The panel origin (FRONTEND_URL) is always allowed so owners can test.
        """
        if not bot.site_url:
            return True
        request_host = host_of(origin) if origin else ""
        if not request_host:
            return True
        if domain_allows(bot.site_url, request_host):
            return True
        front_host = host_of(settings.FRONTEND_URL)
        if front_host and (
            request_host == front_host or request_host.endswith("." + front_host)
        ):
            return True
        return False

    def handle_chat(
        self,
        db: Session,
        public_key: str,
        session_id: str,
        message: str,
        origin: Optional[str] = None,
    ) -> ChatOutput:
        bot = self.bot_repo.get_by_public_key(db, public_key)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        if not bot.is_active:
            raise HTTPException(status_code=403, detail="This chatbot is currently disabled.")

        if not self._origin_allowed(bot, origin):
            raise HTTPException(
                status_code=403,
                detail="This chatbot is not authorized to run on this domain.",
            )

        provider = bot.active_provider
        pconf = next((p for p in bot.providers if p.provider == provider), None)
        if pconf is None or not pconf.enabled:
            raise HTTPException(
                status_code=400,
                detail="This chatbot is not fully configured yet.",
            )
        api_key = decrypt(pconf.api_key_encrypted)
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="This chatbot is not fully configured yet.",
            )

        convo = self.conversation_repo.get_or_create(db, bot.id, session_id)
        history = self.conversation_repo.recent_messages(
            db, convo.id, settings.CHAT_HISTORY_LIMIT
        )
        messages = [{"role": m.role, "content": m.content} for m in history]
        # Drop a trailing orphaned user message so roles alternate cleanly
        # (required by providers like Anthropic).
        if messages and messages[-1]["role"] == "user":
            messages.pop()
        messages.append({"role": "user", "content": message})

        system_prompt = self._build_system_prompt(bot)
        reply = llm.generate_reply(
            provider=provider,
            model=pconf.model,
            api_key=api_key,
            system_prompt=system_prompt,
            messages=messages,
        )

        # Persist the exchange atomically, only after a successful reply.
        self.conversation_repo.add_exchange(db, convo.id, message, reply)

        return ChatOutput(reply=reply, session_id=session_id)
