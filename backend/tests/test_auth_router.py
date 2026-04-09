from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import Base, User
from app.gateway.routers.auth import router

_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

_CURRENT_AUTH = AuthContext(user_id="platform-user-1", org_id="org-1", role="admin")


async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


async def _override_get_auth_context() -> AuthContext:
    return _CURRENT_AUTH


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
async def db_seed() -> None:
    async with _test_session_factory() as session:
        session.add(
            User(
                id="platform-user-1",
                email="platform@example.com",
                password_hash="hash",
                display_name="Platform User",
            )
        )
        await session.commit()


@pytest.fixture
async def client():
    transport = ASGITransport(app=_create_test_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_session_returns_platform_admin_flag_true(client: AsyncClient, db_seed: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_AUTH", "0")
    monkeypatch.setenv("PLATFORM_ADMIN_IDS", "platform-user-1")

    resp = await client.get("/api/auth/session")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "platform-user-1"
    assert data["is_platform_admin"] is True


@pytest.mark.asyncio
async def test_get_session_returns_platform_admin_flag_false_when_user_not_in_allowlist(
    client: AsyncClient,
    db_seed: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_AUTH", "0")
    monkeypatch.setenv("PLATFORM_ADMIN_IDS", "another-user")

    resp = await client.get("/api/auth/session")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "platform-user-1"
    assert data["is_platform_admin"] is False
