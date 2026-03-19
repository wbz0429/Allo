"""Usage tracking middleware — logs every API call as a UsageRecord.

Records org_id, user_id, endpoint, and response time for each request
that has an authenticated context attached.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.gateway.db.database import async_session_factory
from app.gateway.db.models import UsageRecord

logger = logging.getLogger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that records an api_call UsageRecord for each request.

    Only tracks requests where auth context has been resolved (i.e. the request
    state contains user_id and org_id). Skips health checks and docs endpoints.
    """

    # Paths to skip tracking
    _SKIP_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request, measure duration, and log usage record."""
        # Skip non-API paths
        if request.url.path.startswith(self._SKIP_PREFIXES):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        # Extract auth context set by the dependency injection
        # We read from request.state which is populated after the route runs,
        # but middleware runs around the route. Instead, we parse from response
        # or use a background task approach. For simplicity, we try to extract
        # auth info from the request scope if available.
        user_id = getattr(request.state, "user_id", None)
        org_id = getattr(request.state, "org_id", None)

        if user_id and org_id:
            try:
                async with async_session_factory() as session:
                    record = UsageRecord(
                        org_id=org_id,
                        user_id=user_id,
                        record_type="api_call",
                        endpoint=request.url.path,
                        duration_seconds=round(duration, 4),
                    )
                    session.add(record)
                    await session.commit()
            except Exception:
                logger.warning("Failed to record usage for %s", request.url.path, exc_info=True)

        return response


def set_request_auth_state(request: Request, user_id: str, org_id: str) -> None:
    """Helper to stamp auth info onto request.state for the usage middleware.

    Call this from auth dependency or a custom dependency so the middleware
    can pick it up after the response is generated.

    Args:
        request: The current FastAPI request.
        user_id: Authenticated user ID.
        org_id: Authenticated org ID.
    """
    request.state.user_id = user_id
    request.state.org_id = org_id
