"""Seed or reset a deterministic local development auth user.

Usage:
    PYTHONPATH=. uv run python dev_seed_auth_user.py
"""

import asyncio
import uuid

import bcrypt
from sqlalchemy import delete, select

from app.gateway.db.database import async_session_factory
from app.gateway.db.models import Organization, OrganizationMember, Session, User

DEV_EMAIL = "dev@allo.local"
DEV_PASSWORD = "Password123!"
DEV_NAME = "Local Dev"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def main() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == DEV_EMAIL).limit(1))
        existing_user = result.scalar_one_or_none()

        if existing_user is not None:
            await db.execute(delete(Session).where(Session.user_id == existing_user.id))
            await db.execute(delete(OrganizationMember).where(OrganizationMember.user_id == existing_user.id))
            await db.execute(delete(User).where(User.id == existing_user.id))
            await db.commit()

        user = User(email=DEV_EMAIL, password_hash=_hash_password(DEV_PASSWORD), display_name=DEV_NAME)
        organization = Organization(name=f"{DEV_NAME}'s Organization", slug=f"local-dev-{uuid.uuid4().hex[:12]}")
        membership = OrganizationMember(user_id=user.id, org_id=organization.id, role="admin")

        db.add(user)
        db.add(organization)
        db.add(membership)
        await db.commit()

        print("Seeded local auth user:")
        print(f"  email: {DEV_EMAIL}")
        print(f"  password: {DEV_PASSWORD}")
        print(f"  user_id: {user.id}")
        print(f"  org_id: {organization.id}")


if __name__ == "__main__":
    asyncio.run(main())
