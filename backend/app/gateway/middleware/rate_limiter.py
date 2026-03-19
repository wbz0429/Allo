"""In-memory token bucket rate limiter per org_id.

Uses a simple token bucket algorithm. Each org gets a bucket that refills
at a configurable rate (requests per minute). When the bucket is empty,
requests are rejected with HTTP 429 and a Retry-After header.

Redis-backed implementation is planned for a future phase.
"""

import logging
import time
from dataclasses import dataclass, field

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Default: 60 requests per minute per org
DEFAULT_RPM = 60


@dataclass
class TokenBucket:
    """A single token bucket for rate limiting.

    Attributes:
        capacity: Maximum tokens the bucket can hold.
        tokens: Current available tokens.
        refill_rate: Tokens added per second.
        last_refill: Timestamp of last refill.
    """

    capacity: float
    tokens: float = field(init=False)
    refill_rate: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self.refill_rate = self.capacity / 60.0  # capacity per minute -> per second
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed, False if rate limited."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def retry_after(self) -> float:
        """Seconds until at least one token is available."""
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.refill_rate


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Per-org token bucket rate limiter middleware.

    Args:
        app: The ASGI application.
        default_rpm: Default requests per minute per org.
        org_quotas: Optional dict mapping org_id -> custom RPM.
    """

    # Paths to skip rate limiting
    _SKIP_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")

    def __init__(self, app: object, default_rpm: int = DEFAULT_RPM, org_quotas: dict[str, int] | None = None) -> None:
        super().__init__(app)
        self.default_rpm = default_rpm
        self.org_quotas: dict[str, int] = org_quotas or {}
        self._buckets: dict[str, TokenBucket] = {}

    def _get_bucket(self, org_id: str) -> TokenBucket:
        """Get or create a token bucket for the given org."""
        if org_id not in self._buckets:
            rpm = self.org_quotas.get(org_id, self.default_rpm)
            self._buckets[org_id] = TokenBucket(capacity=float(rpm))
        return self._buckets[org_id]

    def update_org_quota(self, org_id: str, rpm: int) -> None:
        """Update the RPM quota for an org. Resets the bucket.

        Args:
            org_id: Organization ID.
            rpm: New requests per minute limit.
        """
        self.org_quotas[org_id] = rpm
        # Reset bucket with new capacity
        self._buckets[org_id] = TokenBucket(capacity=float(rpm))

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Check rate limit before forwarding the request."""
        if request.url.path.startswith(self._SKIP_PREFIXES):
            return await call_next(request)

        org_id = getattr(request.state, "org_id", None)
        if not org_id:
            # No auth context yet — let the request through (auth will handle rejection)
            return await call_next(request)

        bucket = self._get_bucket(org_id)
        if not bucket.consume():
            retry_after = max(1.0, bucket.retry_after())
            logger.warning("Rate limit exceeded for org=%s on %s", org_id, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(int(retry_after))},
            )

        return await call_next(request)
