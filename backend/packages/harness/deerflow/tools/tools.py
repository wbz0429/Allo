import asyncio
import logging

from langchain.tools import BaseTool

from deerflow.config import get_app_config
from deerflow.context import get_user_context
from deerflow.reflection import resolve_variable
from deerflow.store_registry import get_store
from deerflow.stores import MarketplaceInstallStore
from deerflow.tools.builtins import ask_clarification_tool, present_file_tool, task_tool, view_image_tool
from deerflow.tools.builtins.tool_search import reset_deferred_registry

logger = logging.getLogger(__name__)


def _run_coroutine_sync(coroutine):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coroutine)
        return future.result()


BUILTIN_TOOLS = [
    present_file_tool,
    ask_clarification_tool,
]

SUBAGENT_TOOLS = [
    task_tool,
    # task_status_tool is no longer exposed to LLM (backend handles polling internally)
]


def get_available_tools(
    groups: list[str] | None = None,
    include_mcp: bool = True,
    model_name: str | None = None,
    subagent_enabled: bool = False,
    runtime_config: dict | None = None,
) -> list[BaseTool]:
    """Get all available tools from config.

    Note: MCP tools should be initialized at application startup using
    `initialize_mcp_tools()` from deerflow.mcp module.

    Args:
        groups: Optional list of tool groups to filter by.
        include_mcp: Whether to include tools from MCP servers (default: True).
        model_name: Optional model name to determine if vision tools should be included.
        subagent_enabled: Whether to include subagent tools (task, task_status).

    Returns:
        List of available tools.
    """
    app_config = get_app_config()
    loaded_tools = [resolve_variable(tool.use, BaseTool) for tool in app_config.tools if groups is None or tool.group in groups]

    ctx = get_user_context(runtime_config)
    metadata = (runtime_config or {}).get("metadata", {})

    # Prefer pre-resolved marketplace data (from app.langgraph_runtime) to avoid
    # sync-wrapping async PG stores inside LangGraph's async event loop.
    resolved_managed = metadata.get("resolved_managed_tools")
    resolved_installed = metadata.get("resolved_installed_tools")

    if resolved_managed is not None:
        managed = set(resolved_managed)
        installed = set(resolved_installed) if resolved_installed else set()
        if managed:
            loaded_tools = [tool for tool in loaded_tools if getattr(tool, "name", None) not in managed or getattr(tool, "name", None) in installed]
    elif ctx:
        marketplace_store = get_store("marketplace")
        if isinstance(marketplace_store, MarketplaceInstallStore):
            try:
                managed = _run_coroutine_sync(marketplace_store.get_managed_runtime_tools())
                installed = _run_coroutine_sync(marketplace_store.get_installed_runtime_tools(ctx.org_id))
                if managed:
                    loaded_tools = [tool for tool in loaded_tools if getattr(tool, "name", None) not in managed or getattr(tool, "name", None) in installed]
            except Exception as e:
                logger.warning("Failed to apply marketplace tool gating: %s", e)

    # Conditionally add tools based on config
    builtin_tools = BUILTIN_TOOLS.copy()

    # Add subagent tools only if enabled via runtime parameter
    if subagent_enabled:
        builtin_tools.extend(SUBAGENT_TOOLS)
        logger.info("Including subagent tools (task)")

    # If no model_name specified, use the first model (default)
    if model_name is None and app_config.models:
        model_name = app_config.models[0].name

    # Add view_image_tool only if the model supports vision
    model_config = app_config.get_model_config(model_name) if model_name else None
    if model_config is not None and model_config.supports_vision:
        builtin_tools.append(view_image_tool)
        logger.info(f"Including view_image_tool for model '{model_name}' (supports_vision=True)")

    # Get cached MCP tools if enabled
    # NOTE: We use ExtensionsConfig.from_file() instead of config.extensions
    # to always read the latest configuration from disk. This ensures that changes
    # made through the Gateway API (which runs in a separate process) are immediately
    # reflected when loading MCP tools.
    mcp_tools = []
    # Reset deferred registry upfront to prevent stale state from previous calls
    reset_deferred_registry()
    if include_mcp:
        try:
            from deerflow.config.extensions_config import ExtensionsConfig
            from deerflow.mcp.cache import get_cached_mcp_tools

            extensions_config = ExtensionsConfig.from_file()
            if extensions_config.get_enabled_mcp_servers():
                mcp_tools = get_cached_mcp_tools()
                if mcp_tools:
                    logger.info(f"Using {len(mcp_tools)} cached MCP tool(s)")

                    # When tool_search is enabled, register MCP tools in the
                    # deferred registry and add tool_search to builtin tools.
                    if app_config.tool_search.enabled:
                        from deerflow.tools.builtins.tool_search import DeferredToolRegistry, set_deferred_registry
                        from deerflow.tools.builtins.tool_search import tool_search as tool_search_tool

                        registry = DeferredToolRegistry()
                        for t in mcp_tools:
                            registry.register(t)
                        set_deferred_registry(registry)
                        builtin_tools.append(tool_search_tool)
                        logger.info(f"Tool search active: {len(mcp_tools)} tools deferred")
        except ImportError:
            logger.warning("MCP module not available. Install 'langchain-mcp-adapters' package to enable MCP tools.")
        except Exception as e:
            logger.error(f"Failed to get cached MCP tools: {e}")

    logger.info(f"Total tools loaded: {len(loaded_tools)}, built-in tools: {len(builtin_tools)}, MCP tools: {len(mcp_tools)}")
    return loaded_tools + builtin_tools + mcp_tools
