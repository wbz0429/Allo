"""Postgres-backed implementation of the harness memory store."""

import json

from sqlalchemy import delete, select

from app.gateway.db.models import UserMemory, UserMemoryFact
from deerflow.stores import MemoryStore


def _empty_memory() -> dict:
    """Return the canonical empty-memory structure expected by the harness updater."""
    return {
        "version": "1.0",
        "lastUpdated": "",
        "user": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "history": {
            "recentMonths": {"summary": "", "updatedAt": ""},
            "earlierContext": {"summary": "", "updatedAt": ""},
            "longTermBackground": {"summary": "", "updatedAt": ""},
        },
        "facts": [],
    }


class PostgresMemoryStore(MemoryStore):
    """Persist per-user memory data in gateway Postgres tables."""

    def __init__(self, async_session_factory) -> None:
        self._async_session_factory = async_session_factory

    async def get_memory(self, user_id: str) -> dict:
        async with self._async_session_factory() as session:
            result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id).order_by(UserMemory.updated_at.desc()).limit(1))
            memory = result.scalar_one_or_none()
            if memory is None:
                return _empty_memory()

            try:
                data = json.loads(memory.context_json)
                # Ensure required top-level keys exist (guards against partial data)
                if "user" not in data or "history" not in data:
                    base = _empty_memory()
                    base.update(data)
                    return base
                return data
            except json.JSONDecodeError:
                return _empty_memory()

    async def save_memory(self, user_id: str, data: dict) -> None:
        async with self._async_session_factory() as session:
            result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id).order_by(UserMemory.updated_at.desc()).limit(1))
            memory = result.scalar_one_or_none()
            if memory is None:
                memory = UserMemory(user_id=user_id, org_id=data.get("org_id", "default"), context_json=json.dumps(data, ensure_ascii=False))
                session.add(memory)
            else:
                memory.context_json = json.dumps(data, ensure_ascii=False)
                if isinstance(data.get("org_id"), str) and data["org_id"]:
                    memory.org_id = data["org_id"]

            await session.flush()

            facts = data.get("facts", [])
            await session.execute(delete(UserMemoryFact).where(UserMemoryFact.memory_id == memory.id))
            for fact in facts:
                if not isinstance(fact, dict):
                    continue
                session.add(
                    UserMemoryFact(
                        id=fact.get("id"),
                        user_id=user_id,
                        memory_id=memory.id,
                        content=str(fact.get("content", "")),
                        category=str(fact.get("category", "context")),
                        confidence=float(fact.get("confidence", 0.5)),
                        source=str(fact.get("source", "unknown")),
                    )
                )

            await session.commit()

    async def get_facts(self, user_id: str, limit: int = 15) -> list[dict]:
        async with self._async_session_factory() as session:
            result = await session.execute(select(UserMemoryFact).where(UserMemoryFact.user_id == user_id).order_by(UserMemoryFact.created_at.desc()).limit(limit))
            facts = result.scalars().all()
            return [
                {
                    "id": fact.id,
                    "content": fact.content,
                    "category": fact.category,
                    "confidence": fact.confidence,
                    "source": fact.source,
                    "createdAt": fact.created_at.isoformat() if fact.created_at else "",
                }
                for fact in facts
            ]
