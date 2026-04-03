"""MCP tool and skill marketplace API."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import MarketplaceSkill, MarketplaceTool, OrgInstalledSkill, OrgInstalledTool
from app.gateway.marketplace_seed import SEED_SKILLS, SEED_TOOLS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ---------------------------------------------------------------------------
# Response / Request models
# ---------------------------------------------------------------------------


class ToolResponse(BaseModel):
    """Public marketplace tool."""

    id: str
    name: str
    description: str
    category: str
    icon: str
    is_public: bool


class SkillResponse(BaseModel):
    """Public marketplace skill."""

    id: str
    name: str
    description: str
    category: str
    is_public: bool


class InstalledToolResponse(BaseModel):
    """An installed tool with its marketplace metadata."""

    id: str
    tool: ToolResponse
    config_json: str
    installed_at: str


class InstalledSkillResponse(BaseModel):
    """An installed skill with its marketplace metadata."""

    id: str
    skill: SkillResponse
    installed_at: str


class InstallToolRequest(BaseModel):
    """Request body for installing a tool with optional config."""

    config_json: str = "{}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tool_to_response(tool: MarketplaceTool) -> ToolResponse:
    return ToolResponse(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        category=tool.category,
        icon=tool.icon,
        is_public=tool.is_public,
    )


def _skill_to_response(skill: MarketplaceSkill) -> SkillResponse:
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        category=skill.category,
        is_public=skill.is_public,
    )


_seed_done = False


async def _ensure_seed_data(db: AsyncSession) -> None:
    """Idempotent upsert of seed tools and skills.

    Uses ``merge()`` so rows are inserted on first run and silently
    skipped (or updated) on subsequent runs.  A module-level flag
    avoids repeated DB round-trips after the first successful check.
    """
    global _seed_done
    if _seed_done:
        return

    for tool_data in SEED_TOOLS:
        await db.merge(MarketplaceTool(**tool_data))
    for skill_data in SEED_SKILLS:
        await db.merge(MarketplaceSkill(**skill_data))
    await db.commit()
    _seed_done = True
    logger.info("Marketplace seed data ensured (%d tools, %d skills)", len(SEED_TOOLS), len(SEED_SKILLS))


# ---------------------------------------------------------------------------
# Browse catalog
# ---------------------------------------------------------------------------


@router.get("/tools", response_model=list[ToolResponse], summary="Browse Tools Catalog")
async def list_tools(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[ToolResponse]:
    """Browse public tools in the marketplace catalog."""
    logger.info("Marketplace: list_tools start user_id=%s org_id=%s role=%s", auth.user_id, auth.org_id, auth.role)
    await _ensure_seed_data(db)

    stmt = select(MarketplaceTool).where(MarketplaceTool.is_public.is_(True)).order_by(MarketplaceTool.name)
    result = await db.execute(stmt)
    tools = result.scalars().all()
    logger.info("Marketplace: list_tools success count=%s", len(tools))
    return [_tool_to_response(t) for t in tools]


@router.get("/skills", response_model=list[SkillResponse], summary="Browse Skills Catalog")
async def list_skills(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[SkillResponse]:
    """Browse public skills in the marketplace catalog."""
    logger.info("Marketplace: list_skills start user_id=%s org_id=%s role=%s", auth.user_id, auth.org_id, auth.role)
    await _ensure_seed_data(db)

    stmt = select(MarketplaceSkill).where(MarketplaceSkill.is_public.is_(True)).order_by(MarketplaceSkill.name)
    result = await db.execute(stmt)
    skills = result.scalars().all()
    logger.info("Marketplace: list_skills success count=%s", len(skills))
    return [_skill_to_response(s) for s in skills]


@router.get("/tools/{tool_id}", response_model=ToolResponse, summary="Get Tool Details")
async def get_tool(
    tool_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ToolResponse:
    """Get details for a specific marketplace tool."""
    await _ensure_seed_data(db)

    stmt = select(MarketplaceTool).where(MarketplaceTool.id == tool_id)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return _tool_to_response(tool)


@router.get("/skills/{skill_id}", response_model=SkillResponse, summary="Get Skill Details")
async def get_skill(
    skill_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SkillResponse:
    """Get details for a specific marketplace skill."""
    await _ensure_seed_data(db)

    stmt = select(MarketplaceSkill).where(MarketplaceSkill.id == skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _skill_to_response(skill)


# ---------------------------------------------------------------------------
# Install / Uninstall
# ---------------------------------------------------------------------------


@router.post("/tools/{tool_id}/install", response_model=InstalledToolResponse, status_code=201, summary="Install Tool")
async def install_tool(
    tool_id: str,
    request: InstallToolRequest | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> InstalledToolResponse:
    """Install a marketplace tool for the authenticated organization."""
    # Verify tool exists
    tool_stmt = select(MarketplaceTool).where(MarketplaceTool.id == tool_id)
    tool_result = await db.execute(tool_stmt)
    tool = tool_result.scalar_one_or_none()
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Check for duplicate
    dup_stmt = select(OrgInstalledTool).where(OrgInstalledTool.org_id == auth.org_id, OrgInstalledTool.tool_id == tool_id)
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Tool already installed")

    config_json = request.config_json if request else "{}"
    installed = OrgInstalledTool(org_id=auth.org_id, tool_id=tool_id, config_json=config_json)
    db.add(installed)
    await db.commit()
    await db.refresh(installed)

    logger.info(f"Installed tool {tool_id} for org={auth.org_id}")
    return InstalledToolResponse(
        id=installed.id,
        tool=_tool_to_response(tool),
        config_json=installed.config_json,
        installed_at=installed.installed_at.isoformat() if installed.installed_at else "",
    )


@router.delete("/tools/{tool_id}/install", status_code=204, summary="Uninstall Tool")
async def uninstall_tool(
    tool_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Uninstall a marketplace tool from the authenticated organization."""
    stmt = select(OrgInstalledTool).where(OrgInstalledTool.org_id == auth.org_id, OrgInstalledTool.tool_id == tool_id)
    result = await db.execute(stmt)
    installed = result.scalar_one_or_none()
    if installed is None:
        raise HTTPException(status_code=404, detail="Tool not installed")

    await db.delete(installed)
    await db.commit()
    logger.info(f"Uninstalled tool {tool_id} for org={auth.org_id}")


