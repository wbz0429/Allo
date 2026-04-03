import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.gateway.config import get_gateway_config
from app.gateway.db.database import async_session_factory
from app.gateway.redis_client import close_redis_pool, get_redis
from app.gateway.routers import (
    admin,
    agents,
    api_keys,
    artifacts,
    auth,
    channels,
    config,
    knowledge_bases,
    marketplace,
    mcp,
    memory,
    models,
    skills,
    soul,
    suggestions,
    threads,
    uploads,
    users,
)
from app.gateway.services.marketplace_install_store_pg import PostgresMarketplaceInstallStore
from app.gateway.services.mcp_config_store_pg import PostgresMcpConfigStore
from app.gateway.services.memory_store_pg import PostgresMemoryStore
from app.gateway.services.model_key_resolver_pg import PostgresModelKeyResolver
from app.gateway.services.skill_catalog_store_pg import PostgresSkillCatalogStore
from app.gateway.services.skill_config_store_pg import PostgresSkillConfigStore
from app.gateway.services.soul_store_pg import PostgresSoulStore
from deerflow.config.app_config import get_app_config
from deerflow.store_registry import register_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    import time

    t0 = time.monotonic()

    # Load config and check necessary environment variables at startup
    try:
        get_app_config()
        logger.info("Configuration loaded successfully (%.1fs)", time.monotonic() - t0)
    except Exception as e:
        error_msg = f"Failed to load configuration during gateway startup: {e}"
        logger.exception(error_msg)
        raise RuntimeError(error_msg) from e
    config = get_gateway_config()
    logger.info(f"Starting API Gateway on {config.host}:{config.port}")

    logger.info("Registering PG stores...")
    t1 = time.monotonic()
    register_store("memory", PostgresMemoryStore(async_session_factory))
    register_store("soul", PostgresSoulStore(async_session_factory))
    register_store("skill", PostgresSkillConfigStore(async_session_factory))
    register_store("skill_catalog", PostgresSkillCatalogStore(async_session_factory))
    register_store("mcp", PostgresMcpConfigStore(async_session_factory))
    register_store("marketplace", PostgresMarketplaceInstallStore(async_session_factory))
    register_store("key", PostgresModelKeyResolver(async_session_factory, get_redis))
    logger.info("PG stores registered (%.1fs)", time.monotonic() - t1)

    # Ensure a stable local dev account exists (idempotent).
    # Uses fixed IDs so install records, threads, memory etc. survive restarts.
    import os

    if os.getenv("ALLO_ENV", "development") != "production":
        from app.gateway.dev_seed import ensure_dev_account

        await ensure_dev_account(async_session_factory)

    # NOTE: MCP tools initialization is NOT done here because:
    # 1. Gateway doesn't use MCP tools - they are used by Agents in the LangGraph Server
    # 2. Gateway and LangGraph Server are separate processes with independent caches
    # MCP tools are lazily initialized in LangGraph Server when first needed

    # Start IM channel service if any channels are configured
    try:
        from app.channels.service import start_channel_service

        channel_service = await start_channel_service()
        logger.info("Channel service started: %s", channel_service.get_status())
    except Exception:
        logger.exception("No IM channels configured or channel service failed to start")

    logger.info("Gateway startup complete (%.1fs total)", time.monotonic() - t0)
    yield

    # Stop channel service on shutdown
    try:
        from app.channels.service import stop_channel_service

        await stop_channel_service()
    except Exception:
        logger.exception("Failed to stop channel service")

    try:
        await close_redis_pool()
    except Exception:
        logger.exception("Failed to close Redis pool")

    logger.info("Shutting down API Gateway")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """

    app = FastAPI(
        title="Allo API Gateway",
        description="""
## Allo API Gateway

API Gateway for Allo - An AI-powered office assistant with sandbox execution capabilities.

### Features

- **Models Management**: Query and retrieve available AI models
- **MCP Configuration**: Manage Model Context Protocol (MCP) server configurations
- **Memory Management**: Access and manage global memory data for personalized conversations
- **Skills Management**: Query and manage skills and their enabled status
- **Artifacts**: Access thread artifacts and generated files
- **Health Monitoring**: System health check endpoints

