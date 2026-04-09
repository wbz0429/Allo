"""Platform and enterprise administration API."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context, is_platform_admin
from app.gateway.db.database import get_db_session
from app.gateway.db.models import Organization, OrganizationMember, UsageRecord, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Response / Request models
# ---------------------------------------------------------------------------


class OrgResponse(BaseModel):
    """Organization summary with member count."""

    id: str
    name: str
    slug: str
    member_count: int
    created_at: str


class MemberResponse(BaseModel):
    """Organization member."""

    id: str
    user_id: str
    role: str
    created_at: str


class AddMemberRequest(BaseModel):
    """Request body for adding a member to an organization."""

    user_id: str
    role: str = "member"


class UsageStatsResponse(BaseModel):
    """Aggregated usage statistics."""

    total_api_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_sandbox_seconds: float
    total_usage_records: int


class UserUsageItemResponse(BaseModel):
    """Platform-wide per-user usage aggregate."""

    user_id: str
    display_name: str | None
    email: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    api_calls: int


class UserUsageRankingResponse(BaseModel):
    """Ranked platform-wide usage by user."""

    metric: str
    items: list[UserUsageItemResponse]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_org_admin(auth: AuthContext) -> None:
    """Raise 403 if the authenticated user is not an org admin."""
    if auth.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def _require_platform_admin(auth: AuthContext) -> None:
    """Raise 403 if the authenticated user is not a platform admin."""
    if not is_platform_admin(auth):
        raise HTTPException(status_code=403, detail="Platform admin access required")


# ---------------------------------------------------------------------------
# Platform admin endpoints (require role == "admin")
# ---------------------------------------------------------------------------


@router.get("/organizations", response_model=list[OrgResponse], summary="List All Organizations")
async def list_organizations(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[OrgResponse]:
    """List all organizations (platform admin only)."""
    logger.info("Admin: list_organizations start user_id=%s org_id=%s role=%s", auth.user_id, auth.org_id, auth.role)
    _require_platform_admin(auth)

    stmt = select(Organization).order_by(Organization.created_at.desc())
    result = await db.execute(stmt)
    orgs = result.scalars().all()

    responses: list[OrgResponse] = []
    for org in orgs:
        count_stmt = select(func.count()).select_from(OrganizationMember).where(OrganizationMember.org_id == org.id)
        count_result = await db.execute(count_stmt)
        member_count = count_result.scalar_one()
        responses.append(
            OrgResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                member_count=member_count,
                created_at=org.created_at.isoformat() if org.created_at else "",
            )
        )
    logger.info("Admin: list_organizations success count=%s", len(responses))
    return responses


@router.get("/organizations/{org_id}", response_model=OrgResponse, summary="Get Organization Details")
async def get_organization(
    org_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> OrgResponse:
    """Get organization details with member count (platform admin only)."""
    _require_platform_admin(auth)

    stmt = select(Organization).where(Organization.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    count_stmt = select(func.count()).select_from(OrganizationMember).where(OrganizationMember.org_id == org.id)
    count_result = await db.execute(count_stmt)
    member_count = count_result.scalar_one()

    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        member_count=member_count,
        created_at=org.created_at.isoformat() if org.created_at else "",
    )


@router.get("/usage", response_model=UsageStatsResponse, summary="Get Platform Usage Stats")
async def get_platform_usage(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> UsageStatsResponse:
    """Get aggregated usage stats across all organizations (platform admin only)."""
    logger.info("Admin: get_platform_usage start user_id=%s org_id=%s role=%s", auth.user_id, auth.org_id, auth.role)
    _require_platform_admin(auth)

    stmt = select(
        func.count().label("total_usage_records"),
        func.coalesce(func.sum(case((UsageRecord.record_type == "api_call", 1), else_=0)), 0).label("total_api_calls"),
        func.coalesce(func.sum(case((UsageRecord.record_type == "llm_token", UsageRecord.input_tokens), else_=0)), 0).label("total_input_tokens"),
        func.coalesce(func.sum(case((UsageRecord.record_type == "llm_token", UsageRecord.output_tokens), else_=0)), 0).label("total_output_tokens"),
        func.coalesce(func.sum(case((UsageRecord.record_type == "sandbox_time", UsageRecord.duration_seconds), else_=0.0)), 0.0).label("total_sandbox_seconds"),
    ).select_from(UsageRecord)
    result = await db.execute(stmt)
    row = result.one()

    logger.info(
        "Admin: get_platform_usage success total_usage_records=%s api_calls=%s input=%s output=%s sandbox=%s",
        row.total_usage_records,
        row.total_api_calls,
        row.total_input_tokens,
        row.total_output_tokens,
        row.total_sandbox_seconds,
    )
    return UsageStatsResponse(
        total_api_calls=int(row.total_api_calls),
        total_input_tokens=int(row.total_input_tokens),
        total_output_tokens=int(row.total_output_tokens),
        total_sandbox_seconds=float(row.total_sandbox_seconds),
        total_usage_records=int(row.total_usage_records),
    )


# ---------------------------------------------------------------------------
# Enterprise admin endpoints (scoped to auth.org_id)
# ---------------------------------------------------------------------------


@router.get("/org/members", response_model=list[MemberResponse], summary="List Org Members")
async def list_org_members(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[MemberResponse]:
    """List members of the authenticated organization."""
    stmt = select(OrganizationMember).where(OrganizationMember.org_id == auth.org_id).order_by(OrganizationMember.created_at.desc())
    result = await db.execute(stmt)
    members = result.scalars().all()

    return [
        MemberResponse(
            id=m.id,
            user_id=m.user_id,
            role=m.role,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in members
    ]


@router.post("/org/members", response_model=MemberResponse, status_code=201, summary="Add Org Member")
async def add_org_member(
    request: AddMemberRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MemberResponse:
    """Add a member to the authenticated organization (admin only)."""
    _require_org_admin(auth)

    member = OrganizationMember(org_id=auth.org_id, user_id=request.user_id, role=request.role)
    db.add(member)
    await db.commit()
    await db.refresh(member)

    logger.info(f"Added member user_id={request.user_id} to org={auth.org_id}")
    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        created_at=member.created_at.isoformat() if member.created_at else "",
    )


@router.delete("/org/members/{member_id}", status_code=204, summary="Remove Org Member")
async def remove_org_member(
    member_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove a member from the authenticated organization (admin only)."""
    _require_org_admin(auth)

    stmt = select(OrganizationMember).where(OrganizationMember.id == member_id, OrganizationMember.org_id == auth.org_id)
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(member)
    await db.commit()
    logger.info(f"Removed member id={member_id} from org={auth.org_id}")


