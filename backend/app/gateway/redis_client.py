"""Async Redis client helpers for the gateway."""

import os

from dotenv import load_dotenv
from redis.asyncio import Redis

from app.gateway.db.database import _root_env_path

load_dotenv(_root_env_path)

_redis_client: Redis | None = None


def get_redis() -> Redis:
    """Return a shared async Redis client configured from REDIS_URL."""
    global _redis_client

    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    return _redis_client


async def close_redis_pool() -> None:
    """Close the shared async Redis client if it has been initialized."""
    global _redis_client

    if _redis_client is None:
        return

    await _redis_client.aclose()
    _redis_client = None
