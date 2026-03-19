"""Tests for the auth module: AuthContext model, get_auth_context, get_optional_auth_context."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.gateway.auth import AuthContext, _DEV_ORG_ID, _DEV_ROLE, _DEV_USER_ID, _resolve_session_from_db, get_auth_context, get_optional_auth_context


# ---------------------------------------------------------------------------
# AuthContext model tests
# ---------------------------------------------------------------------------


def test_auth_context_creation() -> None:
    ctx = AuthContext(user_id="u1", org_id="o1", role="admin")
    assert ctx.user_id == "u1"
    assert ctx.org_id == "o1"
    assert ctx.role == "admin"


def test_auth_context_member_role() -> None:
    ctx = AuthContext(user_id="u2", org_id="o2", role="member")
    assert ctx.role == "member"


def test_auth_context_serialization() -> None:
    ctx = AuthContext(user_id="u1", org_id="o1", role="admin")
    data = ctx.model_dump()
    assert data == {"user_id": "u1", "org_id": "o1", "role": "admin"}


def test_auth_context_from_dict() -> None:
    ctx = AuthContext.model_validate({"user_id": "u1", "org_id": "o1", "role": "member"})
    assert ctx.user_id == "u1"


# ---------------------------------------------------------------------------
# _resolve_session_from_db tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_session_valid_token() -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = ("user-123", "org-456", "admin")
    mock_db.execute.return_value = mock_result

    ctx = await _resolve_session_from_db("valid-token", mock_db)

    assert ctx is not None
    assert ctx.user_id == "user-123"
    assert ctx.org_id == "org-456"
    assert ctx.role == "admin"
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_session_invalid_token() -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    ctx = await _resolve_session_from_db("bad-token", mock_db)
    assert ctx is None


# ---------------------------------------------------------------------------
# get_auth_context tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_auth_context_skip_auth() -> None:
    request = MagicMock()
    mock_db = AsyncMock()

    with patch("app.gateway.auth.SKIP_AUTH", True):
        ctx = await get_auth_context(request, mock_db)

    assert ctx.user_id == _DEV_USER_ID
    assert ctx.org_id == _DEV_ORG_ID
    assert ctx.role == _DEV_ROLE


@pytest.mark.asyncio
async def test_get_auth_context_valid_cookie() -> None:
    request = MagicMock()
    request.cookies = {"better-auth.session_token": "tok-abc"}
    request.headers = {}
    mock_db = AsyncMock()

    with (
        patch("app.gateway.auth.SKIP_AUTH", False),
        patch("app.gateway.auth._resolve_session_from_db", new_callable=AsyncMock) as mock_resolve,
    ):
        mock_resolve.return_value = AuthContext(user_id="u1", org_id="o1", role="member")
        ctx = await get_auth_context(request, mock_db)

    assert ctx.user_id == "u1"
    assert ctx.org_id == "o1"
    mock_resolve.assert_awaited_once_with("tok-abc", mock_db)


@pytest.mark.asyncio
async def test_get_auth_context_expired_cookie_raises_401() -> None:
    from fastapi import HTTPException

    request = MagicMock()
    request.cookies = {"better-auth.session_token": "expired-tok"}
    request.headers = {}
    mock_db = AsyncMock()

    with (
        patch("app.gateway.auth.SKIP_AUTH", False),
        patch("app.gateway.auth._resolve_session_from_db", new_callable=AsyncMock) as mock_resolve,
    ):
        mock_resolve.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_context(request, mock_db)

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_auth_context_no_credentials_raises_401() -> None:
    from fastapi import HTTPException

    request = MagicMock()
    request.cookies = {}
    request.headers = {}
    mock_db = AsyncMock()

    with patch("app.gateway.auth.SKIP_AUTH", False):
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_context(request, mock_db)

    assert exc_info.value.status_code == 401
    assert "required" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_auth_context_api_key_not_yet_supported() -> None:
    from fastapi import HTTPException

    request = MagicMock()
    request.cookies = {}
    request.headers = {"X-API-Key": "df-test-key"}
    mock_db = AsyncMock()

    with patch("app.gateway.auth.SKIP_AUTH", False):
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_context(request, mock_db)

    assert exc_info.value.status_code == 401
    assert "not yet supported" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_auth_context_bearer_api_key_not_yet_supported() -> None:
    from fastapi import HTTPException

    request = MagicMock()
    request.cookies = {}
    request.headers = {"Authorization": "Bearer df-my-key", "X-API-Key": ""}
    mock_db = AsyncMock()

    # Ensure X-API-Key is falsy so it falls through to Authorization header
    request.headers.get = lambda key, default="": {"Authorization": "Bearer df-my-key", "X-API-Key": ""}.get(key, default)

    with patch("app.gateway.auth.SKIP_AUTH", False):
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_context(request, mock_db)

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_optional_auth_context tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_optional_auth_context_skip_auth() -> None:
    request = MagicMock()
    mock_db = AsyncMock()

    with patch("app.gateway.auth.SKIP_AUTH", True):
        ctx = await get_optional_auth_context(request, mock_db)

    assert ctx is not None
    assert ctx.user_id == _DEV_USER_ID


@pytest.mark.asyncio
async def test_get_optional_auth_context_no_credentials_returns_none() -> None:
    request = MagicMock()
    request.cookies = {}
    mock_db = AsyncMock()

    with patch("app.gateway.auth.SKIP_AUTH", False):
        ctx = await get_optional_auth_context(request, mock_db)

    assert ctx is None


@pytest.mark.asyncio
async def test_get_optional_auth_context_valid_cookie() -> None:
    request = MagicMock()
    request.cookies = {"better-auth.session_token": "tok-xyz"}
    mock_db = AsyncMock()

    with (
        patch("app.gateway.auth.SKIP_AUTH", False),
        patch("app.gateway.auth._resolve_session_from_db", new_callable=AsyncMock) as mock_resolve,
    ):
        mock_resolve.return_value = AuthContext(user_id="u9", org_id="o9", role="admin")
        ctx = await get_optional_auth_context(request, mock_db)

    assert ctx is not None
    assert ctx.user_id == "u9"


@pytest.mark.asyncio
async def test_get_optional_auth_context_invalid_cookie_returns_none() -> None:
    request = MagicMock()
    request.cookies = {"better-auth.session_token": "bad-tok"}
    mock_db = AsyncMock()

    with (
        patch("app.gateway.auth.SKIP_AUTH", False),
        patch("app.gateway.auth._resolve_session_from_db", new_callable=AsyncMock) as mock_resolve,
    ):
        mock_resolve.return_value = None
        ctx = await get_optional_auth_context(request, mock_db)

    assert ctx is None
