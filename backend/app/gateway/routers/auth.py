"""Cookie-based authentication API for the gateway."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import SESSION_COOKIE_NAME, AuthContext, cache_auth_context, clear_auth_context_cache, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import Organization, OrganizationMember, Session, User
from app.gateway.redis_client import get_redis

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class SessionResponse(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    avatar_url: str | None
    locale: str
    org_id: str


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise HTTPException(status_code=422, detail="A valid email address is required")
    return normalized


def _normalize_display_name(display_name: str) -> str:
    normalized = display_name.strip()
    if not normalized:
        raise HTTPException(status_code=422, detail="Display name is required")
    return normalized


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def _generate_personal_org_slug() -> str:
    return f"personal-{uuid.uuid4().hex[:12]}"


def _create_session(user_id: str) -> Session:
    return Session(
        user_id=user_id,
        token=_generate_session_token(),
        expires_at=datetime.now(UTC) + timedelta(seconds=SESSION_MAX_AGE_SECONDS),
    )


def _set_session_cookie(response: Response, session_token: str) -> None:
    import os

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=os.getenv("ALLO_ENV") == "production",
        path="/",
        max_age=SESSION_MAX_AGE_SECONDS,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, httponly=True, samesite="lax", path="/")


async def _get_primary_membership(user_id: str, db: AsyncSession) -> OrganizationMember | None:
    result = await db.execute(select(OrganizationMember).where(OrganizationMember.user_id == user_id).limit(1))
    return result.scalar_one_or_none()


def _build_session_response(user: User, org_id: str) -> SessionResponse:
    return SessionResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        locale=user.locale,
        org_id=org_id,
    )


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    raw_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    # Per-IP rate limit: max 5 registrations per hour
    client_ip = raw_request.headers.get("x-forwarded-for", raw_request.client.host if raw_request.client else "unknown").split(",")[0].strip()
    rate_key = f"register_rate:{client_ip}"
    try:
        redis = await get_redis()
        count = await redis.incr(rate_key)
        if count == 1:
            await redis.expire(rate_key, 3600)
        if count > 5:
            raise HTTPException(status_code=429, detail="Too many registrations. Please try again later.")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis failure should not block registration

    email = _normalize_email(request.email)
    display_name = _normalize_display_name(request.display_name)

    existing_user = await db.execute(select(User).where(User.email == email))
    if existing_user.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(email=email, password_hash=_hash_password(request.password), display_name=display_name)
    organization = Organization(name=f"{display_name}'s Organization", slug=_generate_personal_org_slug())
    membership = OrganizationMember(user_id=user.id, org_id=organization.id, role="admin")
    session = _create_session(user.id)

    db.add(user)
    db.add(organization)
    db.add(membership)
    db.add(session)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Unable to create account") from exc

    # Auto-install all public marketplace skills and tools for the new org
    try:
        from app.gateway.db.models import MarketplaceSkill, MarketplaceTool, OrgInstalledSkill, OrgInstalledTool
        skill_result = await db.execute(select(MarketplaceSkill.id).where(MarketplaceSkill.is_public.is_(True)))
        for row in skill_result.all():
            db.add(OrgInstalledSkill(org_id=organization.id, skill_id=row[0]))
        tool_result = await db.execute(select(MarketplaceTool.id).where(MarketplaceTool.is_public.is_(True)))
        for row in tool_result.all():
            db.add(OrgInstalledTool(org_id=organization.id, tool_id=row[0]))
        await db.commit()
    except Exception:
        pass  # Non-critical — user can install manually from marketplace

    auth_context = AuthContext(user_id=user.id, org_id=organization.id, role="admin")
    await cache_auth_context(session.token, auth_context)
    _set_session_cookie(response, session.token)
    return _build_session_response(user, organization.id)


@router.post("/login", response_model=SessionResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    email = _normalize_email(request.email)

    result = await db.execute(select(User).where(User.email == email).limit(1))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not _verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    membership = await _get_primary_membership(user.id, db)
    if membership is None:
        raise HTTPException(status_code=401, detail="User has no active organization membership")

    session = _create_session(user.id)
    db.add(session)
    await db.commit()

    auth_context = AuthContext(user_id=user.id, org_id=membership.org_id, role=membership.role)
    await cache_auth_context(session.token, auth_context)
    _set_session_cookie(response, session.token)
    return _build_session_response(user, membership.org_id)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    del auth
    session_token = getattr(request.state, "session_token", None)
    if not isinstance(session_token, str) or not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    await db.execute(delete(Session).where(Session.token == session_token))
    await db.commit()
    await clear_auth_context_cache(session_token)
    _clear_session_cookie(response)
    return {"success": True}


@router.get("/session", response_model=SessionResponse)
async def get_session(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    user = await db.get(User, auth.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return _build_session_response(user, auth.org_id)


@router.get("/check")
async def check_session(auth: AuthContext = Depends(get_auth_context)) -> Response:
    response = Response(status_code=status.HTTP_200_OK)
    response.headers["X-User-Id"] = auth.user_id
    response.headers["X-Org-Id"] = auth.org_id
    return response
