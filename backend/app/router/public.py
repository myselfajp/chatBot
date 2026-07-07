from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schema.bot import ChatInput, ChatOutput, PublicBotConfig
from app.service.bot import BotService
from app.service.deps import get_bot_service

router = APIRouter(prefix="/v1/public", tags=["public"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/bots/{public_key}/config", response_model=PublicBotConfig)
def get_public_config(
    public_key: str,
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """
    Non-secret config used by the embeddable widget to decide whether and how
    to render. Never exposes the prompt, feed data or API keys.
    """
    bot = bot_service.bot_repo.get_by_public_key(db, public_key)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot_service.public_config(bot)


@router.post("/bots/{public_key}/chat", response_model=ChatOutput)
@limiter.limit("30/minute")
def chat(
    request: Request,
    public_key: str,
    payload: ChatInput,
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """
    Public chat endpoint used by the widget. Rate limited per IP.
    Builds the system prompt from the bot's prompt + feed data, calls the
    configured provider, stores the exchange and returns the reply.
    Enforces that the request comes from the bot's configured domain.
    """
    origin = request.headers.get("origin") or request.headers.get("referer")
    return bot_service.handle_chat(
        db=db,
        public_key=public_key,
        session_id=payload.session_id,
        message=payload.message,
        origin=origin,
    )
