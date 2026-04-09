from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.gateway.db.models import UsageRecord
from deerflow.stores import UsageRecordStore


class PostgresUsageRecordStore(UsageRecordStore):
    """Persist runtime LLM token usage to gateway usage_records."""

    def __init__(self, async_session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._async_session_factory = async_session_factory

    async def record_llm_token(
        self,
        *,
        user_id: str,
        org_id: str,
        model_name: str | None,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        async with self._async_session_factory() as session:
            session.add(
                UsageRecord(
                    org_id=org_id,
                    user_id=user_id,
                    record_type="llm_token",
                    model_name=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
            await session.commit()
