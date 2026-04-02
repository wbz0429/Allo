"""Unified skill catalog resolver for Gateway layer.

Resolves the final skill catalog for a user by combining:
1. Built-in public skills
2. Marketplace installed skills (org-level gating)
3. User custom skills
4. User-level toggles

This resolver ensures /api/skills and runtime load_skills() return consistent results.
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.db.models import MarketplaceSkill, OrgInstalledSkill, UserSkillConfig
from deerflow.skills import Skill, load_skills

logger = logging.getLogger(__name__)


async def get_user_skill_catalog(
    user_id: str,
    org_id: str,
    db: AsyncSession,
    enabled_only: bool = False,
) -> list[Skill]:
    """Resolve the final skill catalog for a user.

    Args:
        user_id: User ID
        org_id: Organization ID
        db: Database session
        enabled_only: If True, only return enabled skills

    Returns:
        List of Skill objects representing the user's final catalog
    """
    # Step 1: Load all public skills (file-based discovery)
    all_skills = load_skills(enabled_only=False, user_id=user_id, use_config=True)

    # Step 2: Get marketplace managed skills
    managed_result = await db.execute(select(MarketplaceSkill.runtime_skill_name).where(MarketplaceSkill.runtime_skill_name.is_not(None)))
    managed_skills = {name for name in managed_result.scalars().all() if name}

    # Step 3: Get org installed skills
    installed_result = await db.execute(
        select(MarketplaceSkill.runtime_skill_name).join(OrgInstalledSkill, OrgInstalledSkill.skill_id == MarketplaceSkill.id).where(OrgInstalledSkill.org_id == org_id, MarketplaceSkill.runtime_skill_name.is_not(None))
    )
    installed_skills = {name for name in installed_result.scalars().all() if name}

    # Step 4: Get user toggles
    toggles_result = await db.execute(select(UserSkillConfig).where(UserSkillConfig.user_id == user_id, UserSkillConfig.org_id == org_id).order_by(UserSkillConfig.updated_at.desc()).limit(1))
    config_record = toggles_result.scalar_one_or_none()

    user_toggles: dict[str, bool] = {}
    if config_record is not None:
        try:
            payload = json.loads(config_record.config_json)
            skills_payload = payload.get("skills", {}) if isinstance(payload, dict) else {}
            user_toggles = {name: bool(value.get("enabled", True)) for name, value in skills_payload.items() if isinstance(value, dict)}
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse skill config for user {user_id}")

    # Step 5: Apply gating and toggles
    final_catalog = []
    for skill in all_skills:
        # Marketplace gating: if skill is managed but not installed, skip it
        if skill.name in managed_skills and skill.name not in installed_skills:
            logger.debug(f"Skill {skill.name} is managed by marketplace but not installed for org {org_id}, excluding from catalog")
            continue

        # Apply user toggle if present
        if skill.name in user_toggles:
            skill.enabled = user_toggles[skill.name]

        # Filter by enabled status if requested
        if enabled_only and not skill.enabled:
            continue

        final_catalog.append(skill)

    logger.info(f"Resolved skill catalog for user {user_id}, org {org_id}: {len(final_catalog)} skills (enabled_only={enabled_only})")
    return final_catalog
