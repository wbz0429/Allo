"""Tests for the token bucket rate limiter middleware."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.gateway.middleware.rate_limiter import RateLimiterMiddleware, TokenBucket

# ---------------------------------------------------------------------------
# TokenBucket unit tests
# ---------------------------------------------------------------------------


class TestTokenBucket:
    def test_initial_tokens_equal_capacity(self) -> None:
        bucket = TokenBucket(capacity=60.0)
        assert bucket.tokens == 60.0

    def test_refill_rate_is_capacity_per_second(self) -> None:
        bucket = TokenBucket(capacity=60.0)
        assert bucket.refill_rate == 1.0  # 60/60

    def test_consume_success(self) -> None:
        bucket = TokenBucket(capacity=10.0)
        assert bucket.consume() is True
        assert bucket.tokens < 10.0

    def test_consume_drains_bucket(self) -> None:
        bucket = TokenBucket(capacity=3.0)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is True
        # Bucket should be empty now (or very close)
        # Next consume should fail (unless time elapsed refilled)
        # Force last_refill to now to prevent refill
        bucket.last_refill = time.monotonic()
        bucket.tokens = 0.0
        assert bucket.consume() is False

    def test_retry_after_when_empty(self) -> None:
        bucket = TokenBucket(capacity=60.0)
        bucket.tokens = 0.0
        retry = bucket.retry_after()
        assert retry > 0.0
        # deficit is 1.0, refill_rate is 1.0, so retry_after ~ 1.0s
        assert abs(retry - 1.0) < 0.1

    def test_retry_after_when_full(self) -> None:
        bucket = TokenBucket(capacity=60.0)
        assert bucket.retry_after() == 0.0

    def test_refill_over_time(self) -> None:
        bucket = TokenBucket(capacity=60.0)
        # Drain all tokens
        bucket.tokens = 0.0
        # Simulate 2 seconds passing
        bucket.last_refill = time.monotonic() - 2.0
        assert bucket.consume() is True  # Should have refilled ~2 tokens

    def test_tokens_capped_at_capacity(self) -> None:
        bucket = TokenBucket(capacity=10.0)
        # Simulate long time passing
        bucket.last_refill = time.monotonic() - 1000.0
        bucket.consume()
        assert bucket.tokens <= 10.0


# ---------------------------------------------------------------------------
# RateLimiterMiddleware unit tests
# ---------------------------------------------------------------------------


class TestRateLimiterMiddleware:
    def _make_request(self, path: str = "/api/test", org_id: str | None = "org-1") -> MagicMock:
        request = MagicMock()
        request.url.path = path
        if org_id:
            request.state.org_id = org_id
        else:
            request.state = MagicMock(spec=[])  # no org_id attribute
        return request

    @pytest.mark.asyncio
    async def test_skip_health_endpoint(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=1)
        request = self._make_request(path="/health")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        await mw.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skip_docs_endpoint(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=1)
        request = self._make_request(path="/docs")
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        await mw.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_org_id_passes_through(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=1)
        request = self._make_request(org_id=None)
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        await mw.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_quota(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=60)
        request = self._make_request()
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        await mw.dispatch(request, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rate_limit_rejects_over_quota(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=2)
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        # Drain the bucket
        bucket = mw._get_bucket("org-1")
        bucket.tokens = 0.0
        bucket.last_refill = time.monotonic()

        request = self._make_request()
        response = await mw.dispatch(request, call_next)

        assert response.status_code == 429
        # Post-hoc rate limiter: call_next IS awaited, but response is replaced with 429
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rate_limit_429_has_retry_after_header(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=2)
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        bucket = mw._get_bucket("org-1")
        bucket.tokens = 0.0
        bucket.last_refill = time.monotonic()

        request = self._make_request()
        response = await mw.dispatch(request, call_next)

        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_custom_org_quota(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=60, org_quotas={"org-vip": 120})
        bucket = mw._get_bucket("org-vip")
        assert bucket.capacity == 120.0

    def test_update_org_quota(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=60)
        mw.update_org_quota("org-1", 120)
        bucket = mw._get_bucket("org-1")
        assert bucket.capacity == 120.0

    def test_different_orgs_have_separate_buckets(self) -> None:
        app = MagicMock()
        mw = RateLimiterMiddleware(app, default_rpm=60)
        b1 = mw._get_bucket("org-1")
        b2 = mw._get_bucket("org-2")
        assert b1 is not b2
