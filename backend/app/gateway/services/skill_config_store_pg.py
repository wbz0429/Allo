"""Postgres-backed skill config store.

The current Sprint 2 contract does not define a dedicated per-user skill-toggle
table under the allowed schema. This implementation therefore returns no
overrides so the harness continues to use the global extensions config.
"""

from deerflow.stores import SkillConfigStore


class PostgresSkillConfigStore(SkillConfigStore):
    """Return no per-user skill overrides until a backing table exists."""

    def __init__(self, async_session_factory) -> None:
        self._async_session_factory = async_session_factory

    async def get_skill_toggles(self, user_id: str) -> dict[str, bool]:
        del user_id
        return {}
