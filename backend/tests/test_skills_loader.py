"""Tests for recursive skills loading."""

from pathlib import Path

import pytest

from deerflow.skills.loader import get_skills_root_path, load_skills


def _write_skill(skill_dir: Path, name: str, description: str) -> None:
    """Write a minimal SKILL.md for tests."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_get_skills_root_path_points_to_project_root_skills():
    """get_skills_root_path() should point to deer-flow/skills (sibling of backend/), not backend/packages/skills."""
    path = get_skills_root_path()
    assert path.name == "skills", f"Expected 'skills', got '{path.name}'"
    assert (path.parent / "backend").is_dir(), f"Expected skills path's parent to be project root containing 'backend/', but got {path}"


def test_load_skills_discovers_nested_skills_and_sets_container_paths(tmp_path: Path):
    """Nested skills should be discovered recursively with correct container paths."""
    skills_root = tmp_path / "skills"

    _write_skill(skills_root / "public" / "root-skill", "root-skill", "Root skill")
    _write_skill(skills_root / "public" / "parent" / "child-skill", "child-skill", "Child skill")
    _write_skill(skills_root / "custom" / "team" / "helper", "team-helper", "Team helper")

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    by_name = {skill.name: skill for skill in skills}

    assert {"root-skill", "child-skill", "team-helper"} <= set(by_name)

    root_skill = by_name["root-skill"]
    child_skill = by_name["child-skill"]
    team_skill = by_name["team-helper"]

    assert root_skill.skill_path == "root-skill"
    assert root_skill.get_container_file_path() == "/mnt/skills/public/root-skill/SKILL.md"

    assert child_skill.skill_path == "parent/child-skill"
    assert child_skill.get_container_file_path() == "/mnt/skills/public/parent/child-skill/SKILL.md"

    assert team_skill.skill_path == "team/helper"
    assert team_skill.get_container_file_path() == "/mnt/skills/custom/team/helper/SKILL.md"


def test_load_skills_skips_hidden_directories(tmp_path: Path):
    """Hidden directories should be excluded from recursive discovery."""
    skills_root = tmp_path / "skills"

    _write_skill(skills_root / "public" / "visible" / "ok-skill", "ok-skill", "Visible skill")
    _write_skill(
        skills_root / "public" / "visible" / ".hidden" / "secret-skill",
        "secret-skill",
        "Hidden skill",
    )

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    names = {skill.name for skill in skills}

    assert "ok-skill" in names
    assert "secret-skill" not in names


def test_load_skills_with_user_id_loads_public_and_user_custom_skills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Per-user mode should read public skills from the platform root and custom skills from the user's private directory."""
    skills_root = tmp_path / "skills"
    user_base_dir = tmp_path / ".deer-flow"

    _write_skill(skills_root / "public" / "shared" / "public-skill", "public-skill", "Shared public skill")
    _write_skill(skills_root / "custom" / "legacy" / "legacy-skill", "legacy-skill", "Legacy shared custom skill")
    _write_skill(user_base_dir / "users" / "user-123" / "skills" / "custom" / "private" / "secret-skill", "secret-skill", "Private user skill")

    from deerflow.config.paths import Paths

    monkeypatch.setattr("deerflow.skills.loader.get_paths", lambda: Paths(base_dir=user_base_dir))

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False, user_id="user-123")
    names = {skill.name for skill in skills}

    assert "public-skill" in names
    assert "secret-skill" in names
    assert "legacy-skill" not in names


def test_load_skills_with_user_toggle_store_can_disable_skills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Per-user toggle store should override file-based enabled state when available."""
    skills_root = tmp_path / "skills"
    user_base_dir = tmp_path / ".deer-flow"

    _write_skill(skills_root / "public" / "shared" / "public-skill", "public-skill", "Shared public skill")
    _write_skill(user_base_dir / "users" / "user-123" / "skills" / "custom" / "private" / "secret-skill", "secret-skill", "Private user skill")

    from deerflow.config.paths import Paths

    class FakeSkillConfigStore:
        async def get_skill_toggles(self, user_id: str) -> dict[str, bool]:
            assert user_id == "user-123"
            return {
                "public-skill": False,
                "secret-skill": True,
            }

    monkeypatch.setattr("deerflow.skills.loader.get_paths", lambda: Paths(base_dir=user_base_dir))

    skills = load_skills(
        skills_path=skills_root,
        use_config=False,
        enabled_only=True,
        user_id="user-123",
        skill_config_store=FakeSkillConfigStore(),
    )

    names = {skill.name for skill in skills}
    assert "public-skill" not in names
    assert "secret-skill" in names
