"""Current-user soul management API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import UserSoul

router = APIRouter(prefix="/api/users/me/soul", tags=["soul"])


class SoulResponse(BaseModel):
    content: str = Field(default="")


class SoulUpdateRequest(BaseModel):
    content: str = Field(default="")


@router.get("", response_model=SoulResponse)
async def get_current_user_soul(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SoulResponse:
    result = await db.execute(select(UserSoul).where(UserSoul.user_id == auth.user_id, UserSoul.org_id == auth.org_id).order_by(UserSoul.updated_at.desc()).limit(1))
    soul = result.scalar_one_or_none()
    if soul is None:
        return SoulResponse(content="")
    return SoulResponse(content=soul.content)


@router.put("", response_model=SoulResponse)
async def update_current_user_soul(
    request: SoulUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SoulResponse:
    result = await db.execute(select(UserSoul).where(UserSoul.user_id == auth.user_id, UserSoul.org_id == auth.org_id).order_by(UserSoul.updated_at.desc()).limit(1))
    soul = result.scalar_one_or_none()
    if soul is None:
        soul = UserSoul(user_id=auth.user_id, org_id=auth.org_id, content=request.content)
        db.add(soul)
    else:
        soul.content = request.content

    await db.commit()
    await db.refresh(soul)
    return SoulResponse(content=soul.content)
