"""Resolver for per-run model keys written by the gateway."""

import json

from deerflow.stores import ModelKeyResolver


class PostgresModelKeyResolver(ModelKeyResolver):
    """Resolve decrypted model API keys from Redis by run ID."""

    def __init__(self, async_session_factory, redis_factory) -> None:
        self._async_session_factory = async_session_factory
        self._redis_factory = redis_factory

    async def resolve_key(self, run_id: str) -> tuple[str, str | None]:
        del self._async_session_factory
        payload = await self._redis_factory().get(f"run:{run_id}:key")
        if not payload:
            return "", None

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return "", None

        api_key = data.get("api_key")
        if not isinstance(api_key, str) or not api_key:
            return "", None

        base_url = data.get("base_url")
        return api_key, base_url if isinstance(base_url, str) and base_url else None
