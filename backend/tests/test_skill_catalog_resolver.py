"""Tests for unified skill catalog resolver.

Verifies that the resolver correctly combines:
1. Built-in public skills
2. Marketplace installed skills (org-level gating)
3. User custom skills
4. User-level toggles
"""

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.gateway.db.database import DATABASE_URL
from app.gateway.db.models import MarketplaceSkill, Organization, OrgInstalledSkill, User, UserSkillConfig
from app.gateway.services.skill_catalog_resolver import get_user_skill_catalog


@pytest.fixture
async def db_session():
    """Provide a database session for tests."""
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
    await engine.dispose()


def _write_skill(skill_dir: Path, name: str, description: str) -> None:
    """Write a minimal SKILL.md for tests."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


@pytest.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    suffix = uuid.uuid4().hex[:8]
    org = Organization(id=f"org-test-{suffix}", name="Test Org", slug=f"test-org-{suffix}")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def test_user(db_session: AsyncSession, test_org: Organization) -> User:
    """Create a test user."""
    suffix = uuid.uuid4().hex[:8]
    user = User(id=f"user-test-{suffix}", email=f"test-{suffix}@example.com", password_hash="dummy_hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def marketplace_skills(db_session: AsyncSession) -> dict[str, MarketplaceSkill]:
    """Create marketplace skills with runtime mappings."""
    suffix = uuid.uuid4().hex[:8]
    skills = {
        "deep-research": MarketplaceSkill(
            id=f"skill-deep-research-{suffix}",
            name=f"Deep Research {suffix}",
            runtime_skill_name="deep-research",
            description="Multi-step research skill",
            category="research",
            skill_content="# Deep Research\n\nResearch workflow...",
            is_public=True,
        ),
        "data-analysis": MarketplaceSkill(
            id=f"skill-data-analysis-{suffix}",
            name=f"Data Analysis {suffix}",
            runtime_skill_name="data-analysis",
            description="Data analysis skill",
            category="data",
            skill_content="# Data Analysis\n\nAnalysis workflow...",
            is_public=True,
        ),
        "code-review": MarketplaceSkill(
            id=f"skill-code-review-{suffix}",
            name=f"Code Review {suffix}",
            runtime_skill_name=None,  # Not managed at runtime
            description="Code review skill",
            category="coding",
            skill_content="# Code Review\n\nReview workflow...",
            is_public=True,
        ),
    }
    for skill in skills.values():
        db_session.add(skill)
    await db_session.commit()
    for skill in skills.values():
        await db_session.refresh(skill)
    return skills


@pytest.mark.asyncio
async def test_resolver_excludes_uninstalled_marketplace_skills(
    db_session: AsyncSession,
    test_user: User,
    test_org: Organization,
    marketplace_skills: dict[str, MarketplaceSkill],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Marketplace-managed skills should be excluded if not installed by org."""
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "deep-research", "deep-research", "Deep research skill")
    _write_skill(skills_root / "public" / "data-analysis", "data-analysis", "Data analysis skill")
    _write_skill(skills_root / "public" / "bootstrap", "bootstrap", "Bootstrap skill")

    # Patch load_skills to use our test skills directory
    from app.gateway.services import skill_catalog_resolver as resolver_module

    original_load_skills = resolver_module.load_skills

    def patched_load_skills(*args, **kwargs):
        kwargs["skills_path"] = skills_root
        kwargs["use_config"] = False
        return original_load_skills(*args, **kwargs)

    monkeypatch.setattr(resolver_module, "load_skills", patched_load_skills)

    # Don't install any marketplace skills for this org
    catalog = await get_user_skill_catalog(
        user_id=test_user.id,
        org_id=test_org.id,
        db=db_session,
        enabled_only=False,
    )

    skill_names = {skill.name for skill in catalog}

    # deep-research and data-analysis are managed by marketplace but not installed
    assert "deep-research" not in skill_names
    assert "data-analysis" not in skill_names

    # bootstrap is not managed by marketplace, so it should be included
    assert "bootstrap" in skill_names


