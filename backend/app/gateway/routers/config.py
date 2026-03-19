"""Tenant configuration API — per-org config overrides merged with base YAML."""

import json
import logging

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import TenantConfig
from deerflow.config.app_config import get_app_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class TenantConfigOverrides(BaseModel):
    """JSON structure stored in TenantConfig.config_json."""

    default_model: str | None = Field(default=None, description="Default model name for this tenant")
    enabled_models: list[str] | None = Field(default=None, description="Subset of models enabled for this tenant")
    enabled_tool_groups: list[str] | None = Field(default=None, description="Subset of tool groups enabled for this tenant")
    custom_settings: dict | None = Field(default=None, description="Arbitrary tenant-specific settings")


class MergedConfigResponse(BaseModel):
    """GET /api/config response — base config merged with tenant overrides."""

    models: list[dict] = Field(default_factory=list, description="Available models (filtered by tenant if overrides exist)")
    tool_groups: list[dict] = Field(default_factory=list, description="Available tool groups (filtered by tenant if overrides exist)")
    default_model: str | None = Field(default=None, description="Tenant's default model (or first model from base)")
    overrides: TenantConfigOverrides = Field(default_factory=TenantConfigOverrides, description="Raw tenant overrides")


class ModelConfigUpdate(BaseModel):
    """PUT /api/config/models request body."""

    default_model: str | None = Field(default=None, description="Default model name")
    enabled_models: list[str] | None = Field(default=None, description="List of enabled model names")


class ToolConfigUpdate(BaseModel):
    """PUT /api/config/tools request body."""

    enabled_tool_groups: list[str] | None = Field(default=None, description="List of enabled tool group names")


