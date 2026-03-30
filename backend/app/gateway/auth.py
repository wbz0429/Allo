"""Authentication helpers for the Allo gateway."""

import logging
import os
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.db.database import get_db_session
from app.gateway.db.models import OrganizationMember, Session, User
from app.gateway.redis_client import get_redis

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "session_token"
SESSION_CACHE_TTL_SECONDS = 300


def _get_runtime_env() -> str:
    return os.getenv("ENV", os.getenv("NODE_ENV", "development")).lower()


def _get_runtime_skip_auth() -> bool:
    env_name = _get_runtime_env()
    skip_auth_raw = os.getenv("SKIP_AUTH", "0") == "1"
    if skip_auth_raw and env_name not in ("development", "dev", "test"):
        logger.critical("SKIP_AUTH=1 is set but ENV=%s - refusing to skip auth outside development. Set ENV=development to enable.", env_name)
        return False
    return skip_auth_raw


_env = _get_runtime_env()
SKIP_AUTH = _get_runtime_skip_auth()

if SKIP_AUTH:
    logger.warning("SKIP_AUTH=1 is active — all requests will use dev context. Do NOT use in production.")

_DEV_USER_ID = "dev-user-000"
_DEV_ORG_ID = "dev-org-000"
_DEV_ROLE = "admin"


class AuthContext(BaseModel):
    """Authenticated user context injected into route handlers."""

    user_id: str
    org_id: str
    role: str


def _session_cache_key(session_token: str) -> str:
    return f"session:{session_token}"


def _stamp_request_state(request: Request, ctx: AuthContext) -> None:
    request.state.user_id = ctx.user_id
    request.state.org_id = ctx.org_id
    request.state.session_token = getattr(request.state, "session_token", None)


async def _get_auth_context_from_cache(session_token: str) -> AuthContext | None:
    try:
        cached_value = await get_redis().get(_session_cache_key(session_token))
    except Exception:
        logger.exception("Auth cache read failed token_prefix=%s", session_token[:12])
        return None

    if not cached_value:
        return None

    try:
        return AuthContext.model_validate_json(cached_value)
    except (ValueError, TypeError):
        logger.warning("Auth cache contained invalid JSON token_prefix=%s", session_token[:12])
        return None


async def cache_auth_context(session_token: str, ctx: AuthContext) -> None:
    try:
        await get_redis().setex(_session_cache_key(session_token), SESSION_CACHE_TTL_SECONDS, ctx.model_dump_json())
    except Exception:
        logger.exception("Auth cache write failed token_prefix=%s", session_token[:12])


async def clear_auth_context_cache(session_token: str) -> None:
    try:
        await get_redis().delete(_session_cache_key(session_token))
    except Exception:
        logger.exception("Auth cache delete failed token_prefix=%s", session_token[:12])


async def _resolve_session_from_db(session_token: str, db: AsyncSession) -> AuthContext | None:
    result = await db.execute(
        select(Session.user_id, OrganizationMember.org_id, OrganizationMember.role)
        .join(User, User.id == Session.user_id)
        .join(OrganizationMember, OrganizationMember.user_id == Session.user_id)
        .where(Session.token == session_token)
        .where(Session.expires_at > datetime.now(UTC))
        .where(User.is_active.is_(True))
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None

    user_id, org_id, role = row
    return AuthContext(user_id=user_id, org_id=org_id, role=role)


async def _resolve_auth_context(session_token: str, db: AsyncSession) -> AuthContext | None:
    cached_ctx = await _get_auth_context_from_cache(session_token)
    if cached_ctx is not None:
        return cached_ctx

    db_ctx = await _resolve_session_from_db(session_token, db)
    if db_ctx is None:
        return None

    await cache_auth_context(session_token, db_ctx)
    return db_ctx


async def get_auth_context(request: Request, db: AsyncSession = Depends(get_db_session)) -> AuthContext:
    if _get_runtime_skip_auth():
        ctx = AuthContext(user_id=_DEV_USER_ID, org_id=_DEV_ORG_ID, role=_DEV_ROLE)
        _stamp_request_state(request, ctx)
        return ctx

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    request.state.session_token = session_token
    ctx = await _resolve_auth_context(session_token, db)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    _stamp_request_state(request, ctx)
    return ctx


async def get_optional_auth_context(request: Request, db: AsyncSession = Depends(get_db_session)) -> AuthContext | None:
    if _get_runtime_skip_auth():
        return AuthContext(user_id=_DEV_USER_ID, org_id=_DEV_ORG_ID, role=_DEV_ROLE)

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None

    request.state.session_token = session_token
    ctx = await _resolve_auth_context(session_token, db)
    if ctx is not None:
        _stamp_request_state(request, ctx)
    return ctx
