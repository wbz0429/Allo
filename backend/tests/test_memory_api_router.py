"""API tests for async memory router behavior."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.routers.memory import router
from deerflow import store_registry
from deerflow.stores import MemoryStore


class FakeMemoryStore(MemoryStore):
    async def get_memory(self, user_id: str) -> dict:
        assert user_id == "memory-user-1"
        return {
            "version": "1.0",
            "lastUpdated": "2026-04-03T00:00:00Z",
            "user": {
                "workContext": {"summary": "Works on Allo", "updatedAt": "2026-04-03T00:00:00Z"},
                "personalContext": {"summary": "", "updatedAt": ""},
                "topOfMind": {"summary": "", "updatedAt": ""},
            },
            "history": {
                "recentMonths": {"summary": "", "updatedAt": ""},
                "earlierContext": {"summary": "", "updatedAt": ""},
                "longTermBackground": {"summary": "", "updatedAt": ""},
            },
            "facts": [
                {
                    "id": "fact-1",
                    "content": "User likes green",
                    "category": "preference",
                    "confidence": 0.9,
                    "createdAt": "2026-04-03T00:00:00Z",
                    "source": "thread-1",
                }
            ],
        }

    async def save_memory(self, user_id: str, data: dict) -> None:
        return None

    async def get_facts(self, user_id: str, limit: int = 15) -> list[dict]:
        return []


async def _override_get_auth_context() -> AuthContext:
    return AuthContext(user_id="memory-user-1", org_id="memory-org-1", role="admin")


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_auth_context] = _override_get_auth_context
    monkeypatch.setattr(store_registry, "get_store", lambda name: FakeMemoryStore() if name == "memory" else None)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_memory_reads_async_store_directly(client: AsyncClient) -> None:
    resp = await client.get("/api/memory")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["workContext"]["summary"] == "Works on Allo"
    assert body["facts"][0]["content"] == "User likes green"


@pytest.mark.asyncio
async def test_get_memory_status_reads_async_store_directly(client: AsyncClient) -> None:
    resp = await client.get("/api/memory/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["user"]["workContext"]["summary"] == "Works on Allo"
    assert body["data"]["facts"][0]["content"] == "User likes green"
