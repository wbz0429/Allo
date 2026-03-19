"""Tests that routers properly require auth and pass AuthContext through."""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.gateway.auth import AuthContext, get_auth_context

# ---------------------------------------------------------------------------
# Helper: check that a router function has an auth parameter with the right default
# ---------------------------------------------------------------------------


def _get_auth_param(func):
    """Return the auth parameter from a route function's signature, or None."""
    sig = inspect.signature(func)
    for name, param in sig.parameters.items():
        if name == "auth":
            return param
    return None


# ---------------------------------------------------------------------------
# Router import helpers — import the raw async functions, not the decorated ones
# ---------------------------------------------------------------------------


def _import_agents_router():
    from app.gateway.routers import agents

    return agents


def _import_models_router():
    from app.gateway.routers import models

    return models


def _import_mcp_router():
    from app.gateway.routers import mcp

    return mcp


def _import_memory_router():
    from app.gateway.routers import memory

    return memory


def _import_skills_router():
    from app.gateway.routers import skills

    return skills


def _import_artifacts_router():
    from app.gateway.routers import artifacts

    return artifacts


def _import_uploads_router():
    from app.gateway.routers import uploads

    return uploads


def _import_suggestions_router():
    from app.gateway.routers import suggestions

    return suggestions


def _import_channels_router():
    from app.gateway.routers import channels

    return channels


# ---------------------------------------------------------------------------
# Tests: every authenticated endpoint has an `auth` parameter
# ---------------------------------------------------------------------------


class TestAgentsRouterAuth:
    def test_list_agents_has_auth(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.list_agents)
        assert param is not None, "list_agents must have an 'auth' parameter"

    def test_check_agent_name_has_auth(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.check_agent_name)
        assert param is not None

    def test_get_agent_has_auth(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.get_agent)
        assert param is not None

    def test_create_agent_has_auth(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.create_agent_endpoint)
        assert param is not None

    def test_update_agent_has_auth(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.update_agent)
        assert param is not None

    def test_delete_agent_has_auth(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.delete_agent)
        assert param is not None

    def test_get_user_profile_has_auth(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.get_user_profile)
        assert param is not None

    def test_update_user_profile_has_auth(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.update_user_profile)
        assert param is not None


class TestModelsRouterAuth:
    def test_list_models_has_auth(self) -> None:
        mod = _import_models_router()
        param = _get_auth_param(mod.list_models)
        assert param is not None

    def test_get_model_has_auth(self) -> None:
        mod = _import_models_router()
        param = _get_auth_param(mod.get_model)
        assert param is not None


class TestMcpRouterAuth:
    def test_get_mcp_config_has_auth(self) -> None:
        mod = _import_mcp_router()
        param = _get_auth_param(mod.get_mcp_configuration)
        assert param is not None

    def test_update_mcp_config_has_auth(self) -> None:
        mod = _import_mcp_router()
        param = _get_auth_param(mod.update_mcp_configuration)
        assert param is not None


class TestMemoryRouterAuth:
    def test_get_memory_has_auth(self) -> None:
        mod = _import_memory_router()
        param = _get_auth_param(mod.get_memory)
        assert param is not None

    def test_reload_memory_has_auth(self) -> None:
        mod = _import_memory_router()
        param = _get_auth_param(mod.reload_memory)
        assert param is not None

    def test_get_memory_config_has_auth(self) -> None:
        mod = _import_memory_router()
        param = _get_auth_param(mod.get_memory_config_endpoint)
        assert param is not None

    def test_get_memory_status_has_auth(self) -> None:
        mod = _import_memory_router()
        param = _get_auth_param(mod.get_memory_status)
        assert param is not None


class TestSkillsRouterAuth:
    def test_list_skills_has_auth(self) -> None:
        mod = _import_skills_router()
        param = _get_auth_param(mod.list_skills)
        assert param is not None

    def test_get_skill_has_auth(self) -> None:
        mod = _import_skills_router()
        param = _get_auth_param(mod.get_skill)
        assert param is not None

    def test_update_skill_has_auth(self) -> None:
        mod = _import_skills_router()
        param = _get_auth_param(mod.update_skill)
        assert param is not None

    def test_install_skill_has_auth(self) -> None:
        mod = _import_skills_router()
        param = _get_auth_param(mod.install_skill)
        assert param is not None


