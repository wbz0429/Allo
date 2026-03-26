"""Authentication middleware for the Allo gateway.

Provides AuthContext extraction from session cookies or API key headers,
with support for SKIP_AUTH=1 dev mode for backward compatibility.
"""

import json
import logging
import os
from collections.abc import Awaitable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.db.database import get_db_session
from app.gateway.db.models import Organization

logger = logging.getLogger(__name__)

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

# Default dev context used when SKIP_AUTH=1
_DEV_USER_ID = "dev-user-000"
_DEV_ORG_ID = "dev-org-000"
_DEV_ROLE = "admin"
_DEV_AUTH_SESSIONS_FILE = Path(__file__).resolve().parents[3] / "data" / "local-dev-auth-sessions.json"


async def _ensure_dev_org_exists(db: AsyncSession) -> None:
    """Ensure the development fallback organization exists for local-dev DB writes."""
    if _env not in ("development", "dev", "test"):
        return

    existing = await db.get(Organization, _DEV_ORG_ID)
    if existing is not None:
        return

    db.add(Organization(id=_DEV_ORG_ID, name="Local Dev Org", slug="local-dev-org"))
    await db.commit()
    logger.info("Auth: created dev fallback organization org_id=%s", _DEV_ORG_ID)


class AuthContext(BaseModel):
    """Authenticated user context injected into route handlers.

    Attributes:
        user_id: The authenticated user's ID.
        org_id: The organization (tenant) ID the user belongs to.
        role: The user's role within the organization ("admin" or "member").
    """

    user_id: str
    org_id: str
    role: str  # "admin" | "member"


async def _get_first_row(result: object) -> object:
    """Return ``result.first()`` while tolerating AsyncMock-based test doubles."""
    first_result = result.first()
    if isinstance(first_result, Awaitable):
        return await first_result
    return first_result


def _get_row_value(row: object, index: int) -> str | None:
    """Extract a string column from a DB row or return None for test doubles/invalid rows."""
    if not isinstance(row, (tuple, list)):
        return None
    if index >= len(row):
        return None
    value = row[index]
    if not isinstance(value, str):
        return None
    return value


async def _resolve_session_from_db(session_token: str, db: AsyncSession) -> AuthContext | None:
    """Look up a Better Auth session token in the database.

    Joins the session table with organization_members to build an AuthContext.

    Args:
        session_token: The session token value from the cookie.
        db: An async database session.

    Returns:
        AuthContext if the session is valid and the user belongs to an org, else None.
    """
    logger.info("Auth: DB session lookup start token_prefix=%s", session_token[:12])
    query = text('SELECT s."userId", om.org_id, om.role FROM session s JOIN organization_members om ON om.user_id = s."userId" WHERE s.token = :token AND s."expiresAt" > now() LIMIT 1')
    try:
        result = await db.execute(query, {"token": session_token})
    except Exception as exc:
        if _env in ("development", "dev", "test") and 'relation "session" does not exist' in str(exc):
            await db.rollback()
            logger.warning("Auth: session table missing in development, falling back to dev auth token_prefix=%s", session_token[:12])
            return None
        logger.exception("Auth: DB session lookup error token_prefix=%s", session_token[:12])
        raise
    row = await _get_first_row(result)
    if row is None:
        logger.info("Auth: DB session lookup miss token_prefix=%s", session_token[:12])
        return None
    user_id = _get_row_value(row, 0)
    org_id = _get_row_value(row, 1)
    role = _get_row_value(row, 2)
    if user_id is None or org_id is None or role is None:
        return None
    logger.info("Auth: DB session lookup hit user_id=%s org_id=%s role=%s", user_id, org_id, role)
    return AuthContext(user_id=user_id, org_id=org_id, role=role)


async def _resolve_dev_session_fallback(session_token: str, db: AsyncSession) -> AuthContext | None:
    """Restore a dev auth context from a valid Better Auth session without org membership.

    This fallback is limited to local development/test environments so the frontend
    register/login flow can proceed before org membership seeding is in place.

    Args:
        session_token: The session token value from the cookie.
        db: An async database session.

    Returns:
        AuthContext when the session exists in Better Auth's session table, else None.
    """
    if _env not in ("development", "dev", "test"):
        return None

    query = text('SELECT s."userId" FROM session s WHERE s.token = :token AND s."expiresAt" > now() LIMIT 1')
    try:
        result = await db.execute(query, {"token": session_token})
    except Exception as exc:
        if 'relation "session" does not exist' in str(exc):
            await db.rollback()
            logger.warning("Auth: dev session fallback skipped because session table is missing token_prefix=%s", session_token[:12])
            return None
        raise
    row = await _get_first_row(result)
    if row is None:
        return None
    user_id = _get_row_value(row, 0)
    if user_id is None:
        return None
    await _ensure_dev_org_exists(db)
    return AuthContext(user_id=user_id, org_id=_DEV_ORG_ID, role=_DEV_ROLE)


