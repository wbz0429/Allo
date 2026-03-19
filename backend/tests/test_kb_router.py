"""Tests for the knowledge base CRUD API router.

Uses httpx.AsyncClient with ASGITransport against a test FastAPI app
backed by an in-memory SQLite database. The embedder is mocked to
avoid OpenAI API calls.
"""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import Base
from app.gateway.routers.knowledge_bases import router

# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

_DEV_AUTH = AuthContext(user_id="dev-user-000", org_id="dev-org-000", role="admin")


async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


async def _override_get_auth_context() -> AuthContext:
    return _DEV_AUTH


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.dependency_overrides[get_auth_context] = _override_get_auth_context
    return app


@pytest.fixture(autouse=True)
async def _setup_db():
    """Create tables before each test and drop them after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def app():
    return _create_test_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests: Knowledge Base CRUD
# ---------------------------------------------------------------------------


class TestCreateKnowledgeBase:
    """Tests for POST /api/knowledge-bases."""

    @pytest.mark.asyncio
    async def test_create_kb(self, client):
        resp = await client.post(
            "/api/knowledge-bases",
            json={"name": "Test KB", "description": "A test knowledge base"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test KB"
        assert data["description"] == "A test knowledge base"
        assert data["org_id"] == "dev-org-000"
        assert data["chunk_size"] == 500
        assert data["chunk_overlap"] == 50
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_kb_with_custom_settings(self, client):
        resp = await client.post(
            "/api/knowledge-bases",
            json={
                "name": "Custom KB",
                "chunk_size": 1000,
                "chunk_overlap": 100,
                "embedding_model": "text-embedding-3-large",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["chunk_size"] == 1000
        assert data["chunk_overlap"] == 100
        assert data["embedding_model"] == "text-embedding-3-large"

    @pytest.mark.asyncio
    async def test_create_kb_overlap_gte_size_rejected(self, client):
        resp = await client.post(
            "/api/knowledge-bases",
            json={"name": "Bad KB", "chunk_size": 100, "chunk_overlap": 100},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_kb_missing_name_rejected(self, client):
        resp = await client.post("/api/knowledge-bases", json={"description": "no name"})
        assert resp.status_code == 422


class TestListKnowledgeBases:
    """Tests for GET /api/knowledge-bases."""

    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        resp = await client.get("/api/knowledge-bases")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_after_create(self, client):
        await client.post("/api/knowledge-bases", json={"name": "KB-1"})
        await client.post("/api/knowledge-bases", json={"name": "KB-2"})

        resp = await client.get("/api/knowledge-bases")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {kb["name"] for kb in data}
        assert names == {"KB-1", "KB-2"}


class TestGetKnowledgeBase:
    """Tests for GET /api/knowledge-bases/{id}."""

    @pytest.mark.asyncio
    async def test_get_existing_kb(self, client):
        create_resp = await client.post("/api/knowledge-bases", json={"name": "My KB"})
        kb_id = create_resp.json()["id"]

        resp = await client.get(f"/api/knowledge-bases/{kb_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "My KB"
        assert resp.json()["id"] == kb_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_kb_404(self, client):
        resp = await client.get("/api/knowledge-bases/nonexistent-id")
        assert resp.status_code == 404


class TestUpdateKnowledgeBase:
    """Tests for PUT /api/knowledge-bases/{id}."""

    @pytest.mark.asyncio
    async def test_update_name(self, client):
        create_resp = await client.post("/api/knowledge-bases", json={"name": "Original"})
        kb_id = create_resp.json()["id"]

        resp = await client.put(f"/api/knowledge-bases/{kb_id}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_description(self, client):
        create_resp = await client.post("/api/knowledge-bases", json={"name": "KB"})
        kb_id = create_resp.json()["id"]

        resp = await client.put(f"/api/knowledge-bases/{kb_id}", json={"description": "New desc"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "New desc"

    @pytest.mark.asyncio
    async def test_update_nonexistent_kb_404(self, client):
        resp = await client.put("/api/knowledge-bases/fake-id", json={"name": "X"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_partial_preserves_other_fields(self, client):
        create_resp = await client.post(
            "/api/knowledge-bases",
            json={"name": "KB", "description": "Desc", "chunk_size": 800},
        )
        kb_id = create_resp.json()["id"]

        resp = await client.put(f"/api/knowledge-bases/{kb_id}", json={"name": "New Name"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["description"] == "Desc"
        assert data["chunk_size"] == 800


class TestDeleteKnowledgeBase:
    """Tests for DELETE /api/knowledge-bases/{id}."""

    @pytest.mark.asyncio
    async def test_delete_existing_kb(self, client):
        create_resp = await client.post("/api/knowledge-bases", json={"name": "Delete Me"})
        kb_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/knowledge-bases/{kb_id}")
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"/api/knowledge-bases/{kb_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_kb_404(self, client):
        resp = await client.delete("/api/knowledge-bases/fake-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Document management (mocked embedder)
# ---------------------------------------------------------------------------


class TestListDocuments:
    """Tests for GET /api/knowledge-bases/{id}/documents."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client):
        create_resp = await client.post("/api/knowledge-bases", json={"name": "Doc KB"})
        kb_id = create_resp.json()["id"]

        resp = await client.get(f"/api/knowledge-bases/{kb_id}/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_documents_nonexistent_kb_404(self, client):
        resp = await client.get("/api/knowledge-bases/fake-id/documents")
        assert resp.status_code == 404


class TestDeleteDocument:
    """Tests for DELETE /api/knowledge-bases/{id}/documents/{doc_id}."""

    @pytest.mark.asyncio
    async def test_delete_document_nonexistent_kb_404(self, client):
        resp = await client.delete("/api/knowledge-bases/fake-id/documents/fake-doc")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Search (mocked embedder)
# ---------------------------------------------------------------------------


class TestSearchKnowledgeBase:
    """Tests for POST /api/knowledge-bases/{id}/search."""

    @pytest.mark.asyncio
    async def test_search_nonexistent_kb_404(self, client):
        resp = await client.post(
            "/api/knowledge-bases/fake-id/search",
            json={"query": "test query"},
        )
        assert resp.status_code == 404
