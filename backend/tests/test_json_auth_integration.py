"""Integration checks for the local-dev auth MVP contract."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.gateway.auth import get_auth_context


@pytest.mark.asyncio
async def test_get_auth_context_valid_session_token_resolves_user(monkeypatch) -> None:
    """A valid session_token cookie should resolve the user via _resolve_auth_context."""
    from app.gateway.auth import AuthContext

    request = MagicMock()
    request.cookies = {"session_token": "tok-dev"}
    request.state = MagicMock()
    mock_db = AsyncMock()

    monkeypatch.setattr("app.gateway.auth._get_runtime_skip_auth", lambda: False)

    expected_ctx = AuthContext(user_id="user-dev-123", org_id="org-dev-456", role="member")
    monkeypatch.setattr(
        "app.gateway.auth._resolve_auth_context",
        AsyncMock(return_value=expected_ctx),
    )

    ctx = await get_auth_context(request, mock_db)

    assert ctx.user_id == "user-dev-123"
    assert ctx.org_id == "org-dev-456"
    assert ctx.role == "member"
    assert request.state.user_id == "user-dev-123"
    assert request.state.org_id == "org-dev-456"


def test_register_page_does_not_call_missing_create_org_route() -> None:
    """The local-dev register flow must not depend on a missing frontend API route."""
    register_page = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "(auth)" / "register" / "page.tsx"
    contents = register_page.read_text()

    assert "/api/auth/create-org" not in contents


def test_login_page_uses_hard_navigation_after_success() -> None:
    """Login should force a document navigation so the new session cookie is visible to middleware."""
    login_page = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "(auth)" / "login" / "page.tsx"
    contents = login_page.read_text()

    assert "window.location.assign" in contents
    assert 'router.push("/workspace")' not in contents


def test_auth_pages_preserve_callback_url_on_success() -> None:
    """Login and register should redirect to callbackUrl when present."""
    frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "(auth)"

    for page_name in ("login", "register"):
        contents = (frontend_root / page_name / "page.tsx").read_text()
        assert "useSearchParams" in contents
        assert "callbackUrl" in contents
