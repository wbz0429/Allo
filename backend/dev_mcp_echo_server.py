"""Local MCP test server for per-user execution isolation verification.

Exposes a single tool that returns selected environment variables so we can
verify whether different users receive different MCP runtime contexts.
"""

import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dev-echo")


@mcp.tool()
def echo_env() -> dict[str, str]:
    return {
        "MCP_TEST_USER": os.getenv("MCP_TEST_USER", ""),
        "MCP_TEST_TOKEN": os.getenv("MCP_TEST_TOKEN", ""),
    }


if __name__ == "__main__":
    mcp.run()