class ConfigImportRequest(BaseModel):
    """POST /api/config/import request body."""

    content: str = Field(..., description="YAML or JSON string to import as tenant overrides")
    format: str = Field(default="auto", description="'yaml', 'json', or 'auto' (detect)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_or_create_tenant_config(org_id: str, db: AsyncSession) -> TenantConfig:
    """Fetch the TenantConfig row for an org, creating one if it doesn't exist."""
    result = await db.execute(select(TenantConfig).where(TenantConfig.org_id == org_id))
    tenant_cfg = result.scalar_one_or_none()
    if tenant_cfg is None:
        tenant_cfg = TenantConfig(org_id=org_id, config_json="{}")
        db.add(tenant_cfg)
        await db.commit()
        await db.refresh(tenant_cfg)
    return tenant_cfg


def _parse_overrides(config_json: str) -> TenantConfigOverrides:
    """Parse the config_json string into a TenantConfigOverrides model."""
    try:
        data = json.loads(config_json) if config_json else {}
    except json.JSONDecodeError:
        data = {}
    return TenantConfigOverrides(**data)


def _merge_config(overrides: TenantConfigOverrides) -> MergedConfigResponse:
    """Merge base YAML config with tenant overrides.

    Args:
        overrides: Tenant-specific config overrides.

    Returns:
        MergedConfigResponse with filtered models/tool_groups and default_model.
    """
    app_cfg = get_app_config()

    # Base models as dicts
    all_models = [{"name": m.name, "display_name": m.display_name, "description": m.description} for m in app_cfg.models]

    # Base tool groups as dicts
    all_tool_groups = [{"name": tg.name} for tg in app_cfg.tool_groups]

    # Filter models if tenant has enabled_models override
    if overrides.enabled_models is not None:
        enabled_set = set(overrides.enabled_models)
        models = [m for m in all_models if m["name"] in enabled_set]
    else:
        models = all_models

    # Filter tool groups if tenant has enabled_tool_groups override
    if overrides.enabled_tool_groups is not None:
        enabled_tg_set = set(overrides.enabled_tool_groups)
        tool_groups = [tg for tg in all_tool_groups if tg["name"] in enabled_tg_set]
    else:
        tool_groups = all_tool_groups

    # Resolve default model
    default_model = overrides.default_model
    if default_model is None and models:
        default_model = models[0]["name"]

    return MergedConfigResponse(
        models=models,
        tool_groups=tool_groups,
        default_model=default_model,
        overrides=overrides,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=MergedConfigResponse,
    summary="Get Tenant Config",
    description="Get the current tenant config (base YAML merged with tenant overrides).",
)
async def get_config(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MergedConfigResponse:
    """Return merged config for the authenticated tenant."""
    tenant_cfg = await _get_or_create_tenant_config(auth.org_id, db)
    overrides = _parse_overrides(tenant_cfg.config_json)
    return _merge_config(overrides)


@router.put(
    "",
    response_model=MergedConfigResponse,
    summary="Update Tenant Config",
    description="Update tenant config overrides (partial update — only provided fields are changed).",
)
async def update_config(
    request: TenantConfigOverrides,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MergedConfigResponse:
    """Update tenant config overrides and return the merged result."""
    tenant_cfg = await _get_or_create_tenant_config(auth.org_id, db)

    # Merge with existing overrides (partial update)
    existing = _parse_overrides(tenant_cfg.config_json)
    update_data = request.model_dump(exclude_none=True)
    merged_data = existing.model_dump()
    merged_data.update(update_data)

    tenant_cfg.config_json = json.dumps(merged_data, ensure_ascii=False)
    await db.commit()
    await db.refresh(tenant_cfg)

    overrides = _parse_overrides(tenant_cfg.config_json)
    return _merge_config(overrides)


@router.post(
    "/import",
    response_model=MergedConfigResponse,
    summary="Import Config",
    description="Import YAML or JSON config as tenant overrides (replaces existing overrides).",
)
async def import_config(
    request: ConfigImportRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MergedConfigResponse:
    """Import config from YAML or JSON string, replacing tenant overrides."""
    content = request.content.strip()
    fmt = request.format.lower()

    # Auto-detect format
    if fmt == "auto":
        if content.startswith("{"):
            fmt = "json"
        else:
            fmt = "yaml"

    try:
        if fmt == "json":
            data = json.loads(content)
        elif fmt == "yaml":
            data = yaml.safe_load(content) or {}
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported format: {fmt}. Use 'yaml', 'json', or 'auto'.")
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse config: {e}")

    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Config must be a JSON/YAML object (dict)")

    # Validate by constructing overrides
    overrides = TenantConfigOverrides(**{k: v for k, v in data.items() if k in TenantConfigOverrides.model_fields})

    tenant_cfg = await _get_or_create_tenant_config(auth.org_id, db)
    tenant_cfg.config_json = json.dumps(overrides.model_dump(exclude_none=True), ensure_ascii=False)
    await db.commit()
    await db.refresh(tenant_cfg)

    return _merge_config(overrides)


@router.get(
    "/export",
    summary="Export Config",
    description="Export the current tenant config overrides as YAML.",
)
async def export_config(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> str:
    """Export tenant config overrides as a YAML string."""
    tenant_cfg = await _get_or_create_tenant_config(auth.org_id, db)
    overrides = _parse_overrides(tenant_cfg.config_json)
    data = overrides.model_dump(exclude_none=True)
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


@router.get(
    "/models",
    summary="List Available Models",
    description="List all models from the base config.",
)
async def list_models(auth: AuthContext = Depends(get_auth_context)) -> dict:
    """Return all models defined in the base YAML config."""
    app_cfg = get_app_config()
    models = [{"name": m.name, "display_name": m.display_name, "description": m.description} for m in app_cfg.models]
    return {"models": models}


@router.put(
    "/models",
    response_model=MergedConfigResponse,
    summary="Set Tenant Model Config",
    description="Set the tenant's default model and enabled models.",
)
async def update_model_config(
    request: ModelConfigUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MergedConfigResponse:
    """Update the tenant's model configuration."""
    tenant_cfg = await _get_or_create_tenant_config(auth.org_id, db)
    existing = _parse_overrides(tenant_cfg.config_json)
    merged_data = existing.model_dump()

    if request.default_model is not None:
        merged_data["default_model"] = request.default_model
    if request.enabled_models is not None:
        merged_data["enabled_models"] = request.enabled_models

    tenant_cfg.config_json = json.dumps(merged_data, ensure_ascii=False)
    await db.commit()
    await db.refresh(tenant_cfg)

    overrides = _parse_overrides(tenant_cfg.config_json)
    return _merge_config(overrides)


@router.get(
    "/tools",
    summary="List Available Tool Groups",
    description="List all tool groups from the base config.",
)
async def list_tools(auth: AuthContext = Depends(get_auth_context)) -> dict:
    """Return all tool groups defined in the base YAML config."""
    app_cfg = get_app_config()
    tool_groups = [{"name": tg.name} for tg in app_cfg.tool_groups]
    return {"tool_groups": tool_groups}


@router.put(
    "/tools",
    response_model=MergedConfigResponse,
    summary="Set Tenant Tool Config",
    description="Set the tenant's enabled tool groups.",
)
async def update_tool_config(
    request: ToolConfigUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MergedConfigResponse:
    """Update the tenant's tool group configuration."""
    tenant_cfg = await _get_or_create_tenant_config(auth.org_id, db)
    existing = _parse_overrides(tenant_cfg.config_json)
    merged_data = existing.model_dump()

    if request.enabled_tool_groups is not None:
        merged_data["enabled_tool_groups"] = request.enabled_tool_groups

    tenant_cfg.config_json = json.dumps(merged_data, ensure_ascii=False)
    await db.commit()
    await db.refresh(tenant_cfg)

    overrides = _parse_overrides(tenant_cfg.config_json)
    return _merge_config(overrides)
