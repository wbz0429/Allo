from unittest.mock import MagicMock, patch

from deerflow.sandbox.middleware import SandboxMiddleware


def test_after_agent_ignores_none_runtime_context():
    middleware = SandboxMiddleware()
    runtime = MagicMock()
    runtime.context = None

    with patch("deerflow.sandbox.middleware.get_sandbox_provider") as get_provider:
        result = middleware.after_agent(state={}, runtime=runtime)

    assert result is None
    get_provider.return_value.release.assert_not_called()
