import json
import logging
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import UserSkillConfig
from app.gateway.path_utils import resolve_thread_virtual_path
from app.gateway.services.skill_catalog_resolver import get_user_skill_catalog
from deerflow.config.paths import get_paths
from deerflow.skills import Skill
from deerflow.skills.validation import _validate_skill_frontmatter

logger = logging.getLogger(__name__)


async def _get_user_skill_toggles(db: AsyncSession, auth: AuthContext) -> dict[str, bool]:
    result = await db.execute(select(UserSkillConfig).where(UserSkillConfig.user_id == auth.user_id, UserSkillConfig.org_id == auth.org_id).order_by(UserSkillConfig.updated_at.desc()).limit(1))
    record = result.scalar_one_or_none()
    if record is None:
        return {}

    try:
        payload = json.loads(record.config_json)
    except json.JSONDecodeError:
        return {}

    raw = payload.get("skills", {}) if isinstance(payload, dict) else {}
    return {name: bool(value.get("enabled", True)) for name, value in raw.items() if isinstance(value, dict)}


def _apply_user_toggles(skills: list[Skill], toggles: dict[str, bool]) -> list[Skill]:
    for skill in skills:
        if skill.name in toggles:
            skill.enabled = toggles[skill.name]
    return skills


def _is_unsafe_zip_member(info: zipfile.ZipInfo) -> bool:
    """Return True if the zip member path is absolute or attempts directory traversal."""
    name = info.filename
    if not name:
        return False
    path = Path(name)
    if path.is_absolute():
        return True
    if ".." in path.parts:
        return True
    return False


def _is_symlink_member(info: zipfile.ZipInfo) -> bool:
    """Detect symlinks based on the external attributes stored in the ZipInfo."""
    # Upper 16 bits of external_attr contain the Unix file mode when created on Unix.
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)


def _safe_extract_skill_archive(
    zip_ref: zipfile.ZipFile,
    dest_path: Path,
    max_total_size: int = 512 * 1024 * 1024,
) -> None:
    """Safely extract a skill archive into dest_path with basic protections.

    Protections:
    - Reject absolute paths and directory traversal (..).
    - Skip symlink entries instead of materialising them.
    - Enforce a hard limit on total uncompressed size to mitigate zip bombs.
    """
    dest_root = Path(dest_path).resolve()
    total_size = 0

    for info in zip_ref.infolist():
        # Reject absolute paths or any path that attempts directory traversal.
        if _is_unsafe_zip_member(info):
            raise HTTPException(
                status_code=400,
                detail=f"Archive contains unsafe member path: {info.filename!r}",
            )

        # Skip any symlink entries instead of materialising them on disk.
        if _is_symlink_member(info):
            logger.warning("Skipping symlink entry in skill archive: %s", info.filename)
            continue

        # Basic unzip-bomb defence: bound the total uncompressed size we will write.
        total_size += max(info.file_size, 0)
        if total_size > max_total_size:
            raise HTTPException(
                status_code=400,
                detail="Skill archive is too large or appears highly compressed.",
            )

        member_path = dest_root / info.filename
        member_path_parent = member_path.parent
        member_path_parent.mkdir(parents=True, exist_ok=True)

        if info.is_dir():
            member_path.mkdir(parents=True, exist_ok=True)
            continue

        with zip_ref.open(info) as src, open(member_path, "wb") as dst:
            shutil.copyfileobj(src, dst)


router = APIRouter(prefix="/api", tags=["skills"])


class SkillResponse(BaseModel):
    """Response model for skill information."""

    name: str = Field(..., description="Name of the skill")
    description: str = Field(..., description="Description of what the skill does")
    license: str | None = Field(None, description="License information")
    category: str = Field(..., description="Category of the skill (public or custom)")
    enabled: bool = Field(default=True, description="Whether this skill is enabled")


class SkillsListResponse(BaseModel):
    """Response model for listing all skills."""

    skills: list[SkillResponse]


