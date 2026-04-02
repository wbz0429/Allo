"""Postgres-backed resolved skill catalog store for runtime consumption."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.gateway.services.skill_catalog_resolver import get_user_skill_catalog
from deerflow.stores import SkillCatalogStore


class PostgresSkillCatalogStore(SkillCatalogStore):
    """Return the final enabled runtime skill names for a user/org."""

    def __init__(self, async_session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._async_session_factory = async_session_factory

    async def get_enabled_skill_names(self, user_id: str, org_id: str) -> set[str]:
        async with self._async_session_factory() as session:
            skills = await get_user_skill_catalog(user_id=user_id, org_id=org_id, db=session, enabled_only=True)
        return {skill.name for skill in skills}
