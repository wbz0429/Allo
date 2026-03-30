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
    (direct API) in the configurable section.

    Args:
        config: RunnableConfig dictionary from LangGraph runtime.

    Returns:
        UserContext if user_id is present, None otherwise.
    """
    if not config:
        return None
    configurable = config.get("configurable", {})
    user_id = configurable.get("x-user-id") or configurable.get("user_id")
    org_id = configurable.get("x-org-id") or configurable.get("org_id", "default")
    run_id = configurable.get("run_id")
    if user_id:
        return UserContext(user_id=user_id, org_id=org_id, run_id=run_id)
    return None