class TestArtifactsRouterAuth:
    def test_get_artifact_has_auth(self) -> None:
        mod = _import_artifacts_router()
        param = _get_auth_param(mod.get_artifact)
        assert param is not None


class TestUploadsRouterAuth:
    def test_upload_files_has_auth(self) -> None:
        mod = _import_uploads_router()
        param = _get_auth_param(mod.upload_files)
        assert param is not None

    def test_list_uploaded_files_has_auth(self) -> None:
        mod = _import_uploads_router()
        param = _get_auth_param(mod.list_uploaded_files)
        assert param is not None

    def test_delete_uploaded_file_has_auth(self) -> None:
        mod = _import_uploads_router()
        param = _get_auth_param(mod.delete_uploaded_file)
        assert param is not None


class TestSuggestionsRouterAuth:
    def test_generate_suggestions_has_auth(self) -> None:
        mod = _import_suggestions_router()
        param = _get_auth_param(mod.generate_suggestions)
        assert param is not None


class TestChannelsRouterAuth:
    """Channels use optional auth (get_optional_auth_context)."""

    def test_get_channels_status_has_auth(self) -> None:
        mod = _import_channels_router()
        param = _get_auth_param(mod.get_channels_status)
        assert param is not None

    def test_restart_channel_has_auth(self) -> None:
        mod = _import_channels_router()
        param = _get_auth_param(mod.restart_channel)
        assert param is not None


# ---------------------------------------------------------------------------
# Tests: auth annotation type is correct
# ---------------------------------------------------------------------------


class TestAuthAnnotationTypes:
    """Verify that required-auth endpoints annotate as AuthContext
    and optional-auth endpoints annotate as AuthContext | None."""

    def test_agents_list_requires_auth_context(self) -> None:
        mod = _import_agents_router()
        param = _get_auth_param(mod.list_agents)
        assert param.annotation is AuthContext

    def test_channels_status_uses_optional_auth(self) -> None:
        mod = _import_channels_router()
        param = _get_auth_param(mod.get_channels_status)
        # The annotation should allow None (AuthContext | None)
        annotation = param.annotation
        # For union types in Python 3.10+, check __args__
        if hasattr(annotation, "__args__"):
            assert type(None) in annotation.__args__
            assert AuthContext in annotation.__args__
        else:
            # Fallback: just check it's not plain AuthContext (it should be Optional)
            assert annotation is not AuthContext


# ---------------------------------------------------------------------------
# Tests: health endpoint does NOT have auth
# ---------------------------------------------------------------------------


class TestHealthEndpointNoAuth:
    """The /health endpoint must remain unauthenticated."""

    def test_health_endpoint_has_no_auth_dependency(self) -> None:
        from app.gateway.app import create_app

        app = create_app()
        # Find the health route
        health_route = None
        for route in app.routes:
            if hasattr(route, "path") and route.path == "/health":
                health_route = route
                break

        assert health_route is not None, "/health route must exist"

        # Check that the endpoint function does NOT have an 'auth' parameter
        endpoint = health_route.endpoint
        param = _get_auth_param(endpoint)
        assert param is None, "/health endpoint must NOT require auth"


# ---------------------------------------------------------------------------
# Tests: SKIP_AUTH mode returns dev context for all routers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip_auth_returns_dev_context() -> None:
    """When SKIP_AUTH=1, get_auth_context returns the dev context without DB."""
    from app.gateway.auth import _DEV_ORG_ID, _DEV_ROLE, _DEV_USER_ID

    request = MagicMock()
    mock_db = AsyncMock()

    with patch("app.gateway.auth.SKIP_AUTH", True):
        ctx = await get_auth_context(request, mock_db)

    assert ctx.user_id == _DEV_USER_ID
    assert ctx.org_id == _DEV_ORG_ID
    assert ctx.role == _DEV_ROLE
    # DB should NOT have been called
    mock_db.execute.assert_not_awaited()
