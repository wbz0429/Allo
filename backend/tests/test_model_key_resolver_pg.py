import json

import pytest

from app.gateway.services.model_key_resolver_pg import PostgresModelKeyResolver


class _FakeRedis:
    def __init__(self, payloads: dict[str, str | None]):
        self._payloads = payloads

    async def get(self, key: str) -> str | None:
        return self._payloads.get(key)


@pytest.mark.asyncio
async def test_resolve_key_can_be_called_multiple_times() -> None:
    resolver = PostgresModelKeyResolver(
        async_session_factory=object(),
        redis_factory=lambda: _FakeRedis(
            {
                "run:run-1:key": json.dumps({"api_key": "sk-1", "base_url": "https://example.test/v1"}),
            }
        ),
    )

    first = await resolver.resolve_key("run-1")
    second = await resolver.resolve_key("run-1")

    assert first == ("sk-1", "https://example.test/v1")
    assert second == ("sk-1", "https://example.test/v1")
