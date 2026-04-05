"""Thread CRUD and run tracking APIs.

Response shapes are compatible with the LangGraph SDK ``Thread`` type so the
frontend can consume them directly via ``AgentThread`` (which extends
``Thread<AgentThreadState>``).
"""

import logging
import os
import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import Thread, ThreadRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/threads", tags=["threads"])

LANGGRAPH_URL = os.getenv("LANGGRAPH_INTERNAL_URL", "http://127.0.0.1:2024")
LANGGRAPH_THREAD_SYNC_RETRIES = 3


async def _sync_langgraph_thread(thread_id: str) -> None:
    last_error: Exception | None = None

    for attempt in range(1, LANGGRAPH_THREAD_SYNC_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{LANGGRAPH_URL}/threads", json={"thread_id": thread_id})
                response.raise_for_status()
                return
        except Exception as error:
            last_error = error
            logger.warning(
                "LangGraph thread sync failed: thread_id=%s attempt=%s/%s error_type=%s error=%r",
                thread_id,
                attempt,
                LANGGRAPH_THREAD_SYNC_RETRIES,
                type(error).__name__,
                error,
            )
            if attempt < LANGGRAPH_THREAD_SYNC_RETRIES:
                await asyncio.sleep(0.25 * attempt)

    logger.warning(
        "Failed to sync thread %s to LangGraph checkpointer after %s attempts: %r",
        thread_id,
        LANGGRAPH_THREAD_SYNC_RETRIES,
        last_error,
    )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ThreadCreateRequest(BaseModel):
    thread_id: str = Field(..., min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=500)
    agent_name: str | None = Field(default=None, max_length=100)
    default_model: str | None = Field(default=None, max_length=100)
    last_model_name: str | None = Field(default=None, max_length=100)
    status: str = Field(default="active", min_length=1, max_length=20)


class ThreadUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    agent_name: str | None = Field(default=None, max_length=100)
    default_model: str | None = Field(default=None, max_length=100)
    last_model_name: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, min_length=1, max_length=20)
    last_active_at: datetime | None = None


class ThreadRunCreateRequest(BaseModel):
    id: str | None = Field(default=None, max_length=36)
    model_name: str | None = Field(default=None, max_length=100)
    agent_name: str | None = Field(default=None, max_length=100)
    sandbox_id: str | None = Field(default=None, max_length=100)
    status: str = Field(default="running", min_length=1, max_length=20)


class ThreadRunUpdateRequest(BaseModel):
    status: str | None = Field(default=None, min_length=1, max_length=20)
    sandbox_id: str | None = Field(default=None, max_length=100)
    error_message: str | None = None
    finished_at: datetime | None = None


# ---------------------------------------------------------------------------
# Response models — LangGraph SDK ``Thread`` compatible
# ---------------------------------------------------------------------------


class ThreadRunResponse(BaseModel):
    id: str
    thread_id: str
    user_id: str
    org_id: str
    model_name: str | None
    agent_name: str | None
    sandbox_id: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None


class ThreadResponse(BaseModel):
    """Matches the LangGraph SDK ``Thread<AgentThreadState>`` shape.

    The frontend ``AgentThread`` type extends ``Thread`` which requires:
    ``thread_id``, ``created_at``, ``updated_at``, ``metadata``, ``status``,
    ``values``, ``interrupts``.
    """

    thread_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any]
    status: str
    values: dict[str, Any]
    interrupts: dict[str, Any]


# ---------------------------------------------------------------------------
# Status mapping — our DB uses "active"/"archived", SDK uses "idle"/"busy"/…
# ---------------------------------------------------------------------------

_STATUS_TO_SDK: dict[str, str] = {
    "active": "idle",
    "running": "busy",
    "error": "error",
    "interrupted": "interrupted",
}


def _map_status(db_status: str) -> str:
    return _STATUS_TO_SDK.get(db_status, "idle")


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------


def _thread_to_response(thread: Thread) -> ThreadResponse:
    return ThreadResponse(
        thread_id=thread.id,
        created_at=thread.created_at.isoformat() if thread.created_at else "",
        updated_at=thread.updated_at.isoformat() if thread.updated_at else "",
        metadata={
            "agent_name": thread.agent_name,
            "default_model": thread.default_model,
            "last_model_name": thread.last_model_name,
            "last_active_at": thread.last_active_at.isoformat() if thread.last_active_at else None,
            "user_id": thread.user_id,
            "org_id": thread.org_id,
        },
        status=_map_status(thread.status),
        values={
            "title": thread.title or "",
        },
        interrupts={},
    )


