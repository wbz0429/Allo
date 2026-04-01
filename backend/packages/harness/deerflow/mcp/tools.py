"""Load MCP tools using langchain-mcp-adapters."""

import logging

from langchain_core.tools import BaseTool

from deerflow.config.extensions_config import ExtensionsConfig
from deerflow.mcp.client import build_servers_config
from deerflow.mcp.oauth import build_oauth_tool_interceptor, get_initial_oauth_headers
from deerflow.stores import McpConfigStore

logger = logging.getLogger(__name__)


async def get_mcp_tools(user_id: str | None = None, mcp_config_store: McpConfigStore | None = None) -> list[BaseTool]:
    """Get all tools from enabled MCP servers.

    Returns:
        List of LangChain tools from all enabled MCP servers.
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.warning("langchain-mcp-adapters not installed. Install it to enable MCP tools: pip install langchain-mcp-adapters")
        return []

    if user_id and mcp_config_store is not None:
        try:
            user_config = await mcp_config_store.get_user_mcp_config(user_id)
            extensions_config = ExtensionsConfig.model_validate({"mcpServers": user_config.get("mcp_servers", {}), "skills": {}})
        except Exception as exc:
            logger.error("Failed to load MCP config from store for user %s: %s", user_id, exc, exc_info=True)
            return []
    else:
        # NOTE: file-backed fallback retained for compatibility when no user-scoped store exists.
        extensions_config = ExtensionsConfig.from_file()
    servers_config = build_servers_config(extensions_config)

    if not servers_config:
        logger.info("No enabled MCP servers configured")
        return []

    try:
        # Create the multi-server MCP client
        logger.info(f"Initializing MCP client with {len(servers_config)} server(s)")

        # Inject initial OAuth headers for server connections (tool discovery/session init)
        initial_oauth_headers = await get_initial_oauth_headers(extensions_config)
        for server_name, auth_header in initial_oauth_headers.items():
            if server_name not in servers_config:
                continue
            if servers_config[server_name].get("transport") in ("sse", "http"):
                existing_headers = dict(servers_config[server_name].get("headers", {}))
                existing_headers["Authorization"] = auth_header
                servers_config[server_name]["headers"] = existing_headers

        for server_name, server_config in servers_config.items():
            headers = dict(server_config.get("headers", {}))
            auth_value = headers.get("Authorization", "")
            logger.info(
                "MCP server auth diagnostics",
                extra={
                    "server_name": server_name,
                    "transport": server_config.get("transport"),
                    "url": server_config.get("url"),
                    "has_authorization": bool(auth_value),
                    "authorization_prefix": auth_value[:16] if auth_value else "",
                    "header_keys": sorted(headers.keys()),
                },
            )

        tool_interceptors = []
        oauth_interceptor = build_oauth_tool_interceptor(extensions_config)
        if oauth_interceptor is not None:
            tool_interceptors.append(oauth_interceptor)

        client = MultiServerMCPClient(servers_config, tool_interceptors=tool_interceptors, tool_name_prefix=True)

        # Get all tools from all servers
        tools = await client.get_tools()
        logger.info(f"Successfully loaded {len(tools)} tool(s) from MCP servers")

        return tools

    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}", exc_info=True)
        return []
