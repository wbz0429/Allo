"""Idempotent local development account seed.

Creates a stable dev@allo.local user with fixed IDs so that install
records, threads, memory, and other per-user data survive restarts.
Only runs when ALLO_ENV != 'production'.
"""

import logging

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.gateway.db.models import MarketplaceSkill, Organization, OrganizationMember, OrgInstalledSkill, User

logger = logging.getLogger(__name__)

# Fixed IDs — never change these.
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
DEV_ORG_ID = "00000000-0000-0000-0000-000000000001"
DEV_EMAIL = "dev@allo.local"
DEV_PASSWORD = "Password123!"
DEV_DISPLAY_NAME = "Local Dev"


async def _ensure_dev_marketplace_installs(db: AsyncSession) -> None:
    """Auto-install all marketplace skills for the dev org."""
    result = await db.execute(select(MarketplaceSkill.id))
    all_skill_ids = [row[0] for row in result.all()]

    existing = await db.execute(
        select(OrgInstalledSkill.skill_id).where(OrgInstalledSkill.org_id == DEV_ORG_ID)
    )
    already_installed = {row[0] for row in existing.all()}

    added = 0
    for skill_id in all_skill_ids:
        if skill_id not in already_installed:
            db.add(OrgInstalledSkill(org_id=DEV_ORG_ID, skill_id=skill_id))
            added += 1

    if added:
        await db.flush()
        logger.info("Auto-installed %d marketplace skills for dev org", added)


async def ensure_dev_account(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Create or verify the local dev account with fixed IDs."""
    async with session_factory() as db:
        # Check by both ID and email to handle stale data
        existing_by_id = await db.execute(select(User).where(User.id == DEV_USER_ID).limit(1))
        if existing_by_id.scalar_one_or_none() is not None:
            # Account exists — just ensure marketplace installs are up to date
            await _ensure_dev_marketplace_installs(db)
            await db.commit()
            logger.info("Dev account already exists (user_id=%s)", DEV_USER_ID)
            return

        # If email exists with a different ID, migrate it to the fixed ID
        existing_by_email = await db.execute(select(User).where(User.email == DEV_EMAIL).limit(1))
        old_user = existing_by_email.scalar_one_or_none()
        if old_user is not None:
            old_id = old_user.id
            logger.warning("Dev email %s exists with wrong id=%s, migrating to fixed id=%s", DEV_EMAIL, old_id, DEV_USER_ID)
            from sqlalchemy import delete as sa_delete
            await db.execute(sa_delete(OrganizationMember).where(OrganizationMember.user_id == old_id))
            await db.execute(sa_delete(User).where(User.id == old_id))
            await db.flush()

        password_hash = bcrypt.hashpw(DEV_PASSWORD.encode(), bcrypt.gensalt()).decode()

        user = User(id=DEV_USER_ID, email=DEV_EMAIL, password_hash=password_hash, display_name=DEV_DISPLAY_NAME)

        # Ensure fixed org exists
        existing_org = await db.execute(select(Organization).where(Organization.id == DEV_ORG_ID).limit(1))
        if existing_org.scalar_one_or_none() is None:
            org = Organization(id=DEV_ORG_ID, name=f"{DEV_DISPLAY_NAME}'s Organization", slug="local-dev")
            db.add(org)

        membership = OrganizationMember(user_id=DEV_USER_ID, org_id=DEV_ORG_ID, role="admin")

        db.add(user)
        db.add(membership)

        # Auto-install all marketplace skills for dev org
        await _ensure_dev_marketplace_installs(db)

        try:
            await db.commit()
            logger.info("Created dev account: email=%s user_id=%s org_id=%s", DEV_EMAIL, DEV_USER_ID, DEV_ORG_ID)
        except Exception as exc:
            await db.rollback()
            logger.error("Failed to create dev account: %s", exc, exc_info=True)