### Architecture

LangGraph requests are handled by nginx reverse proxy.
This gateway provides custom endpoints for models, MCP configuration, skills, and artifacts.
        """,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "auth",
                "description": "Register, login, logout, and inspect authenticated gateway sessions",
            },
            {
                "name": "models",
                "description": "Operations for querying available AI models and their configurations",
            },
            {
                "name": "users",
                "description": "Read and update the current authenticated user profile",
            },
            {
                "name": "soul",
                "description": "Read and update the current user's soul/personality content",
            },
            {
                "name": "api-keys",
                "description": "Manage the current user's provider API keys for BYOK flows",
            },
            {
                "name": "mcp",
                "description": "Manage Model Context Protocol (MCP) server configurations",
            },
            {
                "name": "memory",
                "description": "Access and manage global memory data for personalized conversations",
            },
            {
                "name": "threads",
                "description": "Create, list, update, and delete conversation threads and track thread runs",
            },
            {
                "name": "skills",
                "description": "Manage skills and their configurations",
            },
            {
                "name": "artifacts",
                "description": "Access and download thread artifacts and generated files",
            },
            {
                "name": "uploads",
                "description": "Upload and manage user files for threads",
            },
            {
                "name": "agents",
                "description": "Create and manage custom agents with per-agent config and prompts",
            },
            {
                "name": "suggestions",
                "description": "Generate follow-up question suggestions for conversations",
            },
            {
                "name": "channels",
                "description": "Manage IM channel integrations (Feishu, Slack, Telegram)",
            },
            {
                "name": "admin",
                "description": "Platform and enterprise administration",
            },
            {
                "name": "marketplace",
                "description": "MCP tool and skill marketplace",
            },
            {
                "name": "health",
                "description": "Health check and system status endpoints",
            },
        ],
    )

    # Support direct frontend->gateway calls in local development without nginx.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_gateway_config().cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register rate limiter and usage tracking middleware
    from app.gateway.middleware.rate_limiter import RateLimiterMiddleware
    from app.gateway.middleware.usage_tracking import UsageTrackingMiddleware

    app.add_middleware(UsageTrackingMiddleware)
    app.add_middleware(RateLimiterMiddleware)

    # Include routers
    # Auth API is mounted at /api/auth
    app.include_router(auth.router)

    # Users API is mounted at /api/users
    app.include_router(users.router)

    # Soul API is mounted at /api/users/me/soul
    app.include_router(soul.router)

    # API key management API is mounted at /api/users/me/api-keys
    app.include_router(api_keys.router)

    # Models API is mounted at /api/models
    app.include_router(models.router)

    # Threads API is mounted at /api/threads
    app.include_router(threads.router)

    # MCP API is mounted at /api/mcp
    app.include_router(mcp.router)

    # Memory API is mounted at /api/memory
    app.include_router(memory.router)

    # Skills API is mounted at /api/skills
    app.include_router(skills.router)

    # Artifacts API is mounted at /api/threads/{thread_id}/artifacts
    app.include_router(artifacts.router)

    # Uploads API is mounted at /api/threads/{thread_id}/uploads
    app.include_router(uploads.router)

    # Agents API is mounted at /api/agents
    app.include_router(agents.router)

    # Suggestions API is mounted at /api/threads/{thread_id}/suggestions
    app.include_router(suggestions.router)

    # Channels API is mounted at /api/channels
    app.include_router(channels.router)

    # Knowledge Bases API is mounted at /api/knowledge-bases
    app.include_router(knowledge_bases.router)

    # Config API is mounted at /api/config
    app.include_router(config.router)

    # Admin API is mounted at /api/admin
    app.include_router(admin.router)

    # Marketplace API is mounted at /api/marketplace
    app.include_router(marketplace.router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Health check endpoint.

        Returns:
            Service health status information.
        """
        return {"status": "healthy", "service": "allo-gateway"}

    return app


# Create app instance for uvicorn
app = create_app()
