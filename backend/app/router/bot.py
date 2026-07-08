from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.model.feed_job import FeedJob
from app.model.user import User
from app.schema.bot import (
    BotCreate,
    BotListItem,
    BotListResponse,
    BotOut,
    BotUpdate,
    FeedJobStatus,
    SitemapFeedInput,
)
from app.service.bot import BotService
from app.service.deps import get_bot_service, get_current_user
from app.service.sitemap import process_feed_job

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


@router.post("/{bot_id}/feed/sitemap", response_model=FeedJobStatus, status_code=202)
def start_sitemap_feed(
    bot_id: int,
    payload: SitemapFeedInput,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Start a background job that reads the sitemap and auto-generates feed
    Q&A (with sources) using the bot's configured LLM."""
    bot = bot_service.get_owned_bot(db, bot_id, current_user)

    # Require a usable active provider before spending time crawling.
    pconf = next((p for p in bot.providers if p.provider == bot.active_provider), None)
    if pconf is None or not pconf.enabled or not pconf.api_key_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Configure and enable a provider (model + API key) for this bot first.",
        )

    job = FeedJob(bot_id=bot.id, sitemap_url=payload.sitemap_url.strip(), status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(process_feed_job, job.id, payload.max_pages)
    return FeedJobStatus(
        id=job.id,
        status=job.status,
        sitemap_url=job.sitemap_url,
        message=job.message,
        pages_total=job.pages_total,
        pages_done=job.pages_done,
        items_added=job.items_added,
    )


@router.get("/{bot_id}/feed/jobs/{job_id}", response_model=FeedJobStatus)
def get_feed_job(
    bot_id: int,
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Poll the status of a sitemap feed job."""
    bot_service.get_owned_bot(db, bot_id, current_user)  # ownership check
    job = db.get(FeedJob, job_id)
    if not job or job.bot_id != bot_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return FeedJobStatus(
        id=job.id,
        status=job.status,
        sitemap_url=job.sitemap_url,
        message=job.message,
        pages_total=job.pages_total,
        pages_done=job.pages_done,
        items_added=job.items_added,
    )
