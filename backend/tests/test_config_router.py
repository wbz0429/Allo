"""Tests for the tenant configuration API router.

Since the config router is NOT registered in app.py (BUG), these tests
import the router directly and test endpoint functions with mocked
dependencies (DB session, get_app_config).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.gateway.auth import AuthContext
from app.gateway.routers.config import (
    ConfigImportRequest,
    MergedConfigResponse,
    ModelConfigUpdate,
    TenantConfigOverrides,
    ToolConfigUpdate,
    _merge_config,
    _parse_overrides,
    export_config,
    get_config,
    import_config,
    list_models,
    list_tools,
    update_config,
    update_model_config,
    update_tool_config,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DEV_AUTH = AuthContext(user_id="dev-user-000", org_id="dev-org-000", role="admin")


def _make_tenant_config(org_id: str = "dev-org-000", config_json: str = "{}"):
    """Create a mock TenantConfig object."""
    tc = MagicMock()
    tc.org_id = org_id
    tc.config_json = config_json
    return tc


def _make_app_config(models=None, tool_groups=None):
    """Create a mock AppConfig with models and tool_groups."""
    cfg = MagicMock()
    if models is None:
        m1 = MagicMock()
        m1.name = "gpt-4"
        m1.display_name = "GPT-4"
        m1.description = "OpenAI GPT-4"
        m2 = MagicMock()
        m2.name = "deepseek-v3"
        m2.display_name = "DeepSeek V3"
        m2.description = "DeepSeek model"
        cfg.models = [m1, m2]
    else:
        cfg.models = models

    if tool_groups is None:
        tg1 = MagicMock()
        tg1.name = "web_search"
        tg2 = MagicMock()
        tg2.name = "code_tools"
        cfg.tool_groups = [tg1, tg2]
    else:
        cfg.tool_groups = tool_groups

    return cfg


# ---------------------------------------------------------------------------
# Unit tests: _parse_overrides and _merge_config
# ---------------------------------------------------------------------------


class TestParseOverrides:
    """Tests for the _parse_overrides helper."""

    def test_empty_string(self):
        result = _parse_overrides("")
        assert result.default_model is None
        assert result.enabled_models is None

    def test_empty_json(self):
        result = _parse_overrides("{}")
        assert result.default_model is None

    def test_valid_json(self):
        data = json.dumps({"default_model": "gpt-4", "enabled_models": ["gpt-4"]})
        result = _parse_overrides(data)
        assert result.default_model == "gpt-4"
        assert result.enabled_models == ["gpt-4"]

    def test_invalid_json_returns_defaults(self):
        result = _parse_overrides("not-json{{{")
        assert result.default_model is None


class TestMergeConfig:
    """Tests for the _merge_config helper."""

    @patch("app.gateway.routers.config.get_app_config")
    def test_no_overrides_returns_all(self, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        overrides = TenantConfigOverrides()
        result = _merge_config(overrides)

        assert isinstance(result, MergedConfigResponse)
        assert len(result.models) == 2
        assert len(result.tool_groups) == 2
        assert result.default_model == "gpt-4"  # first model

    @patch("app.gateway.routers.config.get_app_config")
    def test_enabled_models_filters(self, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        overrides = TenantConfigOverrides(enabled_models=["deepseek-v3"])
        result = _merge_config(overrides)

        assert len(result.models) == 1
        assert result.models[0]["name"] == "deepseek-v3"

    @patch("app.gateway.routers.config.get_app_config")
    def test_default_model_override(self, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        overrides = TenantConfigOverrides(default_model="deepseek-v3")
        result = _merge_config(overrides)

        assert result.default_model == "deepseek-v3"

    @patch("app.gateway.routers.config.get_app_config")
    def test_enabled_tool_groups_filters(self, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        overrides = TenantConfigOverrides(enabled_tool_groups=["web_search"])
        result = _merge_config(overrides)

        assert len(result.tool_groups) == 1
        assert result.tool_groups[0]["name"] == "web_search"


# ---------------------------------------------------------------------------
# Endpoint tests: get_config
# ---------------------------------------------------------------------------


class TestGetConfig:
    """Tests for GET /api/config endpoint."""

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_get_config_returns_merged(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        mock_get_tc.return_value = _make_tenant_config(config_json="{}")
        mock_db = AsyncMock()

        result = await get_config(auth=_DEV_AUTH, db=mock_db)

        assert isinstance(result, MergedConfigResponse)
        assert len(result.models) == 2
        mock_get_tc.assert_awaited_once_with(_DEV_AUTH.org_id, mock_db)

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_get_config_with_overrides(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        overrides_json = json.dumps({"default_model": "deepseek-v3", "enabled_models": ["deepseek-v3"]})
        mock_get_tc.return_value = _make_tenant_config(config_json=overrides_json)
        mock_db = AsyncMock()

        result = await get_config(auth=_DEV_AUTH, db=mock_db)

        assert result.default_model == "deepseek-v3"
        assert len(result.models) == 1


# ---------------------------------------------------------------------------
# Endpoint tests: update_config
# ---------------------------------------------------------------------------


class TestUpdateConfig:
    """Tests for PUT /api/config endpoint."""

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_partial_update(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        tc = _make_tenant_config(config_json="{}")
        mock_get_tc.return_value = tc
        mock_db = AsyncMock()

        request = TenantConfigOverrides(default_model="deepseek-v3")
        result = await update_config(request=request, auth=_DEV_AUTH, db=mock_db)

        assert result.default_model == "deepseek-v3"
        # Verify config_json was updated on the tenant config object
        saved_json = json.loads(tc.config_json)
        assert saved_json["default_model"] == "deepseek-v3"
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_partial_update_preserves_existing(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        existing = json.dumps({"default_model": "gpt-4", "enabled_models": ["gpt-4"]})
        tc = _make_tenant_config(config_json=existing)
        mock_get_tc.return_value = tc
        mock_db = AsyncMock()

        # Only update enabled_tool_groups, should preserve default_model and enabled_models
        request = TenantConfigOverrides(enabled_tool_groups=["web_search"])
        await update_config(request=request, auth=_DEV_AUTH, db=mock_db)

        saved_json = json.loads(tc.config_json)
        assert saved_json["default_model"] == "gpt-4"
        assert saved_json["enabled_models"] == ["gpt-4"]
        assert saved_json["enabled_tool_groups"] == ["web_search"]


# ---------------------------------------------------------------------------
# Endpoint tests: import_config
# ---------------------------------------------------------------------------


class TestImportConfig:
    """Tests for POST /api/config/import endpoint."""

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_import_yaml(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        tc = _make_tenant_config(config_json="{}")
        mock_get_tc.return_value = tc
        mock_db = AsyncMock()

        yaml_content = "default_model: deepseek-v3\nenabled_models:\n  - deepseek-v3\n"
        request = ConfigImportRequest(content=yaml_content, format="yaml")
        result = await import_config(request=request, auth=_DEV_AUTH, db=mock_db)

        assert result.default_model == "deepseek-v3"
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_import_json(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        tc = _make_tenant_config(config_json="{}")
        mock_get_tc.return_value = tc
        mock_db = AsyncMock()

        json_content = json.dumps({"default_model": "gpt-4", "enabled_models": ["gpt-4"]})
        request = ConfigImportRequest(content=json_content, format="json")
        result = await import_config(request=request, auth=_DEV_AUTH, db=mock_db)

        assert result.default_model == "gpt-4"

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_import_auto_detect_json(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        tc = _make_tenant_config(config_json="{}")
        mock_get_tc.return_value = tc
        mock_db = AsyncMock()

        json_content = json.dumps({"default_model": "gpt-4"})
        request = ConfigImportRequest(content=json_content, format="auto")
        result = await import_config(request=request, auth=_DEV_AUTH, db=mock_db)

        assert result.default_model == "gpt-4"

    @pytest.mark.asyncio
    async def test_import_invalid_json_raises_422(self):
        from fastapi import HTTPException

        mock_db = AsyncMock()
        request = ConfigImportRequest(content="not valid json{{{", format="json")

        with pytest.raises(HTTPException) as exc_info:
            await import_config(request=request, auth=_DEV_AUTH, db=mock_db)
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Endpoint tests: export_config
# ---------------------------------------------------------------------------


class TestExportConfig:
    """Tests for GET /api/config/export endpoint."""

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_export_returns_yaml_string(self, mock_get_tc):
        overrides_json = json.dumps({"default_model": "gpt-4"})
        mock_get_tc.return_value = _make_tenant_config(config_json=overrides_json)
        mock_db = AsyncMock()

        result = await export_config(auth=_DEV_AUTH, db=mock_db)

        assert isinstance(result, str)
        assert "default_model" in result
        assert "gpt-4" in result

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_export_empty_overrides(self, mock_get_tc):
        mock_get_tc.return_value = _make_tenant_config(config_json="{}")
        mock_db = AsyncMock()

        result = await export_config(auth=_DEV_AUTH, db=mock_db)

        assert isinstance(result, str)
        # Empty overrides should produce minimal YAML
        assert result.strip() == "{}" or result.strip() == ""


# ---------------------------------------------------------------------------
# Endpoint tests: list_models and list_tools
# ---------------------------------------------------------------------------


class TestListModelsAndTools:
    """Tests for GET /api/config/models and GET /api/config/tools."""

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    async def test_list_models(self, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()

        result = await list_models(auth=_DEV_AUTH)

        assert "models" in result
        assert len(result["models"]) == 2
        names = [m["name"] for m in result["models"]]
        assert "gpt-4" in names
        assert "deepseek-v3" in names

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    async def test_list_tools(self, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()

        result = await list_tools(auth=_DEV_AUTH)

        assert "tool_groups" in result
        assert len(result["tool_groups"]) == 2
        names = [tg["name"] for tg in result["tool_groups"]]
        assert "web_search" in names
        assert "code_tools" in names


# ---------------------------------------------------------------------------
# Endpoint tests: update_model_config and update_tool_config
# ---------------------------------------------------------------------------


class TestUpdateModelAndToolConfig:
    """Tests for PUT /api/config/models and PUT /api/config/tools."""

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_update_model_config(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        tc = _make_tenant_config(config_json="{}")
        mock_get_tc.return_value = tc
        mock_db = AsyncMock()

        request = ModelConfigUpdate(default_model="deepseek-v3", enabled_models=["deepseek-v3"])
        result = await update_model_config(request=request, auth=_DEV_AUTH, db=mock_db)

        assert result.default_model == "deepseek-v3"
        saved = json.loads(tc.config_json)
        assert saved["default_model"] == "deepseek-v3"
        assert saved["enabled_models"] == ["deepseek-v3"]

    @pytest.mark.asyncio
    @patch("app.gateway.routers.config.get_app_config")
    @patch("app.gateway.routers.config._get_or_create_tenant_config", new_callable=AsyncMock)
    async def test_update_tool_config(self, mock_get_tc, mock_get_cfg):
        mock_get_cfg.return_value = _make_app_config()
        tc = _make_tenant_config(config_json="{}")
        mock_get_tc.return_value = tc
        mock_db = AsyncMock()

        request = ToolConfigUpdate(enabled_tool_groups=["web_search"])
        result = await update_tool_config(request=request, auth=_DEV_AUTH, db=mock_db)

        assert len(result.tool_groups) == 1
        assert result.tool_groups[0]["name"] == "web_search"
