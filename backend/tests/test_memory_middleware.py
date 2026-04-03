from types import SimpleNamespace

from deerflow.agents.middlewares.memory_middleware import MemoryMiddleware


def test_memory_middleware_reads_thread_and_user_from_runtime_configurable(monkeypatch) -> None:
    captured = {}

    class FakeQueue:
        def add(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("deerflow.agents.middlewares.memory_middleware.get_memory_queue", lambda: FakeQueue())

    middleware = MemoryMiddleware(agent_name=None, memory_store=object())
    runtime = SimpleNamespace(
        context={},
        config={
            "configurable": {
                "thread_id": "thread-abc",
                "user_id": "user-abc",
            }
        },
    )
    state = {
        "messages": [
            SimpleNamespace(type="human", content="hello"),
            SimpleNamespace(type="ai", content="hi", tool_calls=None),
        ]
    }

    result = middleware.after_agent(state=state, runtime=runtime)

    assert result is None
    assert captured["thread_id"] == "thread-abc"
    assert captured["user_id"] == "user-abc"
    assert captured["memory_store"] is not None


def test_memory_middleware_prefers_injected_user_id(monkeypatch) -> None:
    captured = {}

    class FakeQueue:
        def add(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("deerflow.agents.middlewares.memory_middleware.get_memory_queue", lambda: FakeQueue())

    middleware = MemoryMiddleware(agent_name=None, memory_store=object(), user_id="user-injected")
    runtime = SimpleNamespace(context={}, config={"configurable": {"thread_id": "thread-injected"}})
    state = {
        "messages": [
            SimpleNamespace(type="human", content="hello"),
            SimpleNamespace(type="ai", content="hi", tool_calls=None),
        ]
    }

    middleware.after_agent(state=state, runtime=runtime)

    assert captured["thread_id"] == "thread-injected"
    assert captured["user_id"] == "user-injected"
