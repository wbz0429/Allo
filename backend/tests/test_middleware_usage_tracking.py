"""Tests for the usage tracking middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.gateway.middleware.usage_tracking import UsageTrackingMiddleware, set_request_auth_state

# ---------------------------------------------------------------------------
# set_request_auth_state
# ---------------------------------------------------------------------------


def test_set_request_auth_state() -> None:
    request = MagicMock()
    set_request_auth_state(request, "user-1", "org-1")
    assert request.state.user_id == "user-1"
    assert request.state.org_id == "org-1"


# ---------------------------------------------------------------------------
# UsageTrackingMiddleware
# ---------------------------------------------------------------------------


class TestUsageTrackingMiddleware:
    def _make_request(self, path: str = "/api/test", user_id: str | None = None, org_id: str | None = None) -> MagicMock:
        request = MagicMock()
        request.url.path = path
        if user_id and org_id:
            request.state.user_id = user_id
            request.state.org_id = org_id
        else:
            # Simulate missing auth state
            state = MagicMock(spec=[])
            request.state = state
        return request

    @pytest.mark.asyncio
    async def test_skip_health_endpoint(self) -> None:
        app = MagicMock()
        mw = UsageTrackingMiddleware(app)
        request = self._make_request(path="/health")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        await mw.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skip_docs_endpoint(self) -> None:
        app = MagicMock()
        mw = UsageTrackingMiddleware(app)
        request = self._make_request(path="/docs")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        await mw.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_auth_state_skips_recording(self) -> None:
        app = MagicMock()
        mw = UsageTrackingMiddleware(app)
        request = self._make_request()
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        with patch("app.gateway.middleware.usage_tracking.async_session_factory") as mock_factory:
            await mw.dispatch(request, call_next)
            mock_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_records_usage_with_auth_state(self) -> None:
        app = MagicMock()
        mw = UsageTrackingMiddleware(app)
        request = self._make_request(user_id="user-1", org_id="org-1")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.gateway.middleware.usage_tracking.async_session_factory", return_value=mock_ctx):
            await mw.dispatch(request, call_next)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        # Verify the UsageRecord was created with correct fields
        record = mock_session.add.call_args[0][0]
        assert record.org_id == "org-1"
        assert record.user_id == "user-1"
        assert record.record_type == "api_call"
        assert record.endpoint == "/api/test"
        assert record.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_db_error_does_not_break_response(self) -> None:
        app = MagicMock()
        mw = UsageTrackingMiddleware(app)
        request = self._make_request(user_id="user-1", org_id="org-1")
        expected_response = MagicMock(status_code=200)
        call_next = AsyncMock(return_value=expected_response)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.gateway.middleware.usage_tracking.async_session_factory", return_value=mock_ctx):
            response = await mw.dispatch(request, call_next)

        # Response should still be returned even if DB fails
        assert response == expected_response
