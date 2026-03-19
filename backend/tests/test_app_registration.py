"""Tests that verify FastAPI app creation and router registration.

Checks that create_app() returns a properly configured FastAPI instance
with all expected routers mounted at the correct prefixes.
"""

import inspect

import pytest

from app.gateway.app import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_route_paths(app) -> set[str]:
    """Extract all route path strings from a FastAPI app."""
    paths = set()
    for route in app.routes:
        if hasattr(route, "path"):
            paths.add(route.path)
    return paths


def _get_route_prefixes(app) -> set[str]:
    """Extract unique path prefixes (first two segments) from all routes."""
    prefixes = set()
    for route in app.routes:
        if hasattr(route, "path"):
            parts = route.path.strip("/").split("/")
            if len(parts) >= 2:
                prefixes.add(f"/{parts[0]}/{parts[1]}")
            elif len(parts) == 1 and parts[0]:
                prefixes.add(f"/{parts[0]}")
    return prefixes


# ---------------------------------------------------------------------------
# Tests: create_app returns a FastAPI instance
# ---------------------------------------------------------------------------


class TestCreateApp:
    """Verify create_app() returns a properly configured FastAPI instance."""

    def test_create_app_returns_fastapi(self):
        from fastapi import FastAPI

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_create_app_has_title(self):
        app = create_app()
        assert app.title == "DeerFlow API Gateway"

    def test_create_app_has_version(self):
        app = create_app()
        assert app.version == "0.1.0"


# ---------------------------------------------------------------------------
# Tests: expected route prefixes are registered
# ---------------------------------------------------------------------------


class TestRouteRegistration:
    """Verify that all expected routers are mounted at the correct prefixes."""

    def test_models_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/models" in prefixes

    def test_mcp_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/mcp" in prefixes

    def test_memory_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/memory" in prefixes

    def test_skills_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/skills" in prefixes

    def test_agents_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/agents" in prefixes

    def test_knowledge_bases_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/knowledge-bases" in prefixes

    def test_health_route_registered(self):
        app = create_app()
        paths = _get_route_paths(app)
        assert "/health" in paths

    def test_config_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/config" in prefixes

    def test_admin_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/admin" in prefixes

    def test_marketplace_routes_registered(self):
        app = create_app()
        prefixes = _get_route_prefixes(app)
        assert "/api/marketplace" in prefixes


# ---------------------------------------------------------------------------
# Tests: health endpoint has no auth dependency
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """The /health endpoint must remain unauthenticated."""

    def test_health_endpoint_exists(self):
        app = create_app()
        health_route = None
        for route in app.routes:
            if hasattr(route, "path") and route.path == "/health":
                health_route = route
                break
        assert health_route is not None, "/health route must exist"

    def test_health_endpoint_has_no_auth_param(self):
        app = create_app()
        for route in app.routes:
            if hasattr(route, "path") and route.path == "/health":
                sig = inspect.signature(route.endpoint)
                assert "auth" not in sig.parameters, "/health must NOT require auth"
                return
        pytest.fail("/health route not found")


# ---------------------------------------------------------------------------
# Tests: router importability
# ---------------------------------------------------------------------------


class TestRouterImports:
    """Verify that router modules can be imported."""

    def test_config_router_importable(self):
        from app.gateway.routers import config

        assert hasattr(config, "router")

    def test_agents_router_importable(self):
        from app.gateway.routers import agents

        assert hasattr(agents, "router")

    def test_knowledge_bases_router_importable(self):
        from app.gateway.routers import knowledge_bases

        assert hasattr(knowledge_bases, "router")

    def test_admin_router_importable(self):
        from app.gateway.routers import admin  # noqa: F401

    def test_marketplace_router_importable(self):
        from app.gateway.routers import marketplace  # noqa: F401
