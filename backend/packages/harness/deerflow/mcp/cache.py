"""Cache for MCP tools to avoid repeated loading."""

import asyncio
import concurrent.futures
import logging
import os

from langchain_core.tools import BaseTool

from deerflow.stores import McpConfigStore

logger = logging.getLogger(__name__)

_mcp_tools_cache: list[BaseTool] | None = None
_cache_initialized = False
_initialization_lock = asyncio.Lock()
_config_mtime: float | None = None  # Track config file modification time
_mcp_tools_cache_by_user: dict[str, list[BaseTool]] = {}
_cache_initialized_by_user: dict[str, bool] = {}
_config_mtime_by_user: dict[str, float | None] = {}


def _get_config_mtime() -> float | None:
    """Get the modification time of the extensions config file.

    Returns:
        The modification time as a float, or None if the file doesn't exist.
    """
    from deerflow.config.extensions_config import ExtensionsConfig

    config_path = ExtensionsConfig.resolve_config_path()
    if config_path and config_path.exists():
        return os.path.getmtime(config_path)
    return None


def _is_cache_stale(user_id: str | None = None) -> bool:
    """Check if the cache is stale due to config file changes.

    Returns:
        True if the cache should be invalidated, False otherwise.
    """
    global _config_mtime

    if user_id:
        if not _cache_initialized_by_user.get(user_id, False):
            return False

        current_mtime = _get_config_mtime()
        cached_mtime = _config_mtime_by_user.get(user_id)

        if cached_mtime is None or current_mtime is None:
            return False

        if current_mtime > cached_mtime:
            logger.info(f"MCP config file has been modified for user {user_id} (mtime: {cached_mtime} -> {current_mtime}), cache is stale")
            return True

        return False

    if not _cache_initialized:
        return False  # Not initialized yet, not stale

    current_mtime = _get_config_mtime()

    # If we couldn't get mtime before or now, assume not stale
    if _config_mtime is None or current_mtime is None:
        return False

    # If the config file has been modified since we cached, it's stale
    if current_mtime > _config_mtime:
        logger.info(f"MCP config file has been modified (mtime: {_config_mtime} -> {current_mtime}), cache is stale")
        return True

    return False


async def initialize_mcp_tools(user_id: str | None = None, mcp_config_store: McpConfigStore | None = None) -> list[BaseTool]:
    """Initialize and cache MCP tools.

    This should be called once at application startup.

    Returns:
        List of LangChain tools from all enabled MCP servers.
    """
    global _mcp_tools_cache, _cache_initialized, _config_mtime

    async with _initialization_lock:
        if user_id and _cache_initialized_by_user.get(user_id, False):
            logger.info("MCP tools already initialized for user %s", user_id)
            return _mcp_tools_cache_by_user.get(user_id, [])

        if not user_id and _cache_initialized:
            logger.info("MCP tools already initialized")
            return _mcp_tools_cache or []

        from deerflow.mcp.tools import get_mcp_tools

        logger.info("Initializing MCP tools%s...", f" for user {user_id}" if user_id else "")
        tools = await get_mcp_tools()
        config_mtime = _get_config_mtime()

        if user_id:
            _mcp_tools_cache_by_user[user_id] = tools
            _cache_initialized_by_user[user_id] = True
            _config_mtime_by_user[user_id] = config_mtime
        else:
            _mcp_tools_cache = tools
            _cache_initialized = True
            _config_mtime = config_mtime

        logger.info("MCP tools initialized: %s tool(s) loaded (config mtime: %s)", len(tools), config_mtime)

        return tools


def get_cached_mcp_tools(user_id: str | None = None, mcp_config_store: McpConfigStore | None = None) -> list[BaseTool]:
    """Get cached MCP tools with lazy initialization.

    If tools are not initialized, automatically initializes them.
    This ensures MCP tools work in both FastAPI and LangGraph Studio contexts.

    Also checks if the config file has been modified since last initialization,
    and re-initializes if needed. This ensures that changes made through the
    Gateway API (which runs in a separate process) are reflected in the
    LangGraph Server.

    Returns:
        List of cached MCP tools.
    """
    global _mcp_tools_cache, _cache_initialized, _config_mtime

    # Check if cache is stale due to config file changes
    if _is_cache_stale(user_id):
        logger.info("MCP cache is stale, resetting for re-initialization...")
        reset_mcp_tools_cache(user_id)

    if user_id:
        initialized = _cache_initialized_by_user.get(user_id, False)
    else:
        initialized = _cache_initialized

    if not initialized:
        logger.info("MCP tools not initialized, performing lazy initialization...")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            initialized_tools = asyncio.run(initialize_mcp_tools(user_id=user_id, mcp_config_store=mcp_config_store))
        except Exception as e:
            logger.error(f"Failed to lazy-initialize MCP tools: {e}")
            return []
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, initialize_mcp_tools(user_id=user_id, mcp_config_store=mcp_config_store))
                initialized_tools = future.result()

        if initialized_tools is not None:
            if user_id:
                _mcp_tools_cache_by_user[user_id] = initialized_tools
                _cache_initialized_by_user[user_id] = True
                _config_mtime_by_user[user_id] = _get_config_mtime()
            else:
                _mcp_tools_cache = initialized_tools
                _cache_initialized = True
                _config_mtime = _get_config_mtime()
            return initialized_tools

    if user_id:
        return _mcp_tools_cache_by_user.get(user_id, [])

    return _mcp_tools_cache or []


def reset_mcp_tools_cache(user_id: str | None = None) -> None:
    """Reset the MCP tools cache.

    This is useful for testing or when you want to reload MCP tools.
    """
    global _mcp_tools_cache, _cache_initialized, _config_mtime

    if user_id:
        _mcp_tools_cache_by_user.pop(user_id, None)
        _cache_initialized_by_user.pop(user_id, None)
        _config_mtime_by_user.pop(user_id, None)
        logger.info("MCP tools cache reset for user %s", user_id)
        return

    _mcp_tools_cache = None
    _cache_initialized = False
    _config_mtime = None
    _mcp_tools_cache_by_user.clear()
    _cache_initialized_by_user.clear()
    _config_mtime_by_user.clear()
    logger.info("MCP tools cache reset")
