"""LangGraph runtime bootstrap for cross-process store registration.

LangGraph runs in a separate process from the Gateway, so the in-memory
`deerflow.store_registry` must be populated again inside the LangGraph process.
This module keeps that bootstrap in the app layer and then delegates to the
harness entrypoint.
"""

import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.gateway.db.database import DATABASE_URL
from app.gateway.db.models import OrganizationMember, Thread
from app.gateway.redis_client import get_redis
from app.gateway.runtime_paths_guard import verify_runtime_base_dir_ownership
from app.gateway.services.kb_store_pg import PostgresKBStore
from app.gateway.services.marketplace_install_store_pg import PostgresMarketplaceInstallStore
from app.gateway.services.mcp_config_store_pg import PostgresMcpConfigStore
from app.gateway.services.memory_store_pg import PostgresMemoryStore
from app.gateway.services.model_key_resolver_pg import PostgresModelKeyResolver
from app.gateway.services.skill_catalog_store_pg import PostgresSkillCatalogStore
from app.gateway.services.skill_config_store_pg import PostgresSkillConfigStore
from app.gateway.services.soul_store_pg import PostgresSoulStore
from app.gateway.services.usage_record_store_pg import PostgresUsageRecordStore
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
    if get_store("kb") is None:
        register_store("kb", PostgresKBStore(runtime_async_session_factory))
    if get_store("usage") is None:
        register_store("usage", PostgresUsageRecordStore(runtime_async_session_factory))


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


async def _resolve_user_from_auth_id(auth_user_id: str) -> UserContext | None:
    """Fallback: resolve org_id from organization_members table using auth user ID."""
    try:
        async with runtime_async_session_factory() as session:
            result = await session.execute(select(OrganizationMember.org_id).where(OrganizationMember.user_id == auth_user_id).limit(1))
            row = result.one_or_none()
            if row is not None:
                logger.info("Resolved user context from org_members: user_id=%s org_id=%s", auth_user_id, row.org_id)
                return UserContext(user_id=auth_user_id, org_id=row.org_id)
    except Exception as exc:
        logger.warning("Failed to resolve user from auth_id=%s: %s", auth_user_id, exc)
    return None


async def _enforce_thread_ownership(ctx: UserContext, config: dict) -> None:
    """Verify the authenticated user owns the requested thread.

    Prevents user A from accessing user B's thread by guessing thread_id.
    Raises ValueError if ownership check fails.
    """
    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id") or configurable.get("threadId")
    if not thread_id:
        return  # No thread_id in request (e.g. new thread creation)

    try:
        async with runtime_async_session_factory() as session:
            result = await session.execute(select(Thread.user_id).where(Thread.id == thread_id).limit(1))
            row = result.one_or_none()
            if row is None:
                return  # Thread doesn't exist in gateway DB yet (first message)
            if row.user_id != ctx.user_id:
                logger.warning(
                    "Thread ownership violation: user %s attempted to access thread %s owned by %s",
                    ctx.user_id,
                    thread_id,
                    row.user_id,
                )
                raise ValueError(f"Access denied: thread {thread_id} does not belong to user {ctx.user_id}")
    except ValueError:
        raise
    except Exception as exc:
        logger.warning("Thread ownership check failed for thread_id=%s: %s", thread_id, exc)


def _is_history_request(config: dict) -> bool:
    """Detect whether this graph invocation is a history/state retrieval (not a real run).

    History requests have thread_id but no run_id in configurable, and empty metadata.
    """
    configurable = config.get("configurable") or {}
    has_thread_id = bool(configurable.get("thread_id") or configurable.get("threadId"))
    has_run_id = bool(configurable.get("run_id"))
    metadata = config.get("metadata") or {}
    has_metadata_run_id = bool(metadata.get("run_id"))
    return has_thread_id and not has_run_id and not has_metadata_run_id


