"""Postgres-backed implementation of the harness soul store."""

from sqlalchemy import select

from app.gateway.db.models import UserSoul
from deerflow.stores import SoulStore


class PostgresSoulStore(SoulStore):
    """Load per-user soul content from Postgres."""

    def __init__(self, async_session_factory) -> None:
        self._async_session_factory = async_session_factory

    async def get_soul(self, user_id: str) -> str | None:
        async with self._async_session_factory() as session:
            result = await session.execute(select(UserSoul).where(UserSoul.user_id == user_id).order_by(UserSoul.updated_at.desc()).limit(1))
            soul = result.scalar_one_or_none()
            if soul is None:
                return None
            return soul.content
