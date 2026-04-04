"""Shared path resolution for thread virtual paths (e.g. mnt/user-data/outputs/...)."""

from pathlib import Path

from fastapi import HTTPException

from deerflow.config.paths import get_paths


def resolve_thread_virtual_path(thread_id: str, virtual_path: str, user_id: str | None = None) -> Path:
    """Resolve a virtual path to the actual filesystem path under thread user-data.

    Tries per-user path first (users/{user_id}/threads/{thread_id}/user-data/),
    then falls back to global path (threads/{thread_id}/user-data/).
    """
    paths = get_paths()
    stripped = virtual_path.lstrip("/")
    prefix = "mnt/user-data"

    # Try per-user path first
    if user_id and stripped.startswith(prefix):
        relative = stripped[len(prefix):].lstrip("/")
        user_base = (paths.user_thread_dir(user_id, thread_id) / "user-data").resolve()
        actual = (user_base / relative).resolve()
        try:
            actual.relative_to(user_base)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: path traversal detected")
        if actual.exists():
            return actual

    # Fallback to global path
    try:
        return paths.resolve_virtual_path(thread_id, virtual_path)
    except ValueError as e:
        status = 403 if "traversal" in str(e) else 400
        raise HTTPException(status_code=status, detail=str(e))
