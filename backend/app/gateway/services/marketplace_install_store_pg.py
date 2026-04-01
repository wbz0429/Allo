"""Postgres-backed marketplace install store for runtime gating."""

from sqlalchemy import select

from app.gateway.db.models import MarketplaceSkill, MarketplaceTool, OrgInstalledSkill, OrgInstalledTool
from deerflow.stores import MarketplaceInstallStore


class PostgresMarketplaceInstallStore(MarketplaceInstallStore):
    def __init__(self, async_session_factory) -> None:
        self._async_session_factory = async_session_factory

    async def get_installed_runtime_skills(self, org_id: str) -> set[str]:
        async with self._async_session_factory() as session:
            result = await session.execute(
                select(MarketplaceSkill.runtime_skill_name).join(OrgInstalledSkill, OrgInstalledSkill.skill_id == MarketplaceSkill.id).where(OrgInstalledSkill.org_id == org_id, MarketplaceSkill.runtime_skill_name.is_not(None))
            )
            return {name for name in result.scalars().all() if name}

    async def get_managed_runtime_skills(self) -> set[str]:
        async with self._async_session_factory() as session:
            result = await session.execute(select(MarketplaceSkill.runtime_skill_name).where(MarketplaceSkill.runtime_skill_name.is_not(None)))
            return {name for name in result.scalars().all() if name}

    async def get_installed_runtime_tools(self, org_id: str) -> set[str]:
        async with self._async_session_factory() as session:
            result = await session.execute(
                select(MarketplaceTool.runtime_tool_name).join(OrgInstalledTool, OrgInstalledTool.tool_id == MarketplaceTool.id).where(OrgInstalledTool.org_id == org_id, MarketplaceTool.runtime_tool_name.is_not(None))
            )
            return {name for name in result.scalars().all() if name}

    async def get_managed_runtime_tools(self) -> set[str]:
        async with self._async_session_factory() as session:
            result = await session.execute(select(MarketplaceTool.runtime_tool_name).where(MarketplaceTool.runtime_tool_name.is_not(None)))
            return {name for name in result.scalars().all() if name}