@pytest.mark.asyncio
async def test_resolver_includes_installed_marketplace_skills(
    db_session: AsyncSession,
    test_user: User,
    test_org: Organization,
    marketplace_skills: dict[str, MarketplaceSkill],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Marketplace-managed skills should be included if installed by org."""
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "deep-research", "deep-research", "Deep research skill")
    _write_skill(skills_root / "public" / "data-analysis", "data-analysis", "Data analysis skill")
    _write_skill(skills_root / "public" / "bootstrap", "bootstrap", "Bootstrap skill")

    # Patch load_skills
    from app.gateway.services import skill_catalog_resolver as resolver_module

    original_load_skills = resolver_module.load_skills

    def patched_load_skills(*args, **kwargs):
        kwargs["skills_path"] = skills_root
        kwargs["use_config"] = False
        return original_load_skills(*args, **kwargs)

    monkeypatch.setattr(resolver_module, "load_skills", patched_load_skills)

    # Install deep-research for this org
    install = OrgInstalledSkill(
        org_id=test_org.id,
        skill_id=marketplace_skills["deep-research"].id,
    )
    db_session.add(install)
    await db_session.commit()

    catalog = await get_user_skill_catalog(
        user_id=test_user.id,
        org_id=test_org.id,
        db=db_session,
        enabled_only=False,
    )

    skill_names = {skill.name for skill in catalog}

    # deep-research is installed, should be included
    assert "deep-research" in skill_names

    # data-analysis is managed but not installed, should be excluded
    assert "data-analysis" not in skill_names

    # bootstrap is not managed, should be included
    assert "bootstrap" in skill_names


@pytest.mark.asyncio
async def test_resolver_applies_user_toggles(
    db_session: AsyncSession,
    test_user: User,
    test_org: Organization,
    marketplace_skills: dict[str, MarketplaceSkill],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User toggles should override default enabled state."""
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "deep-research", "deep-research", "Deep research skill")
    _write_skill(skills_root / "public" / "bootstrap", "bootstrap", "Bootstrap skill")

    # Patch load_skills
    from app.gateway.services import skill_catalog_resolver as resolver_module

    original_load_skills = resolver_module.load_skills

    def patched_load_skills(*args, **kwargs):
        kwargs["skills_path"] = skills_root
        kwargs["use_config"] = False
        return original_load_skills(*args, **kwargs)

    monkeypatch.setattr(resolver_module, "load_skills", patched_load_skills)

    # Install deep-research
    install = OrgInstalledSkill(
        org_id=test_org.id,
        skill_id=marketplace_skills["deep-research"].id,
    )
    db_session.add(install)

    # Set user toggles: disable deep-research, enable bootstrap
    user_config = UserSkillConfig(
        user_id=test_user.id,
        org_id=test_org.id,
        config_json=json.dumps(
            {
                "skills": {
                    "deep-research": {"enabled": False},
                    "bootstrap": {"enabled": True},
                }
            }
        ),
    )
    db_session.add(user_config)
    await db_session.commit()

    catalog = await get_user_skill_catalog(
        user_id=test_user.id,
        org_id=test_org.id,
        db=db_session,
        enabled_only=False,
    )

    by_name = {skill.name: skill for skill in catalog}

    # deep-research is installed but disabled by user
    assert "deep-research" in by_name
    assert by_name["deep-research"].enabled is False

    # bootstrap is enabled by user
    assert "bootstrap" in by_name
    assert by_name["bootstrap"].enabled is True


