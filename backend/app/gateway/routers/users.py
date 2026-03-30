"""Current-user profile APIs."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import User

router = APIRouter(prefix="/api/users", tags=["users"])


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    avatar_url: str | None
    locale: str
    is_active: bool
    org_id: str


class UpdateUserProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=512)
    locale: str | None = Field(default=None, max_length=10)


def _build_profile_response(user: User, org_id: str) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        locale=user.locale,
        is_active=user.is_active,
        org_id=org_id,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    user = await db.get(User, auth.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _build_profile_response(user, auth.org_id)


@router.put("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    request: UpdateUserProfileRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    user = await db.get(User, auth.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if request.display_name is not None:
        user.display_name = request.display_name.strip() or None
    if request.avatar_url is not None:
        user.avatar_url = request.avatar_url.strip() or None
    if request.locale is not None:
        locale = request.locale.strip()
        if not locale:
            raise HTTPException(status_code=422, detail="Locale cannot be empty")
        user.locale = locale

    await db.commit()
    await db.refresh(user)
    return _build_profile_response(user, auth.org_id)
