from fastapi import APIRouter, Depends

from app.model.user import User
from app.schema.auth import UserInfo
from app.service.deps import get_current_user

router = APIRouter(prefix="/v1", tags=["me"])


@router.get("/me", response_model=UserInfo)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user (used by the panel on load)."""
    return UserInfo.model_validate(current_user, from_attributes=True)
