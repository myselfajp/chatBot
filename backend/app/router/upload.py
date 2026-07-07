import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.model.user import User
from app.service.bot import BotService
from app.service.deps import get_bot_service, get_current_user

router = APIRouter(prefix="/v1/bots", tags=["bots"])

# Raster image types only (SVG is excluded to avoid stored-XSS via embedded scripts).
_ALLOWED = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
}
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB

# app/static/uploads
_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "uploads"
)


@router.post("/{bot_id}/upload")
def upload_asset(
    bot_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot_service: BotService = Depends(get_bot_service),
):
    """Upload a logo / launcher icon for a bot (owner or admin).

    Stores the image under /static/uploads and returns its public URL, which
    the panel then saves into logo_url / launcher_icon_url.
    """
    # Authorization: must own the bot (admins bypass).
    bot_service.get_owned_bot(db, bot_id, current_user)

    ext = _ALLOWED.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use PNG, JPG, GIF or WEBP.",
        )

    contents = file.file.read()
    if len(contents) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 2 MB).")
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file.")

    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    filename = uuid.uuid4().hex + "." + ext
    with open(os.path.join(_UPLOAD_DIR, filename), "wb") as f:
        f.write(contents)

    base = settings.BASE_URL.rstrip("/")
    return {"url": f"{base}/uploads/{filename}"}
