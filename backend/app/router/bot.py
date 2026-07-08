from fastapi import APIRouter, Depends, HTTPException, Query
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
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    FeedJobStatus,
    MessageOut,
    SitemapFeedInput,
    StyleAssistantInput,
    StyleAssistantOutput,
)
from app.service.bot import BotService
from app.service.deps import get_bot_service, get_current_user
from app.service.sitemap import process_feed_job

router = APIRouter(prefix="/v1/bots", tags=["bots"])


def _job_status(job: FeedJob) -> FeedJobStatus:
    return FeedJobStatus(
        id=job.id,
        status=job.status,
        control=job.control,
        sitemap_url=job.sitemap_url,
        message=job.message,
        pages_total=job.pages_total,
        pages_done=job.pages_done,
        items_added=job.items_added,
    )


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Queue a Celery job that reads the sitemap and auto-generates feed Q&A
    (with sources) using the bot's configured LLM."""
    bot = bot_service.get_owned_bot(db, bot_id, current_user)

    pconf = next((p for p in bot.providers if p.provider == bot.active_provider), None)
    if pconf is None or not pconf.enabled or not pconf.api_key_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Configure and enable a provider (model + API key) for this bot first.",
        )

    job = FeedJob(bot_id=bot.id, sitemap_url=payload.sitemap_url.strip(), status="queued")
    db.add(job)
    db.commit()
    job_id = job.id  # populated by the uuid default; no refresh needed

    process_feed_job.delay(job_id, payload.max_pages, payload.exclude)
    return _job_status(job)


@router.get("/{bot_id}/feed/jobs/{job_id}", response_model=FeedJobStatus)
def get_feed_job(
    bot_id: int,
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Poll the status/progress of a sitemap feed job."""
    bot_service.get_owned_bot(db, bot_id, current_user)
    job = db.get(FeedJob, job_id)
    if not job or job.bot_id != bot_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_status(job)


def _set_job_control(db, bot_service, bot_id, job_id, current_user, control):
    bot_service.get_owned_bot(db, bot_id, current_user)
    job = db.get(FeedJob, job_id)
    if not job or job.bot_id != bot_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("done", "error", "stopped", "cancelled"):
        return job  # already finished; nothing to control
    job.control = control
    db.commit()
    db.refresh(job)
    return job


@router.post("/{bot_id}/feed/jobs/{job_id}/stop", response_model=FeedJobStatus)
def stop_feed_job(
    bot_id: int,
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Stop the crawl but keep everything gathered so far."""
    return _job_status(_set_job_control(db, bot_service, bot_id, job_id, current_user, "stop"))


@router.post("/{bot_id}/feed/jobs/{job_id}/cancel", response_model=FeedJobStatus)
def cancel_feed_job(
    bot_id: int,
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Cancel the crawl and discard whatever was gathered."""
    return _job_status(_set_job_control(db, bot_service, bot_id, job_id, current_user, "cancel"))


# --------------------------------------------------------------------------- #
# Conversations (owner view of what people asked)
# --------------------------------------------------------------------------- #
@router.get("/{bot_id}/conversations", response_model=ConversationListResponse)
def list_conversations(
    bot_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    bot_service.get_owned_bot(db, bot_id, current_user)
    convos, total = bot_service.conversation_repo.list_for_bot(db, bot_id, page, limit)
    items = []
    for c in convos:
        msgs = c.messages
        first_user = next((m for m in msgs if m.role == "user"), None)
        preview = (first_user.content if first_user else (msgs[0].content if msgs else ""))[:120]
        items.append(
            ConversationSummary(
                id=c.id,
                session_id=c.session_id,
                message_count=len(msgs),
                preview=preview,
                created_at=c.created_at,
                last_message_at=msgs[-1].created_at if msgs else None,
            )
        )
    return ConversationListResponse(data=items, total=total)


@router.get("/{bot_id}/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    bot_id: int,
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    bot_service.get_owned_bot(db, bot_id, current_user)
    convo = bot_service.conversation_repo.get_detail(db, conversation_id)
    if not convo or convo.bot_id != bot_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(
        id=convo.id,
        session_id=convo.session_id,
        created_at=convo.created_at,
        messages=[
            MessageOut(role=m.role, content=m.content, created_at=m.created_at)
            for m in convo.messages
        ],
    )


# --------------------------------------------------------------------------- #
# Style assistant (helper that only writes widget CSS/JS)
# --------------------------------------------------------------------------- #
@router.post("/{bot_id}/style-assistant", response_model=StyleAssistantOutput)
def style_assistant(
    bot_id: int,
    payload: StyleAssistantInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """A helper agent (uses the bot's provider) that only helps write widget CSS/JS."""
    bot = bot_service.get_owned_bot(db, bot_id, current_user)
    reply = bot_service.style_assistant_reply(db, bot, payload.messages)
    return StyleAssistantOutput(reply=reply)
