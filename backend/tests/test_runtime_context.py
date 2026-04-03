from types import SimpleNamespace

from deerflow.context import get_runtime_thread_id, get_runtime_user_id, get_user_context


def test_get_user_context_reads_configurable_user_and_org() -> None:
    ctx = get_user_context(
        {
            "configurable": {
                "user_id": "user-1",
                "org_id": "org-1",
                "run_id": "run-1",
            }
        }
    )

    assert ctx is not None
    assert ctx.user_id == "user-1"
    assert ctx.org_id == "org-1"
    assert ctx.run_id == "run-1"


def test_get_runtime_thread_id_reads_runtime_context_direct() -> None:
    runtime = SimpleNamespace(context={"thread_id": "thread-1"}, config={})
    assert get_runtime_thread_id(runtime) == "thread-1"


def test_get_runtime_thread_id_reads_runtime_config_configurable() -> None:
    runtime = SimpleNamespace(context={}, config={"configurable": {"thread_id": "thread-2"}})
    assert get_runtime_thread_id(runtime) == "thread-2"


def test_get_runtime_thread_id_reads_runtime_config_context() -> None:
    runtime = SimpleNamespace(context={}, config={"context": {"thread_id": "thread-3"}})
    assert get_runtime_thread_id(runtime) == "thread-3"


def test_get_runtime_user_id_reads_runtime_config_configurable() -> None:
    runtime = SimpleNamespace(context={}, config={"configurable": {"user_id": "user-2"}})
    assert get_runtime_user_id(runtime) == "user-2"


def test_get_runtime_user_id_reads_runtime_config_context() -> None:
    runtime = SimpleNamespace(context={}, config={"context": {"user_id": "user-3"}})
    assert get_runtime_user_id(runtime) == "user-3"
