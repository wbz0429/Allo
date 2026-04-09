from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.gateway.db.models import Base, UsageRecord
from app.gateway.services.usage_record_store_pg import PostgresUsageRecordStore

_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _setup_db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_record_llm_token_persists_usage_record() -> None:
    store = PostgresUsageRecordStore(_test_session_factory)

    await store.record_llm_token(
        user_id="user-1",
        org_id="org-1",
        model_name="gpt-4o",
        input_tokens=123,
        output_tokens=45,
    )

    async with _test_session_factory() as session:
        result = await session.execute(select(UsageRecord))
        records = result.scalars().all()

    assert len(records) == 1
    record = records[0]
    assert record.user_id == "user-1"
    assert record.org_id == "org-1"
    assert record.record_type == "llm_token"
    assert record.model_name == "gpt-4o"
    assert record.input_tokens == 123
    assert record.output_tokens == 45
