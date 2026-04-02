"""API tests for skill catalog routes.

Verifies that `/api/skills` and related endpoints use the final Gateway-resolved
skill catalog rather than raw harness-side toggles.
"""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import Base, MarketplaceSkill, OrgInstalledSkill, UserSkillConfig
from app.gateway.routers.skills import router

_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

_AUTH = AuthContext(user_id="api-user-1", org_id="api-org-1", role="admin")


async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


async def _override_get_auth_context() -> AuthContext:
    return _AUTH


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.dependency_overrides[get_auth_context] = _override_get_auth_context
    return app


def _write_skill(skill_dir: Path, name: str, description: str) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


@pytest.fixture(autouse=True)
async def _setup_db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def app() -> FastAPI:
    return _create_test_app()


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def db_seed() -> None:
    async with _test_session_factory() as session:
        session.add_all(
            [
                MarketplaceSkill(
                    id="mp-deep-research",
                    name="Deep Research",
                    runtime_skill_name="deep-research",
                    description="Research skill",
                    category="research",
                    skill_content="# Deep Research",
                    is_public=True,
                ),
                MarketplaceSkill(
                    id="mp-data-analysis",
                    name="Data Analysis",
                    runtime_skill_name="data-analysis",
                    description="Analysis skill",
                    category="data",
                    skill_content="# Data Analysis",
                    is_public=True,
                ),
            ]
        )
        await session.commit()


@pytest.mark.asyncio
async def test_list_skills_returns_final_catalog(client: AsyncClient, db_seed: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "deep-research", "deep-research", "Deep research")
    _write_skill(skills_root / "public" / "data-analysis", "data-analysis", "Data analysis")
    _write_skill(skills_root / "public" / "bootstrap", "bootstrap", "Bootstrap")

    from app.gateway.services import skill_catalog_resolver as resolver_module

    original_load_skills = resolver_module.load_skills

    def patched_load_skills(*args, **kwargs):
        kwargs["skills_path"] = skills_root
        kwargs["use_config"] = False
        return original_load_skills(*args, **kwargs)

    monkeypatch.setattr(resolver_module, "load_skills", patched_load_skills)

    async with _test_session_factory() as session:
        session.add(OrgInstalledSkill(org_id=_AUTH.org_id, skill_id="mp-deep-research"))
        session.add(
            UserSkillConfig(
                user_id=_AUTH.user_id,
                org_id=_AUTH.org_id,
                config_json='{"skills": {"deep-research": {"enabled": false}}}',
            )
        )
        await session.commit()

    resp = await client.get("/api/skills")
    assert resp.status_code == 200

    by_name = {item["name"]: item for item in resp.json()["skills"]}
    assert "bootstrap" in by_name
    assert "deep-research" in by_name
    assert by_name["deep-research"]["enabled"] is False
    assert "data-analysis" not in by_name


@pytest.mark.asyncio
async def test_get_skill_404_when_not_in_final_catalog(client: AsyncClient, db_seed: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "data-analysis", "data-analysis", "Data analysis")

    from app.gateway.services import skill_catalog_resolver as resolver_module

    original_load_skills = resolver_module.load_skills

    def patched_load_skills(*args, **kwargs):
        kwargs["skills_path"] = skills_root
        kwargs["use_config"] = False
        return original_load_skills(*args, **kwargs)

    monkeypatch.setattr(resolver_module, "load_skills", patched_load_skills)

    resp = await client.get("/api/skills/data-analysis")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_skill_round_trips_through_final_catalog(client: AsyncClient, db_seed: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "deep-research", "deep-research", "Deep research")

    from app.gateway.services import skill_catalog_resolver as resolver_module

    original_load_skills = resolver_module.load_skills

    def patched_load_skills(*args, **kwargs):
        kwargs["skills_path"] = skills_root
        kwargs["use_config"] = False
        return original_load_skills(*args, **kwargs)

    monkeypatch.setattr(resolver_module, "load_skills", patched_load_skills)

    async with _test_session_factory() as session:
        session.add(OrgInstalledSkill(org_id=_AUTH.org_id, skill_id="mp-deep-research"))
        await session.commit()

    update_resp = await client.put("/api/skills/deep-research", json={"enabled": False})
    assert update_resp.status_code == 200
    assert update_resp.json()["enabled"] is False

    get_resp = await client.get("/api/skills/deep-research")
    assert get_resp.status_code == 200
    assert get_resp.json()["enabled"] is False

    list_resp = await client.get("/api/skills")
    assert list_resp.status_code == 200
    by_name = {item["name"]: item for item in list_resp.json()["skills"]}
    assert by_name["deep-research"]["enabled"] is False
