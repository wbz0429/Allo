"""Idempotent local development account seed.

Creates a stable dev@allo.local user with fixed IDs so that install
records, threads, memory, and other per-user data survive restarts.
Only runs when ALLO_ENV != 'production'.
"""

import logging

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.gateway.db.models import Organization, OrganizationMember, User

logger = logging.getLogger(__name__)

# Fixed IDs — never change these.
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
DEV_ORG_ID = "00000000-0000-0000-0000-000000000001"
DEV_EMAIL = "dev@allo.local"
DEV_PASSWORD = "Password123!"
DEV_DISPLAY_NAME = "Local Dev"


async def ensure_dev_account(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Create or verify the local dev account with fixed IDs."""
    async with session_factory() as db:
        existing = await db.execute(select(User).where(User.id == DEV_USER_ID).limit(1))
        if existing.scalar_one_or_none() is not None:
            logger.info("Dev account already exists (user_id=%s)", DEV_USER_ID)
            return

        password_hash = bcrypt.hashpw(DEV_PASSWORD.encode(), bcrypt.gensalt()).decode()

        user = User(id=DEV_USER_ID, email=DEV_EMAIL, password_hash=password_hash, display_name=DEV_DISPLAY_NAME)
        org = Organization(id=DEV_ORG_ID, name=f"{DEV_DISPLAY_NAME}'s Organization", slug="local-dev")
        membership = OrganizationMember(user_id=DEV_USER_ID, org_id=DEV_ORG_ID, role="admin")

        db.add(user)
        db.add(org)
        db.add(membership)

        try:
            await db.commit()
            logger.info("Created dev account: email=%s user_id=%s org_id=%s", DEV_EMAIL, DEV_USER_ID, DEV_ORG_ID)
        except Exception:
            await db.rollback()
            logger.info("Dev account already exists (race condition), skipping")
