"""Postgres-backed skill config store."""

import json

from sqlalchemy import select

from app.gateway.db.models import UserSkillConfig
from deerflow.stores import SkillConfigStore


class PostgresSkillConfigStore(SkillConfigStore):
    """Load per-user skill toggle overrides from Postgres."""

    def __init__(self, async_session_factory) -> None:
        self._async_session_factory = async_session_factory

    async def get_skill_toggles(self, user_id: str) -> dict[str, bool]:
        async with self._async_session_factory() as session:
            result = await session.execute(select(UserSkillConfig).where(UserSkillConfig.user_id == user_id).order_by(UserSkillConfig.updated_at.desc()).limit(1))
            config = result.scalar_one_or_none()
            if config is None:
                return {}

            try:
                payload = json.loads(config.config_json)
            except json.JSONDecodeError:
                return {}

            toggles = payload.get("skills", {}) if isinstance(payload, dict) else {}
            return {name: bool(value.get("enabled", True)) for name, value in toggles.items() if isinstance(value, dict)}
