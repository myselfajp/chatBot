from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.model.user import User
from app.schema.bot import AdminBotListItem, AdminBotListResponse
from app.service.bot import BotService
from app.service.deps import get_bot_service, get_current_admin_user

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/bots", response_model=AdminBotListResponse)
def list_all_bots(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """List every bot in the system with its owner (admin only)."""
    rows, total = bot_service.bot_repo.list_all_with_owner(db, page=page, limit=limit)
    items = []
    for bot, owner_email in rows:
        items.append(
            AdminBotListItem(
                id=bot.id,
                public_key=bot.public_key,
                name=bot.name,
                site_url=bot.site_url,
                is_active=bot.is_active,
                active_provider=bot.active_provider,
                created_at=bot.created_at,
                updated_at=bot.updated_at,
                user_id=bot.user_id,
                owner_email=owner_email,
            )
        )
    return AdminBotListResponse(data=items, total=total)