def _parse_iso_datetime(value: str) -> datetime | None:
    """Parse an ISO datetime string into an aware UTC datetime."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


async def _resolve_dev_json_session_fallback(
    session_token: str,
    sessions_file: Path = _DEV_AUTH_SESSIONS_FILE,
    db: AsyncSession | None = None,
) -> AuthContext | None:
    """Restore a dev auth context from the frontend's local JSON session store.

    Args:
        session_token: The session token value from the cookie.
        sessions_file: Path to the shared JSON session file.

    Returns:
        AuthContext when the token exists and is not expired in local dev, else None.
    """
    if _env not in ("development", "dev", "test"):
        return None

    try:
        raw_data = json.loads(sessions_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        logger.warning("Failed to parse local dev auth sessions JSON at %s", sessions_file)
        return None

    sessions = raw_data.get("sessions")
    if not isinstance(sessions, list):
        return None

    now = datetime.now(UTC)
    for session in sessions:
        if not isinstance(session, dict):
            continue
        token = session.get("token")
        user_id = session.get("userId")
        expires_at_raw = session.get("expiresAt")
        if not isinstance(token, str) or not isinstance(user_id, str) or not isinstance(expires_at_raw, str):
            continue
        if token != session_token:
            continue
        expires_at = _parse_iso_datetime(expires_at_raw)
        if expires_at is None or expires_at <= now:
            return None
        if db is not None:
            await _ensure_dev_org_exists(db)
        return AuthContext(user_id=user_id, org_id=_DEV_ORG_ID, role=_DEV_ROLE)

    return None


async def get_auth_context(request: Request, db: AsyncSession = Depends(get_db_session)) -> AuthContext:
    """FastAPI dependency that extracts and validates auth context.

    Checks (in order):
    1. SKIP_AUTH env flag — returns a default dev context.
    2. ``better-auth.session_token`` cookie — validated against the DB.
    3. ``X-API-Key`` or ``Authorization: Bearer df-...`` header (future-proofed).

    Args:
        request: The incoming FastAPI request.
        db: Async DB session (injected).

    Returns:
        A validated AuthContext.

    Raises:
        HTTPException: 401 if no valid credentials are found.
    """
    if _get_runtime_skip_auth():
        ctx = AuthContext(user_id=_DEV_USER_ID, org_id=_DEV_ORG_ID, role=_DEV_ROLE)
        _stamp_request_state(request, ctx)
        return ctx

    # 1. Try session cookie
    session_token = request.cookies.get("better-auth.session_token")
    if session_token:
        logger.info("Auth: request path=%s has session cookie token_prefix=%s", request.url.path, session_token[:12])
        ctx = await _resolve_session_from_db(session_token, db)
        if ctx is None:
            ctx = await _resolve_dev_session_fallback(session_token, db)
        if ctx is None:
            ctx = await _resolve_dev_json_session_fallback(session_token, db=db)
        if ctx is not None:
            logger.info("Auth: request path=%s resolved user_id=%s org_id=%s role=%s", request.url.path, ctx.user_id, ctx.org_id, ctx.role)
            _stamp_request_state(request, ctx)
            return ctx
        logger.warning("Auth: request path=%s session unresolved token_prefix=%s", request.url.path, session_token[:12])
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # 2. Try API key header (X-API-Key or Authorization: Bearer df-...)
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer df-"):
            api_key = auth_header[len("Bearer ") :]

    if api_key:
        # Phase 1: API key validation is a placeholder — will be fully implemented in Phase 2
        logger.warning("API key auth attempted but not yet implemented; rejecting")
        raise HTTPException(status_code=401, detail="API key authentication not yet supported")

    raise HTTPException(status_code=401, detail="Authentication required")


def _stamp_request_state(request: Request, ctx: AuthContext) -> None:
    """Stamp auth info onto request.state for middleware (usage tracking, rate limiter)."""
    request.state.user_id = ctx.user_id
    request.state.org_id = ctx.org_id


async def get_optional_auth_context(request: Request, db: AsyncSession = Depends(get_db_session)) -> AuthContext | None:
    """Same as get_auth_context but returns None instead of raising 401.

    Useful for endpoints that work with or without authentication (e.g., IM channels).

    Args:
        request: The incoming FastAPI request.
        db: Async DB session (injected).

    Returns:
        AuthContext if valid credentials are found, None otherwise.
    """
    if _get_runtime_skip_auth():
        return AuthContext(user_id=_DEV_USER_ID, org_id=_DEV_ORG_ID, role=_DEV_ROLE)

    session_token = request.cookies.get("better-auth.session_token")
    if session_token:
        ctx = await _resolve_session_from_db(session_token, db)
        if ctx is None:
            ctx = await _resolve_dev_session_fallback(session_token, db)
        if ctx is None:
            ctx = await _resolve_dev_json_session_fallback(session_token)
        return ctx

    return None
