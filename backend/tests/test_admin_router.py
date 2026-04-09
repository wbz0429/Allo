from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import Base, Organization, OrganizationMember, UsageRecord, User
from app.gateway.routers.admin import router

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
        session.add_all(
            [
                Organization(id="org-1", name="Org One", slug="org-one"),
                Organization(id="org-2", name="Org Two", slug="org-two"),
                User(id="platform-user-1", email="platform@example.com", password_hash="hash", display_name="Platform User"),
                User(id="user-2", email="user2@example.com", password_hash="hash", display_name="User Two"),
                User(id="user-3", email="user3@example.com", password_hash="hash", display_name="User Three"),
                OrganizationMember(id="m-1", org_id="org-1", user_id="platform-user-1", role="admin"),
                OrganizationMember(id="m-2", org_id="org-1", user_id="user-2", role="member"),
                OrganizationMember(id="m-3", org_id="org-2", user_id="user-3", role="member"),
                UsageRecord(id="r-1", org_id="org-1", user_id="platform-user-1", record_type="api_call", endpoint="/api/threads"),
                UsageRecord(id="r-2", org_id="org-1", user_id="platform-user-1", record_type="api_call", endpoint="/api/threads"),
                UsageRecord(id="r-3", org_id="org-1", user_id="platform-user-1", record_type="llm_token", model_name="gpt-4o", input_tokens=120, output_tokens=30),
                UsageRecord(id="r-4", org_id="org-1", user_id="user-2", record_type="llm_token", model_name="gpt-4o", input_tokens=50, output_tokens=10),
                UsageRecord(id="r-5", org_id="org-2", user_id="user-3", record_type="api_call", endpoint="/api/agents"),
                UsageRecord(id="r-6", org_id="org-2", user_id="user-3", record_type="sandbox_time", duration_seconds=4.5),
            ]
        )
        await session.commit()


@pytest.fixture
async def client():
    transport = ASGITransport(app=_create_test_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_platform_usage_separates_record_types(client: AsyncClient, db_seed: None) -> None:
    resp = await client.get("/api/admin/usage")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_api_calls"] == 3
    assert data["total_input_tokens"] == 170
    assert data["total_output_tokens"] == 40
    assert data["total_sandbox_seconds"] == 4.5
    assert data["total_usage_records"] == 6


@pytest.mark.asyncio
async def test_get_platform_usage_users_defaults_to_total_tokens_ranking(client: AsyncClient, db_seed: None) -> None:
    resp = await client.get("/api/admin/usage/users")

    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "total_tokens"
    assert [item["user_id"] for item in data["items"]] == ["platform-user-1", "user-2", "user-3"]
    assert data["items"][0]["total_tokens"] == 150
    assert data["items"][0]["api_calls"] == 2


@pytest.mark.asyncio
async def test_get_platform_usage_users_supports_api_call_sorting(client: AsyncClient, db_seed: None) -> None:
    resp = await client.get("/api/admin/usage/users?metric=api_calls")

    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "api_calls"
    assert [item["user_id"] for item in data["items"]] == ["platform-user-1", "user-3", "user-2"]
    assert data["items"][1]["api_calls"] == 1
    assert data["items"][2]["api_calls"] == 0


@pytest.mark.asyncio
async def test_get_platform_usage_rejects_non_platform_admin(
    client: AsyncClient,
    db_seed: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_AUTH", "0")
    monkeypatch.setenv("PLATFORM_ADMIN_IDS", "platform-user-1")
    global _CURRENT_AUTH
    _CURRENT_AUTH = AuthContext(user_id="user-2", org_id="org-1", role="member")

    try:
        resp = await client.get("/api/admin/usage")
    finally:
        _CURRENT_AUTH = AuthContext(user_id="platform-user-1", org_id="org-1", role="admin")

    assert resp.status_code == 403
