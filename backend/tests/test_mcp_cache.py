"""Tests for MCP cache behavior."""

from deerflow.mcp import cache


def test_get_cached_mcp_tools_uses_per_user_cache(monkeypatch):
    calls: list[str | None] = []

    async def fake_initialize(user_id: str | None = None, mcp_config_store=None):
        calls.append(user_id)
        return [f"tool-{user_id}"]

    monkeypatch.setattr(cache, "initialize_mcp_tools", fake_initialize)
    monkeypatch.setattr(cache, "_is_cache_stale", lambda user_id=None: False)
    cache.reset_mcp_tools_cache()

    assert cache.get_cached_mcp_tools(user_id="user-a") == ["tool-user-a"]
    assert cache.get_cached_mcp_tools(user_id="user-a") == ["tool-user-a"]
    assert calls == ["user-a"]


def test_get_cached_mcp_tools_keeps_global_cache_behavior(monkeypatch):
    calls: list[str | None] = []

    async def fake_initialize(user_id: str | None = None, mcp_config_store=None):
        calls.append(user_id)
        return ["global-tool"]

    monkeypatch.setattr(cache, "initialize_mcp_tools", fake_initialize)
    monkeypatch.setattr(cache, "_is_cache_stale", lambda user_id=None: False)
    cache.reset_mcp_tools_cache()

    assert cache.get_cached_mcp_tools() == ["global-tool"]
    assert cache.get_cached_mcp_tools() == ["global-tool"]
    assert calls == [None]
