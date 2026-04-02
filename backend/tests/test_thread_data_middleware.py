from types import SimpleNamespace

from deerflow.agents.middlewares.thread_data_middleware import ThreadDataMiddleware


def test_thread_data_middleware_reads_thread_id_from_runtime_configurable(tmp_path) -> None:
    middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
    runtime = SimpleNamespace(
        context={},
        config={
            "configurable": {
                "thread_id": "thread-123",
                "user_id": "user-123",
            }
        },
    )

    result = middleware.before_agent(state={}, runtime=runtime)

    assert result is not None
    thread_data = result["thread_data"]
    assert thread_data["workspace_path"].endswith("user-data/workspace")
    assert "thread-123" in thread_data["workspace_path"]
    assert "user-123" in thread_data["workspace_path"]
    assert thread_data["user_skills_path"].endswith("skills/custom")


def test_thread_data_middleware_raises_without_thread_id(tmp_path) -> None:
    middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
    runtime = SimpleNamespace(context={}, config={})

    try:
        middleware.before_agent(state={}, runtime=runtime)
    except ValueError as exc:
        assert "Thread ID is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError when thread_id is missing")
