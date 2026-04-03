"""LangGraph runtime bootstrap for cross-process store registration.

LangGraph runs in a separate process from the Gateway, so the in-memory
`deerflow.store_registry` must be populated again inside the LangGraph process.
This module keeps that bootstrap in the app layer and then delegates to the
harness entrypoint.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.gateway.db.database import DATABASE_URL
from app.gateway.redis_client import get_redis
from app.gateway.services.marketplace_install_store_pg import PostgresMarketplaceInstallStore
from app.gateway.services.mcp_config_store_pg import PostgresMcpConfigStore
from app.gateway.services.memory_store_pg import PostgresMemoryStore
from app.gateway.services.model_key_resolver_pg import PostgresModelKeyResolver
from app.gateway.services.skill_catalog_store_pg import PostgresSkillCatalogStore
from app.gateway.services.skill_config_store_pg import PostgresSkillConfigStore
from app.gateway.services.soul_store_pg import PostgresSoulStore
from deerflow.context import get_user_context
from deerflow.agents import make_lead_agent as harness_make_lead_agent
from deerflow.store_registry import get_store, register_store

runtime_async_engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)
runtime_async_session_factory = async_sessionmaker(runtime_async_engine, class_=AsyncSession, expire_on_commit=False)


def _ensure_runtime_stores_registered() -> None:
    if get_store("memory") is None:
        register_store("memory", PostgresMemoryStore(runtime_async_session_factory))
    if get_store("soul") is None:
        register_store("soul", PostgresSoulStore(runtime_async_session_factory))
    if get_store("skill") is None:
        register_store("skill", PostgresSkillConfigStore(runtime_async_session_factory))
    if get_store("skill_catalog") is None:
        register_store("skill_catalog", PostgresSkillCatalogStore(runtime_async_session_factory))
    if get_store("mcp") is None:
        register_store("mcp", PostgresMcpConfigStore(runtime_async_session_factory))
    if get_store("marketplace") is None:
        register_store("marketplace", PostgresMarketplaceInstallStore(runtime_async_session_factory))
    if get_store("key") is None:
        register_store("key", PostgresModelKeyResolver(runtime_async_session_factory, get_redis))


async def make_lead_agent(config):
    _ensure_runtime_stores_registered()

    ctx = get_user_context(config)
    if ctx is not None:
        skill_catalog_store = get_store("skill_catalog")
        if isinstance(skill_catalog_store, PostgresSkillCatalogStore):
            config.setdefault("metadata", {})["resolved_enabled_skill_names"] = sorted(await skill_catalog_store.get_enabled_skill_names(ctx.user_id, ctx.org_id))

        memory_store = get_store("memory")
        if isinstance(memory_store, PostgresMemoryStore):
            config.setdefault("metadata", {})["resolved_memory"] = await memory_store.get_memory(ctx.user_id)

        soul_store = get_store("soul")
        if isinstance(soul_store, PostgresSoulStore):
            config.setdefault("metadata", {})["resolved_soul"] = await soul_store.get_soul(ctx.user_id)

    return harness_make_lead_agent(config)