@router.get("/usage/users", response_model=UserUsageRankingResponse, summary="Get Platform Usage By User")
async def get_platform_usage_users(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    metric: str = Query(default="total_tokens"),
) -> UserUsageRankingResponse:
    """Get platform-wide usage ranking grouped by user."""
    _require_platform_admin(auth)

    input_tokens_expr = func.coalesce(func.sum(case((UsageRecord.record_type == "llm_token", UsageRecord.input_tokens), else_=0)), 0)
    output_tokens_expr = func.coalesce(func.sum(case((UsageRecord.record_type == "llm_token", UsageRecord.output_tokens), else_=0)), 0)
    api_calls_expr = func.coalesce(func.sum(case((UsageRecord.record_type == "api_call", 1), else_=0)), 0)
    total_tokens_expr = input_tokens_expr + output_tokens_expr

    sort_options = {
        "total_tokens": total_tokens_expr,
        "api_calls": api_calls_expr,
        "input_tokens": input_tokens_expr,
        "output_tokens": output_tokens_expr,
    }
    sort_expr = sort_options.get(metric)
    if sort_expr is None:
        raise HTTPException(status_code=422, detail="Unsupported ranking metric")

    stmt = (
        select(
            UsageRecord.user_id,
            User.display_name,
            User.email,
            input_tokens_expr.label("input_tokens"),
            output_tokens_expr.label("output_tokens"),
            total_tokens_expr.label("total_tokens"),
            api_calls_expr.label("api_calls"),
        )
        .join(User, User.id == UsageRecord.user_id)
        .group_by(UsageRecord.user_id, User.display_name, User.email)
        .order_by(sort_expr.desc(), UsageRecord.user_id.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return UserUsageRankingResponse(
        metric=metric,
        items=[
            UserUsageItemResponse(
                user_id=row.user_id,
                display_name=row.display_name,
                email=row.email,
                input_tokens=int(row.input_tokens),
                output_tokens=int(row.output_tokens),
                total_tokens=int(row.total_tokens),
                api_calls=int(row.api_calls),
            )
            for row in rows
        ],
    )


@router.get("/org/usage", response_model=UsageStatsResponse, summary="Get Org Usage Stats")
async def get_org_usage(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> UsageStatsResponse:
    """Get usage stats for the authenticated organization."""
    stmt = (
        select(
            func.count().label("total_usage_records"),
            func.coalesce(func.sum(case((UsageRecord.record_type == "api_call", 1), else_=0)), 0).label("total_api_calls"),
            func.coalesce(func.sum(case((UsageRecord.record_type == "llm_token", UsageRecord.input_tokens), else_=0)), 0).label("total_input_tokens"),
            func.coalesce(func.sum(case((UsageRecord.record_type == "llm_token", UsageRecord.output_tokens), else_=0)), 0).label("total_output_tokens"),
            func.coalesce(func.sum(case((UsageRecord.record_type == "sandbox_time", UsageRecord.duration_seconds), else_=0.0)), 0.0).label("total_sandbox_seconds"),
        )
        .select_from(UsageRecord)
        .where(UsageRecord.org_id == auth.org_id)
    )
    result = await db.execute(stmt)
    row = result.one()

    return UsageStatsResponse(
        total_api_calls=int(row.total_api_calls),
        total_input_tokens=int(row.total_input_tokens),
        total_output_tokens=int(row.total_output_tokens),
        total_sandbox_seconds=float(row.total_sandbox_seconds),
        total_usage_records=int(row.total_usage_records),
    )
