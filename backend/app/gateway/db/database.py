"""Async database engine and session factory for the Allo gateway."""

import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)
_root_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_root_env_path)

DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql+asyncpg://{os.getenv('USER', 'wbz')}@localhost:5432/deerflow")


def _mask_database_url(url: str) -> str:
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return f"{scheme}://{rest}"
    creds, host = rest.split("@", 1)
    if ":" in creds:
        user, _password = creds.split(":", 1)
        creds = f"{user}:***"
    return f"{scheme}://{creds}@{host}"


logger.info(
    "Gateway DB init env_path=%s exists=%s cwd=%s database_url=%s",
    _root_env_path,
    _root_env_path.exists(),
    Path.cwd(),
    _mask_database_url(DATABASE_URL),
)

async_engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

async_session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Yields:
        An async SQLAlchemy session that is automatically closed after use.
    """
    async with async_session_factory() as session:
        yield session
