from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

DISPLAY_MODES = ("all", "all_except", "only")
PROVIDERS = ("openai", "anthropic", "deepseek")
LAUNCHER_STYLES = ("circle", "icon", "bar")


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #
class ProviderConfigInput(BaseModel):
    """Provider config sent from the panel when saving a bot."""

    provider: str
    enabled: bool = False
    model: str = Field(default="", max_length=120)
    # New API key. If None/omitted, the existing stored key is kept.
    # Send "" explicitly to clear the key.
    api_key: Optional[str] = Field(default=None, max_length=500)

    @field_validator("provider")
    @classmethod
    def _valid_provider(cls, v: str) -> str:
        v = (v or "").lower().strip()
        if v not in PROVIDERS:
            raise ValueError(f"provider must be one of {', '.join(PROVIDERS)}")
        return v


class ProviderConfigOut(BaseModel):
    """Provider config returned to the panel (never exposes the raw key)."""

    provider: str
    enabled: bool
    model: str
    has_key: bool
    key_hint: str = ""


# --------------------------------------------------------------------------- #
# Link buttons (navigation buttons shown in the widget)
# --------------------------------------------------------------------------- #
class LinkButton(BaseModel):
    text: str = Field(..., max_length=60)
    slug: str = Field(..., max_length=500)  # e.g. "/contact" or a full URL


# --------------------------------------------------------------------------- #
# Bot create / update
# --------------------------------------------------------------------------- #
class BotCreate(BaseModel):
    name: str = Field(default="My Chatbot", max_length=255)
    site_url: str = Field(default="", max_length=500)


class BotUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    site_url: Optional[str] = Field(default=None, max_length=500)
    display_mode: Optional[str] = None
    display_paths: Optional[List[str]] = None
    system_prompt: Optional[str] = None
    feed_data: Optional[str] = None
    active_provider: Optional[str] = None
    widget_title: Optional[str] = Field(default=None, max_length=120)
    bot_subtitle: Optional[str] = Field(default=None, max_length=120)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    welcome_message: Optional[str] = None
    quick_replies: Optional[List[str]] = None
    link_buttons: Optional[List[LinkButton]] = None
    footer_text: Optional[str] = None
    accent_color: Optional[str] = Field(default=None, max_length=20)
    launcher_style: Optional[str] = None
    launcher_icon_url: Optional[str] = Field(default=None, max_length=500)
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None
    is_active: Optional[bool] = None
    providers: Optional[List[ProviderConfigInput]] = None

    @field_validator("launcher_style")
    @classmethod
    def _valid_launcher(cls, v):
        if v is not None and v not in LAUNCHER_STYLES:
            raise ValueError(
                f"launcher_style must be one of {', '.join(LAUNCHER_STYLES)}"
            )
        return v

    @field_validator("display_mode")
    @classmethod
    def _valid_mode(cls, v):
        if v is not None and v not in DISPLAY_MODES:
            raise ValueError(f"display_mode must be one of {', '.join(DISPLAY_MODES)}")
        return v

    @field_validator("active_provider")
    @classmethod
    def _valid_active(cls, v):
        if v is not None:
            v = v.lower().strip()
            if v not in PROVIDERS:
                raise ValueError(f"active_provider must be one of {', '.join(PROVIDERS)}")
        return v


# --------------------------------------------------------------------------- #
# Bot output
# --------------------------------------------------------------------------- #
class BotOut(BaseModel):
    id: int
    public_key: str
    name: str
    site_url: str
    display_mode: str
    display_paths: List[str]
    system_prompt: str
    feed_data: str
    active_provider: str
    widget_title: str
    bot_subtitle: str
    logo_url: str
    welcome_message: str
    quick_replies: List[str]
    link_buttons: List[LinkButton]
    footer_text: str
    accent_color: str
    launcher_style: str
    launcher_icon_url: str
    custom_css: str
    custom_js: str
    is_active: bool
    providers: List[ProviderConfigOut]
    embed_snippet: str
    created_at: datetime
    updated_at: datetime


class BotListItem(BaseModel):
    id: int
    public_key: str
    name: str
    site_url: str
    is_active: bool
    active_provider: str
    created_at: datetime
    updated_at: datetime


class BotListResponse(BaseModel):
    status: str = "success"
    data: List[BotListItem]
    total: int


# Admin listing includes owner info
class AdminBotListItem(BotListItem):
    user_id: int
    owner_email: str


class AdminBotListResponse(BaseModel):
    status: str = "success"
    data: List[AdminBotListItem]
    total: int


# --------------------------------------------------------------------------- #
# Public (widget) schemas
# --------------------------------------------------------------------------- #
class PublicBotConfig(BaseModel):
    """Non-secret config the widget needs to decide whether/how to render."""

    public_key: str
    name: str
    site_url: str
    display_mode: str
    display_paths: List[str]
    widget_title: str
    bot_subtitle: str
    logo_url: str
    welcome_message: str
    quick_replies: List[str]
    link_buttons: List[LinkButton]
    footer_text: str
    accent_color: str
    launcher_style: str
    launcher_icon_url: str
    custom_css: str
    custom_js: str
    is_active: bool


# --------------------------------------------------------------------------- #
# Chat history / conversations
# --------------------------------------------------------------------------- #
class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime


class PublicHistory(BaseModel):
    session_id: str
    messages: List[MessageOut]


class ConversationSummary(BaseModel):
    id: str
    session_id: str
    message_count: int
    preview: str
    created_at: datetime
    last_message_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    status: str = "success"
    data: List[ConversationSummary]
    total: int


class ConversationDetail(BaseModel):
    id: str
    session_id: str
    created_at: datetime
    messages: List[MessageOut]


# --------------------------------------------------------------------------- #
# Style assistant (helper that only writes widget CSS/JS)
# --------------------------------------------------------------------------- #
class StyleChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class StyleAssistantInput(BaseModel):
    messages: List[StyleChatMessage]


class StyleAssistantOutput(BaseModel):
    reply: str


# --------------------------------------------------------------------------- #
# Feed-from-sitemap job
# --------------------------------------------------------------------------- #
class SitemapFeedInput(BaseModel):
    sitemap_url: str = Field(..., max_length=1000)
    max_pages: int = Field(default=15, ge=1, le=200)
    # URL patterns to skip, e.g. "/blog/*" or "https://example.com/blog/*".
    exclude: List[str] = Field(default_factory=list)


class FeedJobStatus(BaseModel):
    id: str
    status: str  # queued | running | done | error | stopped | cancelled
    control: str = ""
    sitemap_url: str
    message: str
    pages_total: int
    pages_done: int
    items_added: int


class ChatInput(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=4000)


class ChatOutput(BaseModel):
    reply: str
    session_id: str
