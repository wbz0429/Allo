"""
Cross-layer abstract interfaces for multi-tenant data stores.

Harness layer defines these interfaces; Gateway (app) layer provides implementations.
Harness NEVER imports app layer code — dependency flows one way only.
"""

from abc import ABC, abstractmethod


class MemoryStore(ABC):
    """Abstract store for per-user memory data."""

    @abstractmethod
    async def get_memory(self, user_id: str) -> dict: ...

    @abstractmethod
    async def save_memory(self, user_id: str, data: dict) -> None: ...

    @abstractmethod
    async def get_facts(self, user_id: str, limit: int = 15) -> list[dict]: ...


class SoulStore(ABC):
    """Abstract store for per-user soul/personality content."""

    @abstractmethod
    async def get_soul(self, user_id: str) -> str | None: ...


class SkillConfigStore(ABC):
    """Abstract store for per-user skill toggle configuration."""

    @abstractmethod
    async def get_skill_toggles(self, user_id: str) -> dict[str, bool]: ...


class McpConfigStore(ABC):
    """Abstract store for per-user MCP server configuration."""

    @abstractmethod
    async def get_user_mcp_config(self, user_id: str) -> dict: ...


class MarketplaceInstallStore(ABC):
    """Abstract store for org-scoped marketplace runtime mappings."""

    @abstractmethod
    async def get_installed_runtime_skills(self, org_id: str) -> set[str]: ...

    @abstractmethod
    async def get_managed_runtime_skills(self) -> set[str]: ...

    @abstractmethod
    async def get_installed_runtime_tools(self, org_id: str) -> set[str]: ...

    @abstractmethod
    async def get_managed_runtime_tools(self) -> set[str]: ...


class ModelKeyResolver(ABC):
    """Abstract resolver for per-run API key lookup.

    Gateway writes decrypted API keys to Redis before each run.
    Harness reads them via this interface during agent execution.
    """

    @abstractmethod
    async def resolve_key(self, run_id: str) -> tuple[str, str | None]: ...

    # returns (api_key, base_url | None)
