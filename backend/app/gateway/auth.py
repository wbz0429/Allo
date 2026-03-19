"""Authentication middleware for the DeerFlow gateway.

Provides AuthContext extraction from session cookies or API key headers,
with support for SKIP_AUTH=1 dev mode for backward compatibility.
"""

import logging
import os

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.db.database import get_db_session

logger = logging.getLogger(__name__)

SKIP_AUTH = os.getenv("SKIP_AUTH", "0") == "1"

# Default dev context used when SKIP_AUTH=1
_DEV_USER_ID = "dev-user-000"
_DEV_ORG_ID = "dev-org-000"
_DEV_ROLE = "admin"


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


async def _resolve_session_from_db(session_token: str, db: AsyncSession) -> AuthContext | None:
    """Look up a Better Auth session token in the database.

    Joins the session table with organization_members to build an AuthContext.

    Args:
        session_token: The session token value from the cookie.
        db: An async database session.

    Returns:
        AuthContext if the session is valid and the user belongs to an org, else None.
    """
    query = text('SELECT s."userId", om.org_id, om.role FROM session s JOIN organization_members om ON om.user_id = s."userId" WHERE s.token = :token AND s."expiresAt" > now() LIMIT 1')
    result = await db.execute(query, {"token": session_token})
    row = result.first()
    if row is None:
        return None
    return AuthContext(user_id=row[0], org_id=row[1], role=row[2])


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
    if SKIP_AUTH:
        return AuthContext(user_id=_DEV_USER_ID, org_id=_DEV_ORG_ID, role=_DEV_ROLE)

    # 1. Try session cookie
    session_token = request.cookies.get("better-auth.session_token")
    if session_token:
        ctx = await _resolve_session_from_db(session_token, db)
        if ctx is not None:
            return ctx
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


async def get_optional_auth_context(request: Request, db: AsyncSession = Depends(get_db_session)) -> AuthContext | None:
    """Same as get_auth_context but returns None instead of raising 401.

    Useful for endpoints that work with or without authentication (e.g., IM channels).

    Args:
        request: The incoming FastAPI request.
        db: Async DB session (injected).

    Returns:
        AuthContext if valid credentials are found, None otherwise.
    """
    if SKIP_AUTH:
        return AuthContext(user_id=_DEV_USER_ID, org_id=_DEV_ORG_ID, role=_DEV_ROLE)

    session_token = request.cookies.get("better-auth.session_token")
    if session_token:
        return await _resolve_session_from_db(session_token, db)

    return None