def _thread_run_to_response(run: ThreadRun) -> ThreadRunResponse:
    return ThreadRunResponse(
        id=run.id,
        thread_id=run.thread_id,
        user_id=run.user_id,
        org_id=run.org_id,
        model_name=run.model_name,
        agent_name=run.agent_name,
        sandbox_id=run.sandbox_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_message=run.error_message,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_owned_thread(thread_id: str, auth: AuthContext, db: AsyncSession) -> Thread:
    result = await db.execute(select(Thread).where(Thread.id == thread_id, Thread.user_id == auth.user_id, Thread.org_id == auth.org_id).limit(1))
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


async def _get_owned_run(thread_id: str, run_id: str, auth: AuthContext, db: AsyncSession) -> ThreadRun:
    result = await db.execute(
        select(ThreadRun)
        .where(
            ThreadRun.id == run_id,
            ThreadRun.thread_id == thread_id,
            ThreadRun.user_id == auth.user_id,
            ThreadRun.org_id == auth.org_id,
        )
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Thread run not found")
    return run


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    request: ThreadCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ThreadResponse:
    existing = await db.get(Thread, request.thread_id)
    if existing is not None:
        if existing.user_id == auth.user_id and existing.org_id == auth.org_id:
            # Idempotent: return existing thread instead of 409
            return _thread_to_response(existing)
        raise HTTPException(status_code=403, detail="Thread ID already belongs to another user")

    now = datetime.now(UTC)
    title = (request.title.strip() if request.title else "") or "New Thread"
    thread = Thread(
        id=request.thread_id,
        user_id=auth.user_id,
        org_id=auth.org_id,
        title=title,
        status=request.status.strip(),
        agent_name=request.agent_name.strip() if request.agent_name else None,
        default_model=request.default_model.strip() if request.default_model else None,
        last_model_name=request.last_model_name.strip() if request.last_model_name else None,
        last_active_at=now,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)

    # Sync to LangGraph checkpointer so runs/stream works immediately
    await _sync_langgraph_thread(request.thread_id)

    return _thread_to_response(thread)


@router.get("", response_model=list[ThreadResponse])
async def list_threads(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[ThreadResponse]:
    result = await db.execute(select(Thread).where(Thread.user_id == auth.user_id, Thread.org_id == auth.org_id).order_by(Thread.last_active_at.desc(), Thread.updated_at.desc()))
    return [_thread_to_response(thread) for thread in result.scalars().all()]


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ThreadResponse:
    thread = await _get_owned_thread(thread_id, auth, db)
    return _thread_to_response(thread)


@router.patch("/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    request: ThreadUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ThreadResponse:
    thread = await _get_owned_thread(thread_id, auth, db)

    if request.title is not None:
        thread.title = request.title.strip()
    if request.status is not None:
        thread.status = request.status.strip()
    if request.agent_name is not None:
        thread.agent_name = request.agent_name.strip() or None
    if request.default_model is not None:
        thread.default_model = request.default_model.strip() or None
    if request.last_model_name is not None:
        thread.last_model_name = request.last_model_name.strip() or None

    thread.last_active_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(thread)
    return _thread_to_response(thread)


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    thread = await _get_owned_thread(thread_id, auth, db)
    await db.delete(thread)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{thread_id}/runs", response_model=ThreadRunResponse, status_code=status.HTTP_201_CREATED)
async def create_thread_run(
    thread_id: str,
    request: ThreadRunCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ThreadRunResponse:
    thread = await _get_owned_thread(thread_id, auth, db)

    run = ThreadRun(
        id=request.id,
        thread_id=thread.id,
        user_id=auth.user_id,
        org_id=auth.org_id,
        model_name=request.model_name.strip() if request.model_name else None,
        agent_name=request.agent_name.strip() if request.agent_name else None,
        sandbox_id=request.sandbox_id.strip() if request.sandbox_id else None,
        status=request.status.strip(),
    )
    thread.last_active_at = datetime.now(UTC)
    if run.model_name:
        thread.last_model_name = run.model_name
    if run.agent_name:
        thread.agent_name = run.agent_name

    db.add(run)
    await db.commit()
    await db.refresh(run)
    return _thread_run_to_response(run)


@router.patch("/{thread_id}/runs/{run_id}", response_model=ThreadRunResponse)
async def update_thread_run(
    thread_id: str,
    run_id: str,
    request: ThreadRunUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ThreadRunResponse:
    thread = await _get_owned_thread(thread_id, auth, db)
    run = await _get_owned_run(thread_id, run_id, auth, db)

    if request.status is not None:
        run.status = request.status.strip()
    if request.sandbox_id is not None:
        run.sandbox_id = request.sandbox_id.strip() or None
    if request.error_message is not None:
        run.error_message = request.error_message

    if request.finished_at is not None:
        run.finished_at = request.finished_at
    elif run.status.lower() in {"completed", "failed", "cancelled", "stopped"}:
        run.finished_at = datetime.now(UTC)

    thread.last_active_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(run)
    return _thread_run_to_response(run)
