"""Integration checks for the local-dev auth MVP contract."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.gateway.auth import _DEV_ORG_ID, _DEV_ROLE, get_auth_context


@pytest.mark.asyncio
async def test_get_auth_context_falls_back_to_dev_org_for_valid_session_without_membership(monkeypatch) -> None:
    """A valid Better Auth session should still work in local dev without org membership rows."""
    request = MagicMock()
    request.cookies = {"better-auth.session_token": "tok-dev"}
    request.headers = {}
    request.state = MagicMock()
    mock_db = AsyncMock()

    monkeypatch.setattr("app.gateway.auth.SKIP_AUTH", False)
    monkeypatch.setattr("app.gateway.auth._env", "development")

    mock_result = MagicMock()
    mock_result.first.side_effect = [None, ("user-dev-123",)]
    mock_db.execute.return_value = mock_result

    ctx = await get_auth_context(request, mock_db)

    assert ctx.user_id == "user-dev-123"
    assert ctx.org_id == _DEV_ORG_ID
    assert ctx.role == _DEV_ROLE
    assert request.state.user_id == "user-dev-123"
    assert request.state.org_id == _DEV_ORG_ID


def test_register_page_does_not_call_missing_create_org_route() -> None:
    """The local-dev register flow must not depend on a missing frontend API route."""
    register_page = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "(auth)" / "register" / "page.tsx"
    contents = register_page.read_text()

    assert "/api/auth/create-org" not in contents
