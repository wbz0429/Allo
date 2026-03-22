"""Tests for the config router — tenant config overrides and merging."""



from app.gateway.routers.config import (
    ConfigImportRequest,
    MergedConfigResponse,
    ModelConfigUpdate,
    TenantConfigOverrides,
    ToolConfigUpdate,
    _merge_config,
    _parse_overrides,
)

# ---------------------------------------------------------------------------
# TenantConfigOverrides model
# ---------------------------------------------------------------------------


class TestTenantConfigOverrides:
    def test_defaults(self) -> None:
        o = TenantConfigOverrides()
        assert o.default_model is None
        assert o.enabled_models is None
        assert o.enabled_tool_groups is None
        assert o.custom_settings is None

    def test_with_values(self) -> None:
        o = TenantConfigOverrides(
            default_model="gpt-4o",
            enabled_models=["gpt-4o", "claude-3"],
            enabled_tool_groups=["search"],
            custom_settings={"key": "value"},
        )
        assert o.default_model == "gpt-4o"
        assert len(o.enabled_models) == 2
        assert o.custom_settings["key"] == "value"

    def test_serialization(self) -> None:
        o = TenantConfigOverrides(default_model="gpt-4o")
        data = o.model_dump(exclude_none=True)
        assert data == {"default_model": "gpt-4o"}


# ---------------------------------------------------------------------------
# _parse_overrides
# ---------------------------------------------------------------------------


class TestParseOverrides:
    def test_empty_string(self) -> None:
        o = _parse_overrides("")
        assert o.default_model is None

    def test_none_string(self) -> None:
        o = _parse_overrides(None)
        assert o.default_model is None

    def test_valid_json(self) -> None:
        o = _parse_overrides('{"default_model": "gpt-4o"}')
        assert o.default_model == "gpt-4o"

    def test_invalid_json(self) -> None:
        o = _parse_overrides("not json")
        assert o.default_model is None

    def test_empty_json_object(self) -> None:
        o = _parse_overrides("{}")
        assert o.default_model is None

    def test_extra_fields_ignored(self) -> None:
        o = _parse_overrides('{"default_model": "gpt-4o", "unknown_field": 42}')
        assert o.default_model == "gpt-4o"


# ---------------------------------------------------------------------------
# _merge_config
# ---------------------------------------------------------------------------


class TestMergeConfig:
    def test_no_overrides_returns_all_models(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_cfg = MagicMock()
        mock_model = MagicMock()
        mock_model.name = "gpt-4o"
        mock_model.display_name = "GPT-4o"
        mock_model.description = "OpenAI GPT-4o"
        mock_cfg.models = [mock_model]

        mock_tg = MagicMock()
        mock_tg.name = "search"
        mock_cfg.tool_groups = [mock_tg]

        with patch("app.gateway.routers.config.get_app_config", return_value=mock_cfg):
            result = _merge_config(TenantConfigOverrides())

        assert len(result.models) == 1
        assert result.models[0]["name"] == "gpt-4o"
        assert len(result.tool_groups) == 1
        assert result.default_model == "gpt-4o"

    def test_enabled_models_filter(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_cfg = MagicMock()
        m1 = MagicMock()
        m1.name = "gpt-4o"
        m1.display_name = "GPT-4o"
        m1.description = ""
        m2 = MagicMock()
        m2.name = "claude-3"
        m2.display_name = "Claude 3"
        m2.description = ""
        mock_cfg.models = [m1, m2]
        mock_cfg.tool_groups = []

        with patch("app.gateway.routers.config.get_app_config", return_value=mock_cfg):
            overrides = TenantConfigOverrides(enabled_models=["gpt-4o"])
            result = _merge_config(overrides)

        assert len(result.models) == 1
        assert result.models[0]["name"] == "gpt-4o"

    def test_enabled_tool_groups_filter(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_cfg = MagicMock()
        mock_cfg.models = []
        tg1 = MagicMock()
        tg1.name = "search"
        tg2 = MagicMock()
        tg2.name = "code"
        mock_cfg.tool_groups = [tg1, tg2]

        with patch("app.gateway.routers.config.get_app_config", return_value=mock_cfg):
            overrides = TenantConfigOverrides(enabled_tool_groups=["search"])
            result = _merge_config(overrides)

        assert len(result.tool_groups) == 1
        assert result.tool_groups[0]["name"] == "search"

    def test_default_model_from_overrides(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_cfg = MagicMock()
        m1 = MagicMock()
        m1.name = "gpt-4o"
        m1.display_name = "GPT-4o"
        m1.description = ""
        mock_cfg.models = [m1]
        mock_cfg.tool_groups = []

        with patch("app.gateway.routers.config.get_app_config", return_value=mock_cfg):
            overrides = TenantConfigOverrides(default_model="custom-model")
            result = _merge_config(overrides)

        assert result.default_model == "custom-model"

    def test_default_model_fallback_to_first(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_cfg = MagicMock()
        m1 = MagicMock()
        m1.name = "first-model"
        m1.display_name = "First"
        m1.description = ""
        mock_cfg.models = [m1]
        mock_cfg.tool_groups = []

        with patch("app.gateway.routers.config.get_app_config", return_value=mock_cfg):
            result = _merge_config(TenantConfigOverrides())

        assert result.default_model == "first-model"

    def test_no_models_default_model_is_none(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_cfg = MagicMock()
        mock_cfg.models = []
        mock_cfg.tool_groups = []

        with patch("app.gateway.routers.config.get_app_config", return_value=mock_cfg):
            result = _merge_config(TenantConfigOverrides())

        assert result.default_model is None


# ---------------------------------------------------------------------------
# Request model validation
# ---------------------------------------------------------------------------


class TestRequestModels:
    def test_model_config_update(self) -> None:
        req = ModelConfigUpdate(default_model="gpt-4o", enabled_models=["gpt-4o"])
        assert req.default_model == "gpt-4o"

    def test_tool_config_update(self) -> None:
        req = ToolConfigUpdate(enabled_tool_groups=["search", "code"])
        assert len(req.enabled_tool_groups) == 2

    def test_config_import_request_auto_format(self) -> None:
        req = ConfigImportRequest(content='{"key": "value"}')
        assert req.format == "auto"

    def test_config_import_request_yaml_format(self) -> None:
        req = ConfigImportRequest(content="key: value", format="yaml")
        assert req.format == "yaml"


# ---------------------------------------------------------------------------
# MergedConfigResponse model
# ---------------------------------------------------------------------------


class TestMergedConfigResponse:
    def test_defaults(self) -> None:
        resp = MergedConfigResponse()
        assert resp.models == []
        assert resp.tool_groups == []
        assert resp.default_model is None

    def test_with_data(self) -> None:
        resp = MergedConfigResponse(
            models=[{"name": "gpt-4o"}],
            tool_groups=[{"name": "search"}],
            default_model="gpt-4o",
        )
        assert len(resp.models) == 1
        assert resp.default_model == "gpt-4o"
