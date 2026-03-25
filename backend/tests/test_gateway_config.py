"""Tests for the gateway configuration.

Tests cover CORS origins configuration, environment variable parsing,
and the global config cache behavior.
"""

import os
from unittest.mock import patch

import pytest

from app.gateway.config import GatewayConfig, get_gateway_config


class TestGatewayConfigDefaults:
    """Tests for GatewayConfig default values."""

    def test_default_host(self):
        """Default host should be 0.0.0.0."""
        config = GatewayConfig()
        assert config.host == "0.0.0.0"

    def test_default_port(self):
        """Default port should be 8001."""
        config = GatewayConfig()
        assert config.port == 8001

    def test_default_cors_origins(self):
        """Default CORS origins should include localhost:3000."""
        config = GatewayConfig()
        assert config.cors_origins == ["http://localhost:3000"]


class TestGetGatewayConfig:
    """Tests for get_gateway_config() function."""

    def setup_method(self):
        """Reset the global config cache before each test."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

    def teardown_method(self):
        """Reset the global config cache after each test."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

    @patch.dict(os.environ, {}, clear=True)
    def test_default_cors_origins_from_env(self):
        """When CORS_ORIGINS is not set, default to localhost:3000."""
        config = get_gateway_config()
        assert config.cors_origins == ["http://localhost:3000"]

    @patch.dict(os.environ, {"CORS_ORIGINS": "http://example.com"}, clear=True)
    def test_cors_origins_from_single_env_var(self):
        """CORS_ORIGINS env var with single value is parsed correctly."""
        # Reset cache to ensure env var is read
        import app.gateway.config as config_module

        config_module._gateway_config = None

        config = get_gateway_config()
        assert config.cors_origins == ["http://example.com"]

    @patch.dict(
        os.environ,
        {"CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000"},
        clear=True,
    )
    def test_multiple_cors_origins_split_by_comma(self):
        """Multiple CORS origins are split by comma."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

        config = get_gateway_config()
        assert config.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]

    @patch.dict(
        os.environ,
        {"CORS_ORIGINS": " http://localhost:3000 , http://127.0.0.1:3000 "},
        clear=True,
    )
    def test_whitespace_not_stripped_from_origins(self):
        """Whitespace is preserved from origins (current behavior)."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

        config = get_gateway_config()
        # Note: Current implementation does not strip whitespace
        assert config.cors_origins == [
            " http://localhost:3000 ",
            " http://127.0.0.1:3000 ",
        ]

    @patch.dict(os.environ, {"CORS_ORIGINS": "http://a.com,,http://b.com,"}, clear=True)
    def test_empty_strings_not_filtered(self):
        """Empty strings from split are not filtered (current behavior)."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

        config = get_gateway_config()
        # Note: Current implementation does not filter empty strings
        assert config.cors_origins == ["http://a.com", "", "http://b.com", ""]

    def test_config_is_cached(self):
        """Calling get_gateway_config twice returns the same object."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

        config1 = get_gateway_config()
        config2 = get_gateway_config()
        assert config1 is config2

    @patch.dict(os.environ, {"GATEWAY_HOST": "127.0.0.1"}, clear=True)
    def test_host_from_env_var(self):
        """GATEWAY_HOST env var sets the host."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

        config = get_gateway_config()
        assert config.host == "127.0.0.1"

    @patch.dict(os.environ, {"GATEWAY_PORT": "9000"}, clear=True)
    def test_port_from_env_var(self):
        """GATEWAY_PORT env var sets the port."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

        config = get_gateway_config()
        assert config.port == 9000

    @patch.dict(
        os.environ,
        {
            "GATEWAY_HOST": "192.168.1.1",
            "GATEWAY_PORT": "8080",
            "CORS_ORIGINS": "https://app.example.com,https://admin.example.com",
        },
        clear=True,
    )
    def test_all_env_vars_together(self):
        """All environment variables work together correctly."""
        import app.gateway.config as config_module

        config_module._gateway_config = None

        config = get_gateway_config()
        assert config.host == "192.168.1.1"
        assert config.port == 8080
        assert config.cors_origins == [
            "https://app.example.com",
            "https://admin.example.com",
        ]


class TestGatewayConfigModel:
    """Tests for GatewayConfig Pydantic model behavior."""

    def test_custom_host(self):
        """Can set custom host."""
        config = GatewayConfig(host="127.0.0.1")
        assert config.host == "127.0.0.1"

    def test_custom_port(self):
        """Can set custom port."""
        config = GatewayConfig(port=3000)
        assert config.port == 3000

    def test_custom_cors_origins(self):
        """Can set custom CORS origins."""
        origins = ["https://example.com", "https://app.example.com"]
        config = GatewayConfig(cors_origins=origins)
        assert config.cors_origins == origins
