from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import Base
from app.gateway.routers.threads import router

_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

_DEV_AUTH = AuthContext(user_id="dev-user-000", org_id="dev-org-000", role="admin")


async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


async def _override_get_auth_context() -> AuthContext:
    return _DEV_AUTH


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.dependency_overrides[get_auth_context] = _override_get_auth_context
    return app


@pytest.fixture(autouse=True)
async def _setup_db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def app():
    return _create_test_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_thread_retries_langgraph_sync_on_timeout(client):
    post = AsyncMock(side_effect=[httpx.ReadTimeout("timed out"), MagicMock(status_code=200, text="ok")])
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = post

    with patch("app.gateway.routers.threads.httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(
            "/api/threads",
            json={
                "thread_id": "thread-retry-1",
                "title": "New Thread",
                "status": "active",
            },
        )

    assert resp.status_code == 201
    assert post.await_count == 2
    assert resp.json()["thread_id"] == "thread-retry-1"
