"""Postgres-backed implementation of the harness MCP config store."""

import json

from sqlalchemy import select

from app.gateway.db.models import UserMcpConfig
from deerflow.stores import McpConfigStore


class PostgresMcpConfigStore(McpConfigStore):
    """Load per-user MCP configuration JSON from Postgres."""

    def __init__(self, async_session_factory) -> None:
        self._async_session_factory = async_session_factory

    async def get_user_mcp_config(self, user_id: str) -> dict:
        async with self._async_session_factory() as session:
            result = await session.execute(select(UserMcpConfig).where(UserMcpConfig.user_id == user_id).order_by(UserMcpConfig.updated_at.desc()).limit(1))
            config = result.scalar_one_or_none()
            if config is None:
                return {}

            try:
                return json.loads(config.config_json)
            except json.JSONDecodeError:
                return {}
