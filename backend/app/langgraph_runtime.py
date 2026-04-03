"""LangGraph runtime bootstrap for cross-process store registration.

LangGraph runs in a separate process from the Gateway, so the in-memory
`deerflow.store_registry` must be populated again inside the LangGraph process.
This module keeps that bootstrap in the app layer and then delegates to the
harness entrypoint.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.gateway.db.database import DATABASE_URL
from app.gateway.db.models import Thread
from app.gateway.redis_client import get_redis
from app.gateway.services.marketplace_install_store_pg import PostgresMarketplaceInstallStore
from app.gateway.services.mcp_config_store_pg import PostgresMcpConfigStore
from app.gateway.services.memory_store_pg import PostgresMemoryStore
from app.gateway.services.model_key_resolver_pg import PostgresModelKeyResolver
from app.gateway.services.skill_catalog_store_pg import PostgresSkillCatalogStore
from app.gateway.services.skill_config_store_pg import PostgresSkillConfigStore
from app.gateway.services.soul_store_pg import PostgresSoulStore
from deerflow.agents import make_lead_agent as harness_make_lead_agent
from deerflow.context import UserContext, get_user_context
from deerflow.store_registry import get_store, register_store

logger = logging.getLogger(__name__)

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


async def _resolve_user_from_thread(config: dict) -> UserContext | None:
    """Fallback: look up user_id/org_id from the threads table when context is missing.

    This covers history/resume requests where LangGraph SDK reconnects
    without the frontend-provided user context.
    """
    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id") or configurable.get("threadId")
    if not thread_id:
        return None

    try:
        async with runtime_async_session_factory() as session:
            result = await session.execute(select(Thread.user_id, Thread.org_id).where(Thread.id == thread_id).limit(1))
            row = result.one_or_none()
            if row is not None:
                logger.info("Resolved user context from threads table: thread_id=%s user_id=%s org_id=%s", thread_id, row.user_id, row.org_id)
                return UserContext(user_id=row.user_id, org_id=row.org_id)
    except Exception as exc:
        logger.warning("Failed to resolve user from thread_id=%s: %s", thread_id, exc)

    return None


async def make_lead_agent(config):
    _ensure_runtime_stores_registered()

    ctx = get_user_context(config)

    # Fallback: resolve user context from threads table for history/resume
    if ctx is None:
        ctx = await _resolve_user_from_thread(config)
        if ctx is not None:
            # Inject back into config so downstream harness code sees it too
            config.setdefault("configurable", {})["user_id"] = ctx.user_id
            config["configurable"]["org_id"] = ctx.org_id

    metadata = config.setdefault("metadata", {})

    if ctx is not None:
        skill_catalog_store = get_store("skill_catalog")
        if isinstance(skill_catalog_store, PostgresSkillCatalogStore):
            metadata["resolved_enabled_skill_names"] = sorted(await skill_catalog_store.get_enabled_skill_names(ctx.user_id, ctx.org_id))

        memory_store = get_store("memory")
        if isinstance(memory_store, PostgresMemoryStore):
            metadata["resolved_memory"] = await memory_store.get_memory(ctx.user_id)

        soul_store = get_store("soul")
        if isinstance(soul_store, PostgresSoulStore):
            metadata["resolved_soul"] = await soul_store.get_soul(ctx.user_id)

        # Pre-resolve marketplace tool gating (avoids sync-wrapper-in-async-loop errors)
        marketplace_store = get_store("marketplace")
        if isinstance(marketplace_store, PostgresMarketplaceInstallStore):
            metadata["resolved_managed_tools"] = sorted(await marketplace_store.get_managed_runtime_tools())
            metadata["resolved_installed_tools"] = sorted(await marketplace_store.get_installed_runtime_tools(ctx.org_id))

    return harness_make_lead_agent(config)