@router.post("/skills/{skill_id}/install", response_model=InstalledSkillResponse, status_code=201, summary="Install Skill")
async def install_skill(
    skill_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> InstalledSkillResponse:
    """Install a marketplace skill for the authenticated organization."""
    skill_stmt = select(MarketplaceSkill).where(MarketplaceSkill.id == skill_id)
    skill_result = await db.execute(skill_stmt)
    skill = skill_result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    dup_stmt = select(OrgInstalledSkill).where(OrgInstalledSkill.org_id == auth.org_id, OrgInstalledSkill.skill_id == skill_id)
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Skill already installed")

    installed = OrgInstalledSkill(org_id=auth.org_id, skill_id=skill_id)
    db.add(installed)
    await db.commit()
    await db.refresh(installed)

    logger.info(f"Installed skill {skill_id} for org={auth.org_id}")
    return InstalledSkillResponse(
        id=installed.id,
        skill=_skill_to_response(skill),
        installed_at=installed.installed_at.isoformat() if installed.installed_at else "",
    )


@router.delete("/skills/{skill_id}/install", status_code=204, summary="Uninstall Skill")
async def uninstall_skill(
    skill_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Uninstall a marketplace skill from the authenticated organization."""
    stmt = select(OrgInstalledSkill).where(OrgInstalledSkill.org_id == auth.org_id, OrgInstalledSkill.skill_id == skill_id)
    result = await db.execute(stmt)
    installed = result.scalar_one_or_none()
    if installed is None:
        raise HTTPException(status_code=404, detail="Skill not installed")

    await db.delete(installed)
    await db.commit()
    logger.info(f"Uninstalled skill {skill_id} for org={auth.org_id}")


# ---------------------------------------------------------------------------
# Installed items
# ---------------------------------------------------------------------------


@router.get("/installed/tools", response_model=list[InstalledToolResponse], summary="List Installed Tools")
async def list_installed_tools(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[InstalledToolResponse]:
    """List tools installed by the authenticated organization."""
    stmt = select(OrgInstalledTool).where(OrgInstalledTool.org_id == auth.org_id).order_by(OrgInstalledTool.installed_at.desc())
    result = await db.execute(stmt)
    installed_tools = result.scalars().all()

    responses: list[InstalledToolResponse] = []
    for it in installed_tools:
        tool_stmt = select(MarketplaceTool).where(MarketplaceTool.id == it.tool_id)
        tool_result = await db.execute(tool_stmt)
        tool = tool_result.scalar_one_or_none()
        if tool is None:
            continue
        responses.append(
            InstalledToolResponse(
                id=it.id,
                tool=_tool_to_response(tool),
                config_json=it.config_json,
                installed_at=it.installed_at.isoformat() if it.installed_at else "",
            )
        )
    return responses


@router.get("/installed/skills", response_model=list[InstalledSkillResponse], summary="List Installed Skills")
async def list_installed_skills(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[InstalledSkillResponse]:
    """List skills installed by the authenticated organization."""
    stmt = select(OrgInstalledSkill).where(OrgInstalledSkill.org_id == auth.org_id).order_by(OrgInstalledSkill.installed_at.desc())
    result = await db.execute(stmt)
    installed_skills = result.scalars().all()

    responses: list[InstalledSkillResponse] = []
    for is_ in installed_skills:
        skill_stmt = select(MarketplaceSkill).where(MarketplaceSkill.id == is_.skill_id)
        skill_result = await db.execute(skill_stmt)
        skill = skill_result.scalar_one_or_none()
        if skill is None:
            continue
        responses.append(
            InstalledSkillResponse(
                id=is_.id,
                skill=_skill_to_response(skill),
                installed_at=is_.installed_at.isoformat() if is_.installed_at else "",
            )
        )
    return responses
