"""Current-user API key management API."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import UserApiKey

router = APIRouter(prefix="/api/users/me/api-keys", tags=["api-keys"])


class ApiKeyCreateRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1)
    base_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class ApiKeyResponse(BaseModel):
    id: str
    provider: str
    base_url: str | None
    is_active: bool
    masked_key: str


def _mask_key(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * max(len(value) - 4, 4)}{value[-4:]}"


def _to_response(record: UserApiKey) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=record.id,
        provider=record.provider,
        base_url=record.base_url,
        is_active=record.is_active,
        masked_key=_mask_key(record.api_key_enc),
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_current_user_api_keys(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[ApiKeyResponse]:
    result = await db.execute(select(UserApiKey).where(UserApiKey.user_id == auth.user_id, UserApiKey.org_id == auth.org_id).order_by(UserApiKey.created_at.desc()))
    return [_to_response(record) for record in result.scalars().all()]


@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_current_user_api_key(
    request: ApiKeyCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiKeyResponse:
    record = UserApiKey(
        user_id=auth.user_id,
        org_id=auth.org_id,
        provider=request.provider.strip(),
        api_key_enc=request.api_key,
        base_url=request.base_url.strip() if request.base_url else None,
        is_active=request.is_active,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _to_response(record)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user_api_key(
    key_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    result = await db.execute(select(UserApiKey).where(UserApiKey.id == key_id, UserApiKey.user_id == auth.user_id, UserApiKey.org_id == auth.org_id).limit(1))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(record)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