class SkillUpdateRequest(BaseModel):
    """Request model for updating a skill."""

    enabled: bool = Field(..., description="Whether to enable or disable the skill")


class SkillInstallRequest(BaseModel):
    """Request model for installing a skill from a .skill file."""

    thread_id: str = Field(..., description="The thread ID where the .skill file is located")
    path: str = Field(..., description="Virtual path to the .skill file (e.g., mnt/user-data/outputs/my-skill.skill)")


class SkillInstallResponse(BaseModel):
    """Response model for skill installation."""

    success: bool = Field(..., description="Whether the installation was successful")
    skill_name: str = Field(..., description="Name of the installed skill")
    message: str = Field(..., description="Installation result message")


def _should_ignore_archive_entry(path: Path) -> bool:
    return path.name.startswith(".") or path.name == "__MACOSX"


def _resolve_skill_dir_from_archive_root(temp_path: Path) -> Path:
    extracted_items = [item for item in temp_path.iterdir() if not _should_ignore_archive_entry(item)]
    if len(extracted_items) == 0:
        raise HTTPException(status_code=400, detail="Skill archive is empty")
    if len(extracted_items) == 1 and extracted_items[0].is_dir():
        return extracted_items[0]
    return temp_path


def _get_user_custom_skills_dir(user_id: str) -> Path:
    """Get the per-user custom skills directory, creating it if needed."""
    custom_dir = get_paths().user_skills_dir(user_id)
    custom_dir.mkdir(parents=True, exist_ok=True)
    return custom_dir


def _install_skill_from_zip(zip_path: Path, target_base_dir: Path, overwrite: bool = False) -> tuple[str, str]:
    """Extract, validate, and install a skill from a zip/skill file.

    Returns (skill_name, message) on success.
    Raises HTTPException on failure.
    """
    if not zipfile.is_zipfile(zip_path):
        raise HTTPException(status_code=400, detail="File is not a valid ZIP archive")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            _safe_extract_skill_archive(zip_ref, temp_path)

        skill_dir = _resolve_skill_dir_from_archive_root(temp_path)

        is_valid, message, skill_name = _validate_skill_frontmatter(skill_dir)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid skill: {message}")
        if not skill_name:
            raise HTTPException(status_code=400, detail="Could not determine skill name")

        target_dir = target_base_dir / skill_name
        if target_dir.exists():
            if overwrite:
                shutil.rmtree(target_dir)
            else:
                raise HTTPException(status_code=409, detail=f"Skill '{skill_name}' already exists. Remove it first or use a different name.")

        shutil.copytree(skill_dir, target_dir)

    return skill_name, f"Skill '{skill_name}' installed successfully"


def _skill_to_response(skill: Skill) -> SkillResponse:
    """Convert a Skill object to a SkillResponse."""
    return SkillResponse(
        name=skill.name,
        description=skill.description,
        license=skill.license,
        category=skill.category,
        enabled=skill.enabled,
    )


@router.get(
    "/skills",
    response_model=SkillsListResponse,
    summary="List All Skills",
    description="Retrieve a list of all available skills from both public and custom directories.",
)
async def list_skills(auth: AuthContext = Depends(get_auth_context), db: AsyncSession = Depends(get_db_session)) -> SkillsListResponse:
    """List all available skills.

    Returns the user's final skill catalog, which includes:
    - Built-in public skills (excluding marketplace-managed skills not installed by org)
    - User custom skills
    - With user-level toggles applied

    Returns:
        A list of all skills with their metadata.

    Example Response:
        ```json
        {
            "skills": [
                {
                    "name": "PDF Processing",
                    "description": "Extract and analyze PDF content",
                    "license": "MIT",
                    "category": "public",
                    "enabled": true
                },
                {
                    "name": "Frontend Design",
                    "description": "Generate frontend designs and components",
                    "license": null,
                    "category": "custom",
                    "enabled": false
                }
            ]
        }
        ```
    """
    try:
        skills = await get_user_skill_catalog(user_id=auth.user_id, org_id=auth.org_id, db=db, enabled_only=False)
        return SkillsListResponse(skills=[_skill_to_response(skill) for skill in skills])
    except Exception as e:
        logger.error(f"Failed to load skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load skills: {str(e)}")