async def make_lead_agent(config):
    verify_runtime_base_dir_ownership()

    t0 = time.monotonic()
    _ensure_runtime_stores_registered()

    context = config.get("context") or {}
    configurable = config.get("configurable") or {}
    metadata = config.get("metadata") or {}

    is_history = _is_history_request(config)

    logger.info(
        "Lead agent config summary top=%s context=%s configurable=%s metadata=%s flags=%s is_history=%s",
        sorted(str(key) for key in config.keys()),
        sorted(str(key) for key in context.keys()) if isinstance(context, dict) else [],
        sorted(str(key) for key in configurable.keys()) if isinstance(configurable, dict) else [],
        sorted(str(key) for key in metadata.keys()) if isinstance(metadata, dict) else [],
        {
            "has_context_run_id": bool(isinstance(context, dict) and context.get("run_id")),
            "has_configurable_run_id": bool(isinstance(configurable, dict) and configurable.get("run_id")),
            "has_context_user": bool(isinstance(context, dict) and (context.get("x-user-id") or context.get("user_id"))),
            "has_configurable_user": bool(isinstance(configurable, dict) and (configurable.get("x-user-id") or configurable.get("user_id"))),
            "has_thread_id": bool(isinstance(configurable, dict) and (configurable.get("thread_id") or configurable.get("threadId"))),
        },
        is_history,
    )

    t1 = time.monotonic()
    ctx = get_user_context(config)

    # Fallback: resolve user context from threads table for history/resume
    if ctx is None:
        ctx = await _resolve_user_from_thread(config)
        if ctx is not None:
            config.setdefault("configurable", {})["user_id"] = ctx.user_id
            config["configurable"]["org_id"] = ctx.org_id

    # Fallback 2: resolve real org_id when defaulted or missing
    if ctx is not None and (not ctx.org_id or ctx.org_id == "default"):
        resolved = await _resolve_user_from_auth_id(ctx.user_id)
        if resolved is not None:
            ctx = resolved
            config.setdefault("configurable", {})["user_id"] = ctx.user_id
            config["configurable"]["org_id"] = ctx.org_id

    # Enforce thread ownership only when ctx came from frontend (not fallback)
    ctx_from_frontend = get_user_context(config)
    if ctx_from_frontend is not None:
        await _enforce_thread_ownership(ctx_from_frontend, config)
    t2 = time.monotonic()
    logger.info("[perf] user_context_resolution=%.1fms", (t2 - t1) * 1000)

    metadata = config.setdefault("metadata", {})

    # --- History fast path: skip expensive pre-resolution for non-run requests ---
    if is_history:
        logger.info("[perf] history fast path: skipping skill/memory/soul/marketplace pre-resolution")
    elif ctx is not None:
        t3 = time.monotonic()
        skill_catalog_store = get_store("skill_catalog")
        if isinstance(skill_catalog_store, PostgresSkillCatalogStore):
            metadata["resolved_enabled_skill_names"] = sorted(await skill_catalog_store.get_enabled_skill_names(ctx.user_id, ctx.org_id))
        t4 = time.monotonic()
        logger.info("[perf] skill_catalog_resolution=%.1fms", (t4 - t3) * 1000)

        memory_store = get_store("memory")
        if isinstance(memory_store, PostgresMemoryStore):
            metadata["resolved_memory"] = await memory_store.get_memory(ctx.user_id)
        t5 = time.monotonic()
        logger.info("[perf] memory_resolution=%.1fms", (t5 - t4) * 1000)

        soul_store = get_store("soul")
        if isinstance(soul_store, PostgresSoulStore):
            metadata["resolved_soul"] = await soul_store.get_soul(ctx.user_id)
        t6 = time.monotonic()
        logger.info("[perf] soul_resolution=%.1fms", (t6 - t5) * 1000)

        # Pre-resolve marketplace tool gating (avoids sync-wrapper-in-async-loop errors)
        marketplace_store = get_store("marketplace")
        if isinstance(marketplace_store, PostgresMarketplaceInstallStore):
            metadata["resolved_managed_tools"] = sorted(await marketplace_store.get_managed_runtime_tools())
            metadata["resolved_installed_tools"] = sorted(await marketplace_store.get_installed_runtime_tools(ctx.org_id))
        t7 = time.monotonic()
        logger.info("[perf] marketplace_resolution=%.1fms", (t7 - t6) * 1000)

        # Pre-resolve knowledge bases for prompt injection
        kb_store = get_store("kb")
        if isinstance(kb_store, PostgresKBStore):
            all_kbs = await kb_store.list_knowledge_bases(ctx.org_id)
            # If user @mentioned specific KBs, filter to only those
            kb_ids = configurable.get("kb_ids")
            if kb_ids and isinstance(kb_ids, list):
                kb_id_set = set(kb_ids)
                metadata["resolved_knowledge_bases"] = [kb for kb in all_kbs if kb["id"] in kb_id_set]
            else:
                metadata["resolved_knowledge_bases"] = all_kbs

    t_harness_start = time.monotonic()
    result = harness_make_lead_agent(config)
    t_harness_end = time.monotonic()
    logger.info("[perf] harness_make_lead_agent=%.1fms total_make_lead_agent=%.1fms is_history=%s", (t_harness_end - t_harness_start) * 1000, (t_harness_end - t0) * 1000, is_history)

    return result
