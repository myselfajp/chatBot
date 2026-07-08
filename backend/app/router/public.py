import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.repository.bot import ConversationRepository
from app.schema.bot import (
    ChatInput,
    ChatOutput,
    MessageOut,
    PublicBotConfig,
    PublicHistory,
)
from app.service import llm
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
    """Non-secret config used by the embeddable widget."""
    bot = bot_service.bot_repo.get_by_public_key(db, public_key)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot_service.public_config(bot)


@router.get("/bots/{public_key}/history", response_model=PublicHistory)
def get_history(
    public_key: str,
    session_id: str,
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Return the message history for a visitor's session (persists across pages)."""
    bot = bot_service.bot_repo.get_by_public_key(db, public_key)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    convo = bot_service.conversation_repo.find_by_session(db, bot.id, session_id)
    messages = []
    if convo:
        messages = [
            MessageOut(role=m.role, content=m.content, created_at=m.created_at)
            for m in convo.messages
        ]
    return PublicHistory(session_id=session_id, messages=messages)


@router.post("/bots/{public_key}/chat", response_model=ChatOutput)
@limiter.limit("30/minute")
def chat(
    request: Request,
    public_key: str,
    payload: ChatInput,
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Non-streaming chat (kept for compatibility / fallback)."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    return bot_service.handle_chat(
        db=db,
        public_key=public_key,
        session_id=payload.session_id,
        message=payload.message,
        origin=origin,
    )


@router.post("/bots/{public_key}/chat/stream")
@limiter.limit("30/minute")
def chat_stream(
    request: Request,
    public_key: str,
    payload: ChatInput,
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Streaming chat via Server-Sent Events. Emits {"delta": "..."} events and a
    final {"done": true}; persists the full exchange after streaming completes."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    ctx = bot_service.prepare_chat(
        db, public_key, payload.session_id, payload.message, origin
    )

    def event_stream():
        parts = []
        try:
            for chunk in llm.generate_reply_stream(
                provider=ctx["provider"],
                model=ctx["model"],
                api_key=ctx["api_key"],
                system_prompt=ctx["system_prompt"],
                messages=ctx["messages"],
            ):
                parts.append(chunk)
                yield "data: " + json.dumps({"delta": chunk}) + "\n\n"
        except HTTPException as exc:
            yield "data: " + json.dumps({"error": str(exc.detail)}) + "\n\n"
            return
        except Exception:  # noqa: BLE001
            yield "data: " + json.dumps({"error": "Provider error."}) + "\n\n"
            return

        reply = "".join(parts).strip()
        if reply:
            _db = SessionLocal()
            try:
                ConversationRepository().add_exchange(
                    _db, ctx["conversation_id"], payload.message, reply
                )
            finally:
                _db.close()
        yield "data: " + json.dumps({"done": True}) + "\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