@pytest.mark.asyncio
async def test_resolver_enabled_only_filter(
    db_session: AsyncSession,
    test_user: User,
    test_org: Organization,
    marketplace_skills: dict[str, MarketplaceSkill],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """enabled_only=True should filter out disabled skills."""
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "deep-research", "deep-research", "Deep research skill")
    _write_skill(skills_root / "public" / "bootstrap", "bootstrap", "Bootstrap skill")

    # Patch load_skills
    from app.gateway.services import skill_catalog_resolver as resolver_module

    original_load_skills = resolver_module.load_skills

    def patched_load_skills(*args, **kwargs):
        kwargs["skills_path"] = skills_root
        kwargs["use_config"] = False
        return original_load_skills(*args, **kwargs)

    monkeypatch.setattr(resolver_module, "load_skills", patched_load_skills)

    # Install deep-research
    install = OrgInstalledSkill(
        org_id=test_org.id,
        skill_id=marketplace_skills["deep-research"].id,
    )
    db_session.add(install)

    # Disable deep-research
    user_config = UserSkillConfig(
        user_id=test_user.id,
        org_id=test_org.id,
        config_json=json.dumps({"skills": {"deep-research": {"enabled": False}}}),
    )
    db_session.add(user_config)
    await db_session.commit()

    catalog = await get_user_skill_catalog(
        user_id=test_user.id,
        org_id=test_org.id,
        db=db_session,
        enabled_only=True,
    )

    skill_names = {skill.name for skill in catalog}

    # deep-research is disabled, should not be in enabled_only catalog
    assert "deep-research" not in skill_names

    # bootstrap is enabled by default, should be included
    assert "bootstrap" in skill_names


@pytest.mark.asyncio
async def test_resolver_multi_org_isolation(
    db_session: AsyncSession,
    marketplace_skills: dict[str, MarketplaceSkill],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Different orgs should have isolated skill catalogs."""
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "deep-research", "deep-research", "Deep research skill")
    _write_skill(skills_root / "public" / "data-analysis", "data-analysis", "Data analysis skill")

    # Patch load_skills
    from app.gateway.services import skill_catalog_resolver as resolver_module

    original_load_skills = resolver_module.load_skills

    def patched_load_skills(*args, **kwargs):
        kwargs["skills_path"] = skills_root
        kwargs["use_config"] = False
        return original_load_skills(*args, **kwargs)

    monkeypatch.setattr(resolver_module, "load_skills", patched_load_skills)

    # Create two orgs and users
    suffix = uuid.uuid4().hex[:8]
    org_a = Organization(id=f"org-a-{suffix}", name="Org A", slug=f"org-a-{suffix}")
    org_b = Organization(id=f"org-b-{suffix}", name="Org B", slug=f"org-b-{suffix}")
    db_session.add_all([org_a, org_b])
    await db_session.commit()

    user_a = User(id=f"user-a-{suffix}", email=f"a-{suffix}@example.com", password_hash="dummy_hash")
    user_b = User(id=f"user-b-{suffix}", email=f"b-{suffix}@example.com", password_hash="dummy_hash")
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # Org A installs deep-research
    install_a = OrgInstalledSkill(org_id=org_a.id, skill_id=marketplace_skills["deep-research"].id)
    db_session.add(install_a)

    # Org B installs data-analysis
    install_b = OrgInstalledSkill(org_id=org_b.id, skill_id=marketplace_skills["data-analysis"].id)
    db_session.add(install_b)
    await db_session.commit()

    # Get catalogs for both users
    catalog_a = await get_user_skill_catalog(user_id=user_a.id, org_id=org_a.id, db=db_session, enabled_only=False)
    catalog_b = await get_user_skill_catalog(user_id=user_b.id, org_id=org_b.id, db=db_session, enabled_only=False)

    names_a = {skill.name for skill in catalog_a}
    names_b = {skill.name for skill in catalog_b}

    # Org A has deep-research but not data-analysis
    assert "deep-research" in names_a
    assert "data-analysis" not in names_a

    # Org B has data-analysis but not deep-research
    assert "data-analysis" in names_b
    assert "deep-research" not in names_b
