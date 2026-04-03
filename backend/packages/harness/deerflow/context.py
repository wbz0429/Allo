"""
User context extraction from LangGraph runtime configuration.

The Gateway + nginx inject X-User-Id and X-Org-Id headers into requests
to LangGraph Server. These end up in config["configurable"] and are
extracted here for use throughout the harness layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserContext:
    """Immutable user context extracted from runtime config."""

    user_id: str
    org_id: str
    run_id: str | None = None


def get_user_context(config: dict | None = None) -> UserContext | None:
    """Extract user context from a RunnableConfig dict.

    Looks for x-user-id / x-org-id (nginx-injected) or user_id / org_id
    (direct API) in either the newer context section or the legacy configurable
    section.

    Args:
        config: RunnableConfig dictionary from LangGraph runtime.

    Returns:
        UserContext if user_id is present, None otherwise.
    """
    if not config:
        return None
    context = config.get("context", {})
    configurable = config.get("configurable", {})
    user_id = context.get("x-user-id") or context.get("user_id") or configurable.get("x-user-id") or configurable.get("user_id")
    org_id = context.get("x-org-id") or context.get("org_id") or configurable.get("x-org-id") or configurable.get("org_id", "default")
    run_id = context.get("run_id") or configurable.get("run_id")
    if user_id:
        return UserContext(user_id=user_id, org_id=org_id, run_id=run_id)
    return None


def get_runtime_thread_id(runtime) -> str | None:
    """Extract thread_id from LangGraph runtime context.

    LangGraph SDK calls may place thread_id in either:
    - runtime.context["thread_id"]
    - runtime.context["threadId"]
    - runtime.context["configurable"]["thread_id"]
    - runtime.context["configurable"]["threadId"]
    - runtime.context["context"]["thread_id"]

    We normalize these access patterns here so middlewares/tools don't depend on
    one transport-specific shape.
    """
    if runtime is None:
        return None

    context = getattr(runtime, "context", None) or {}
    thread_id = context.get("thread_id") or context.get("threadId")
    if thread_id:
        return thread_id

    configurable = context.get("configurable") or {}
    thread_id = configurable.get("thread_id") or configurable.get("threadId")
    if thread_id:
        return thread_id

    nested_context = context.get("context") or {}
    thread_id = nested_context.get("thread_id") or nested_context.get("threadId")
    if thread_id:
        return thread_id

    runtime_config = getattr(runtime, "config", None) or {}
    runtime_context = runtime_config.get("context") or {}
    thread_id = runtime_context.get("thread_id") or runtime_context.get("threadId")
    if thread_id:
        return thread_id

    configurable = runtime_config.get("configurable") or {}
    thread_id = configurable.get("thread_id") or configurable.get("threadId")
    if thread_id:
        return thread_id

    return None


def get_runtime_user_id(runtime) -> str | None:
    """Extract normalized user_id from runtime context."""
    if runtime is None:
        return None

    context = getattr(runtime, "context", None) or {}
    runtime_config = getattr(runtime, "config", None) or {}
    runtime_context = runtime_config.get("context") or {}
    runtime_configurable = runtime_config.get("configurable") or {}
    return (
        context.get("x-user-id")
        or context.get("user_id")
        or (context.get("configurable") or {}).get("x-user-id")
        or (context.get("configurable") or {}).get("user_id")
        or (context.get("context") or {}).get("x-user-id")
        or (context.get("context") or {}).get("user_id")
        or runtime_context.get("x-user-id")
        or runtime_context.get("user_id")
        or runtime_configurable.get("x-user-id")
        or runtime_configurable.get("user_id")
    )
