"""
Simple global store registry for dependency injection.

Gateway (app layer) registers concrete store implementations at startup.
Harness layer retrieves them via get_store(). When no store is registered,
get_store() returns None and callers fall back to local file-based behavior
(preserving backward compatibility with `make dev`).

Usage (Gateway startup):
    from deerflow.store_registry import register_store
    register_store("memory", PostgresMemoryStore(session_factory))
    register_store("soul", PostgresSoulStore(session_factory))

Usage (Harness runtime):
    from deerflow.store_registry import get_store
    from deerflow.stores import MemoryStore
    memory_store: MemoryStore | None = get_store("memory")
"""

import logging

logger = logging.getLogger(__name__)

_stores: dict[str, object] = {}


def register_store(name: str, impl: object) -> None:
    """Register a store implementation by name.

    Args:
        name: Store identifier (e.g. "memory", "soul", "skill", "mcp", "key").
        impl: Concrete implementation of the corresponding abstract store.
    """
    _stores[name] = impl
    logger.info("Store registered: %s -> %s", name, type(impl).__name__)


def get_store(name: str) -> object | None:
    """Retrieve a registered store by name.

    Args:
        name: Store identifier.

    Returns:
        The registered store implementation, or None if not registered.
    """
    return _stores.get(name)


def clear_stores() -> None:
    """Clear all registered stores. Useful for testing."""
    _stores.clear()
    logger.info("All stores cleared")