@router.get(
    "/skills/{skill_name}",
    response_model=SkillResponse,
    summary="Get Skill Details",
    description="Retrieve detailed information about a specific skill by its name.",
)
async def get_skill(skill_name: str, auth: AuthContext = Depends(get_auth_context), db: AsyncSession = Depends(get_db_session)) -> SkillResponse:
    """Get a specific skill by name.

    Args:
        skill_name: The name of the skill to retrieve.

    Returns:
        Skill information if found.

    Raises:
        HTTPException: 404 if skill not found.

    Example Response:
        ```json
        {
            "name": "PDF Processing",
            "description": "Extract and analyze PDF content",
            "license": "MIT",
            "category": "public",
            "enabled": true
        }
        ```
    """
    try:
        skills = await get_user_skill_catalog(user_id=auth.user_id, org_id=auth.org_id, db=db, enabled_only=False)
        skill = next((s for s in skills if s.name == skill_name), None)

        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        return _skill_to_response(skill)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get skill: {str(e)}")


@router.put(
    "/skills/{skill_name}",
    response_model=SkillResponse,
    summary="Update Skill",
    description="Update a skill's enabled status by modifying the user skill config.",
)
async def update_skill(
    skill_name: str,
    request: SkillUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SkillResponse:
    """Update a skill's enabled status.

    This will modify the user_skill_configs table to update the enabled state.
    The SKILL.md file itself is not modified.

    Args:
        skill_name: The name of the skill to update.
        request: The update request containing the new enabled status.

    Returns:
        The updated skill information.

    Raises:
        HTTPException: 404 if skill not found, 500 if update fails.

    Example Request:
        ```json
        {
            "enabled": false
        }
        ```

    Example Response:
        ```json
        {
            "name": "PDF Processing",
            "description": "Extract and analyze PDF content",
            "license": "MIT",
            "category": "public",
            "enabled": false
        }
        ```
    """
    try:
        # Find the skill to verify it exists
        skills = await get_user_skill_catalog(user_id=auth.user_id, org_id=auth.org_id, db=db, enabled_only=False)
        skill = next((s for s in skills if s.name == skill_name), None)

        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        result = await db.execute(select(UserSkillConfig).where(UserSkillConfig.user_id == auth.user_id, UserSkillConfig.org_id == auth.org_id).order_by(UserSkillConfig.updated_at.desc()).limit(1))
        record = result.scalar_one_or_none()

        payload: dict[str, dict] = {"skills": {}}
        if record is not None:
            try:
                existing = json.loads(record.config_json)
                if isinstance(existing, dict):
                    payload = existing
            except json.JSONDecodeError:
                payload = {"skills": {}}

        skills_payload = payload.get("skills")
        if not isinstance(skills_payload, dict):
            skills_payload = {}
            payload["skills"] = skills_payload
        skills_payload[skill_name] = {"enabled": request.enabled}

        payload_json = json.dumps(payload, ensure_ascii=False)
        if record is None:
            record = UserSkillConfig(user_id=auth.user_id, org_id=auth.org_id, config_json=payload_json)
            db.add(record)
        else:
            record.config_json = payload_json

        await db.commit()
        await db.refresh(record)

        skills = await get_user_skill_catalog(user_id=auth.user_id, org_id=auth.org_id, db=db, enabled_only=False)
        updated_skill = next((s for s in skills if s.name == skill_name), None)

        if updated_skill is None:
            raise HTTPException(status_code=500, detail=f"Failed to reload skill '{skill_name}' after update")

        logger.info(f"Skill '{skill_name}' enabled status updated to {request.enabled}")
        return _skill_to_response(updated_skill)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update skill: {str(e)}")


@router.delete(
    "/skills/{skill_name}",
    summary="Delete Custom Skill",
    description="Delete a user-uploaded custom skill by name.",
)
async def delete_skill(skill_name: str, auth: AuthContext = Depends(get_auth_context)):
    """Delete a custom skill from the user's custom skills directory."""
    custom_dir = _get_user_custom_skills_dir(auth.user_id)
    skill_dir = custom_dir / skill_name

    if not skill_dir.exists():
        raise HTTPException(status_code=404, detail=f"Custom skill '{skill_name}' not found")

    # Safety: ensure the resolved path is still under custom_dir
    if not skill_dir.resolve().is_relative_to(custom_dir.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        shutil.rmtree(skill_dir)
        logger.info("Skill '%s' deleted for user %s", skill_name, auth.user_id)
        return {"success": True, "message": f"Skill '{skill_name}' deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete skill '{skill_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete skill: {str(e)}")


@router.post(
    "/skills/install",
    response_model=SkillInstallResponse,
    summary="Install Skill",
    description="Install a skill from a .skill file (ZIP archive) located in the thread's user-data directory.",
)
async def install_skill(request: SkillInstallRequest, auth: AuthContext = Depends(get_auth_context)) -> SkillInstallResponse:
    """Install a skill from a .skill file.

    The .skill file is a ZIP archive containing a skill directory with SKILL.md
    and optional resources (scripts, references, assets).

    Args:
        request: The install request containing thread_id and virtual path to .skill file.

    Returns:
        Installation result with skill name and status message.

    Raises:
        HTTPException:
            - 400 if path is invalid or file is not a valid .skill file
            - 403 if access denied (path traversal detected)
            - 404 if file not found
            - 409 if skill already exists
            - 500 if installation fails

    Example Request:
        ```json
        {
            "thread_id": "abc123-def456",
            "path": "/mnt/user-data/outputs/my-skill.skill"
        }
        ```

    Example Response:
        ```json
        {
            "success": true,
            "skill_name": "my-skill",
            "message": "Skill 'my-skill' installed successfully"
        }
        ```
    """
    try:
        skill_file_path = resolve_thread_virtual_path(request.thread_id, request.path)

        if not skill_file_path.exists():
            raise HTTPException(status_code=404, detail=f"Skill file not found: {request.path}")
        if not skill_file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {request.path}")
        if skill_file_path.suffix != ".skill":
            raise HTTPException(status_code=400, detail="File must have .skill extension")

        custom_dir = _get_user_custom_skills_dir(auth.user_id)
        skill_name, message = _install_skill_from_zip(skill_file_path, custom_dir, overwrite=True)

        logger.info("Skill '%s' installed for user %s", skill_name, auth.user_id)
        return SkillInstallResponse(success=True, skill_name=skill_name, message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to install skill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to install skill: {str(e)}")


@router.post(
    "/skills/upload",
    response_model=SkillInstallResponse,
    summary="Upload and Install Skill",
    description="Upload a .zip or .skill file and install it to the user's custom skills directory.",
)
async def upload_skill(
    file: UploadFile = File(..., description="ZIP or .skill archive containing SKILL.md"),
    auth: AuthContext = Depends(get_auth_context),
) -> SkillInstallResponse:
    """Upload and install a skill from a ZIP archive.

    The archive must contain a SKILL.md with valid frontmatter (name, description).
    Supported formats: .zip, .skill. Max size: 50MB.
    """
    filename = file.filename or ""
    if not filename.lower().endswith((".zip", ".skill")):
        raise HTTPException(status_code=400, detail="File must be .zip or .skill format")

    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            content = await file.read()
            if len(content) > 50 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large (max 50MB)")
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            custom_dir = _get_user_custom_skills_dir(auth.user_id)
            skill_name, message = _install_skill_from_zip(tmp_path, custom_dir, overwrite=True)
            logger.info("Skill '%s' uploaded and installed for user %s", skill_name, auth.user_id)
            return SkillInstallResponse(success=True, skill_name=skill_name, message=message)
        finally:
            tmp_path.unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload skill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload skill: {str(e)}")
