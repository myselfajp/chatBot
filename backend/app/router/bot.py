from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.model.user import User
from app.schema.bot import (
    BotCreate,
    BotListItem,
    BotListResponse,
    BotOut,
    BotUpdate,
)
from app.service.bot import BotService
from app.service.deps import get_bot_service, get_current_user

router = APIRouter(prefix="/v1/bots", tags=["bots"])


@router.get("", response_model=BotListResponse)
def list_my_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """List the current user's chatbots."""
    bots = bot_service.list_bots(db, current_user.id)
    items = [BotListItem.model_validate(b, from_attributes=True) for b in bots]
    return BotListResponse(data=items, total=len(items))


@router.post("", response_model=BotOut, status_code=201)
def create_bot(
    payload: BotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Create a new chatbot for the current user."""
    bot = bot_service.create_bot(
        db, user_id=current_user.id, name=payload.name, site_url=payload.site_url
    )
    # reload with providers for full serialization
    bot = bot_service.get_owned_bot(db, bot.id, current_user)
    return bot_service.to_out(bot)


@router.get("/{bot_id}", response_model=BotOut)
def get_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Get full details of a bot (owner or admin only)."""
    bot = bot_service.get_owned_bot(db, bot_id, current_user)
    return bot_service.to_out(bot)


@router.put("/{bot_id}", response_model=BotOut)
def update_bot(
    bot_id: int,
    payload: BotUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Update a bot's configuration, prompt, feed data and providers."""
    bot = bot_service.get_owned_bot(db, bot_id, current_user)
    bot = bot_service.update_bot(db, bot, payload)
    return bot_service.to_out(bot)


@router.delete("/{bot_id}", status_code=204)
def delete_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Delete a bot (owner or admin only)."""
    bot = bot_service.get_owned_bot(db, bot_id, current_user)
    bot_service.delete_bot(db, bot)
    return None
