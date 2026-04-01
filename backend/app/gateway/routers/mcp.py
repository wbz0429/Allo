import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import UserMcpConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])


class McpOAuthConfigResponse(BaseModel):
    enabled: bool = Field(default=True)
    token_url: str = Field(default="")
    grant_type: str = Field(default="client_credentials")
    client_id: str | None = Field(default=None)
    client_secret: str | None = Field(default=None)
    refresh_token: str | None = Field(default=None)
    scope: str | None = Field(default=None)
    audience: str | None = Field(default=None)
    token_field: str = Field(default="access_token")
    token_type_field: str = Field(default="token_type")
    expires_in_field: str = Field(default="expires_in")
    default_token_type: str = Field(default="Bearer")
    refresh_skew_seconds: int = Field(default=60)
    extra_token_params: dict[str, str] = Field(default_factory=dict)


class McpServerConfigResponse(BaseModel):
    enabled: bool = Field(default=True)
    type: str = Field(default="stdio")
    command: str | None = Field(default=None)
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = Field(default=None)
    headers: dict[str, str] = Field(default_factory=dict)
    oauth: McpOAuthConfigResponse | None = Field(default=None)
    description: str = Field(default="")


class McpConfigResponse(BaseModel):
    mcp_servers: dict[str, McpServerConfigResponse] = Field(default_factory=dict)


class McpConfigUpdateRequest(BaseModel):
    mcp_servers: dict[str, McpServerConfigResponse] = Field(default_factory=dict)


def _normalize_response(config_dict: dict) -> McpConfigResponse:
    servers = config_dict.get("mcp_servers", {}) if isinstance(config_dict, dict) else {}
    return McpConfigResponse(
        mcp_servers={name: McpServerConfigResponse(**server) for name, server in servers.items()},
    )


@router.get("/mcp/config", response_model=McpConfigResponse)
async def get_mcp_configuration(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> McpConfigResponse:
    result = await db.execute(select(UserMcpConfig).where(UserMcpConfig.user_id == auth.user_id, UserMcpConfig.org_id == auth.org_id).order_by(UserMcpConfig.updated_at.desc()).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        return McpConfigResponse(mcp_servers={})

    try:
        return _normalize_response(json.loads(config.config_json))
    except json.JSONDecodeError:
        logger.warning("Invalid MCP config JSON for user_id=%s", auth.user_id)
        return McpConfigResponse(mcp_servers={})


@router.put("/mcp/config", response_model=McpConfigResponse)
async def update_mcp_configuration(
    request: McpConfigUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> McpConfigResponse:
    result = await db.execute(select(UserMcpConfig).where(UserMcpConfig.user_id == auth.user_id, UserMcpConfig.org_id == auth.org_id).order_by(UserMcpConfig.updated_at.desc()).limit(1))
    record = result.scalar_one_or_none()

    payload = {
        "mcp_servers": {name: server.model_dump() for name, server in request.mcp_servers.items()},
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    if record is None:
        record = UserMcpConfig(user_id=auth.user_id, org_id=auth.org_id, config_json=payload_json)
        db.add(record)
    else:
        record.config_json = payload_json

    await db.commit()
    await db.refresh(record)
    logger.info("Updated MCP configuration for user_id=%s org_id=%s", auth.user_id, auth.org_id)
    return _normalize_response(payload)
