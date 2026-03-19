"""Tests for the marketplace seed data."""

import json

from app.gateway.marketplace_seed import SEED_SKILLS, SEED_TOOLS

# ---------------------------------------------------------------------------
# SEED_TOOLS
# ---------------------------------------------------------------------------


class TestSeedTools:
    def test_seed_tools_is_list(self) -> None:
        assert isinstance(SEED_TOOLS, list)

    def test_seed_tools_has_entries(self) -> None:
        assert len(SEED_TOOLS) >= 5

    def test_each_tool_has_required_fields(self) -> None:
        required = {"id", "name", "description", "category", "icon", "mcp_config_json", "is_public"}
        for tool in SEED_TOOLS:
            missing = required - set(tool.keys())
            assert not missing, f"Tool '{tool.get('name', '?')}' missing fields: {missing}"

    def test_tool_ids_are_unique(self) -> None:
        ids = [t["id"] for t in SEED_TOOLS]
        assert len(ids) == len(set(ids))

    def test_tool_names_are_unique(self) -> None:
        names = [t["name"] for t in SEED_TOOLS]
        assert len(names) == len(set(names))

    def test_mcp_config_json_is_valid_json(self) -> None:
        for tool in SEED_TOOLS:
            parsed = json.loads(tool["mcp_config_json"])
            assert isinstance(parsed, dict)

    def test_all_tools_are_public(self) -> None:
        for tool in SEED_TOOLS:
            assert tool["is_public"] is True

    def test_categories_are_valid(self) -> None:
        valid_categories = {"search", "code", "data", "communication"}
        for tool in SEED_TOOLS:
            assert tool["category"] in valid_categories, f"Tool '{tool['name']}' has invalid category '{tool['category']}'"

    def test_tavily_search_exists(self) -> None:
        names = [t["name"] for t in SEED_TOOLS]
        assert "Tavily Search" in names

    def test_mcp_config_has_command(self) -> None:
        for tool in SEED_TOOLS:
            config = json.loads(tool["mcp_config_json"])
            assert "command" in config, f"Tool '{tool['name']}' MCP config missing 'command'"


# ---------------------------------------------------------------------------
# SEED_SKILLS
# ---------------------------------------------------------------------------


class TestSeedSkills:
    def test_seed_skills_is_list(self) -> None:
        assert isinstance(SEED_SKILLS, list)

    def test_seed_skills_has_entries(self) -> None:
        assert len(SEED_SKILLS) >= 3

    def test_each_skill_has_required_fields(self) -> None:
        required = {"id", "name", "description", "category", "skill_content", "is_public"}
        for skill in SEED_SKILLS:
            missing = required - set(skill.keys())
            assert not missing, f"Skill '{skill.get('name', '?')}' missing fields: {missing}"

    def test_skill_ids_are_unique(self) -> None:
        ids = [s["id"] for s in SEED_SKILLS]
        assert len(ids) == len(set(ids))

    def test_skill_names_are_unique(self) -> None:
        names = [s["name"] for s in SEED_SKILLS]
        assert len(names) == len(set(names))

    def test_all_skills_are_public(self) -> None:
        for skill in SEED_SKILLS:
            assert skill["is_public"] is True

    def test_skill_content_is_nonempty(self) -> None:
        for skill in SEED_SKILLS:
            assert skill["skill_content"].strip(), f"Skill '{skill['name']}' has empty content"

    def test_deep_research_skill_exists(self) -> None:
        names = [s["name"] for s in SEED_SKILLS]
        assert "Deep Research" in names
