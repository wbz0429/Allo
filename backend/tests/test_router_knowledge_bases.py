"""Tests for the knowledge_bases router — request/response models and helpers."""

import inspect

import pytest
from pydantic import ValidationError

from app.gateway.auth import AuthContext
from app.gateway.routers.knowledge_bases import (
    _CONVERTIBLE_EXTENSIONS,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdateRequest,
    KnowledgeDocumentResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    _convert_to_markdown,
)

# ---------------------------------------------------------------------------
# Request model validation
# ---------------------------------------------------------------------------


class TestKnowledgeBaseCreateRequest:
    def test_valid_request(self) -> None:
        req = KnowledgeBaseCreateRequest(name="Test KB")
        assert req.name == "Test KB"
        assert req.description == ""
        assert req.chunk_size == 500
        assert req.chunk_overlap == 50
        assert req.embedding_model == "text-embedding-3-small"

    def test_custom_values(self) -> None:
        req = KnowledgeBaseCreateRequest(
            name="Custom",
            description="A custom KB",
            chunk_size=1000,
            chunk_overlap=100,
            embedding_model="text-embedding-3-large",
        )
        assert req.chunk_size == 1000
        assert req.chunk_overlap == 100

    def test_chunk_size_min_validation(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeBaseCreateRequest(name="Test", chunk_size=50)

    def test_chunk_size_max_validation(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeBaseCreateRequest(name="Test", chunk_size=20000)

    def test_chunk_overlap_min_validation(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeBaseCreateRequest(name="Test", chunk_overlap=-1)

    def test_chunk_overlap_max_validation(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeBaseCreateRequest(name="Test", chunk_overlap=2000)


class TestKnowledgeBaseUpdateRequest:
    def test_all_none_by_default(self) -> None:
        req = KnowledgeBaseUpdateRequest()
        assert req.name is None
        assert req.description is None
        assert req.chunk_size is None
        assert req.chunk_overlap is None
        assert req.embedding_model is None

    def test_partial_update(self) -> None:
        req = KnowledgeBaseUpdateRequest(name="Updated Name")
        assert req.name == "Updated Name"
        assert req.description is None


class TestSearchRequest:
    def test_valid_request(self) -> None:
        req = SearchRequest(query="test query")
        assert req.query == "test query"
        assert req.top_k == 5

    def test_custom_top_k(self) -> None:
        req = SearchRequest(query="test", top_k=10)
        assert req.top_k == 10

    def test_top_k_min_validation(self) -> None:
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=0)

    def test_top_k_max_validation(self) -> None:
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=100)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class TestKnowledgeBaseResponse:
    def test_creation(self) -> None:
        resp = KnowledgeBaseResponse(
            id="kb-1",
            org_id="org-1",
            name="Test",
            description="",
            chunk_size=500,
            chunk_overlap=50,
            embedding_model="text-embedding-3-small",
            document_count=3,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert resp.id == "kb-1"
        assert resp.document_count == 3

    def test_default_document_count(self) -> None:
        resp = KnowledgeBaseResponse(
            id="kb-1",
            org_id="org-1",
            name="Test",
            description="",
            chunk_size=500,
            chunk_overlap=50,
            embedding_model="text-embedding-3-small",
            created_at="",
            updated_at="",
        )
        assert resp.document_count == 0


class TestKnowledgeDocumentResponse:
    def test_creation(self) -> None:
        resp = KnowledgeDocumentResponse(
            id="doc-1",
            kb_id="kb-1",
            filename="test.md",
            content_type="text/markdown",
            chunk_count=5,
            status="ready",
            created_at="2024-01-01T00:00:00",
        )
        assert resp.filename == "test.md"
        assert resp.status == "ready"


class TestSearchResultItem:
    def test_creation(self) -> None:
        item = SearchResultItem(
            id="c-1",
            content="Hello world",
            score=0.95,
            chunk_index=0,
            doc_id="doc-1",
        )
        assert item.score == 0.95
        assert item.chunk_index == 0


class TestSearchResponse:
    def test_creation(self) -> None:
        resp = SearchResponse(results=[
            SearchResultItem(id="c-1", content="Hi", score=0.9, chunk_index=0, doc_id="doc-1"),
        ])
        assert len(resp.results) == 1

    def test_empty_results(self) -> None:
        resp = SearchResponse(results=[])
        assert resp.results == []


# ---------------------------------------------------------------------------
# _convert_to_markdown
# ---------------------------------------------------------------------------


class TestConvertToMarkdown:
    @pytest.mark.asyncio
    async def test_text_file(self) -> None:
        result = await _convert_to_markdown("test.txt", b"Hello world")
        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_markdown_file(self) -> None:
        result = await _convert_to_markdown("test.md", b"# Title\nContent")
        assert result == "# Title\nContent"

    @pytest.mark.asyncio
    async def test_json_file(self) -> None:
        result = await _convert_to_markdown("data.json", b'{"key": "value"}')
        assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_yaml_file(self) -> None:
        result = await _convert_to_markdown("config.yaml", b"key: value")
        assert result == "key: value"

    @pytest.mark.asyncio
    async def test_csv_file(self) -> None:
        result = await _convert_to_markdown("data.csv", b"a,b,c\n1,2,3")
        assert result == "a,b,c\n1,2,3"

    @pytest.mark.asyncio
    async def test_unknown_extension_fallback_to_text(self) -> None:
        result = await _convert_to_markdown("file.xyz", b"some content")
        assert result == "some content"

    @pytest.mark.asyncio
    async def test_utf8_decode_errors_replaced(self) -> None:
        result = await _convert_to_markdown("test.txt", b"Hello \xff world")
        assert "Hello" in result
        assert "world" in result

    def test_convertible_extensions(self) -> None:
        assert ".pdf" in _CONVERTIBLE_EXTENSIONS
        assert ".docx" in _CONVERTIBLE_EXTENSIONS
        assert ".pptx" in _CONVERTIBLE_EXTENSIONS
        assert ".xlsx" in _CONVERTIBLE_EXTENSIONS


# ---------------------------------------------------------------------------
# Auth dependency on all endpoints
# ---------------------------------------------------------------------------


class TestKnowledgeBasesRouterAuth:
    def _get_auth_param(self, func):
        sig = inspect.signature(func)
        for name, param in sig.parameters.items():
            if name == "auth":
                return param
        return None

    def test_create_kb_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import create_knowledge_base
        param = self._get_auth_param(create_knowledge_base)
        assert param is not None
        assert param.annotation is AuthContext

    def test_list_kb_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import list_knowledge_bases
        param = self._get_auth_param(list_knowledge_bases)
        assert param is not None

    def test_get_kb_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import get_knowledge_base
        param = self._get_auth_param(get_knowledge_base)
        assert param is not None

    def test_update_kb_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import update_knowledge_base
        param = self._get_auth_param(update_knowledge_base)
        assert param is not None

    def test_delete_kb_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import delete_knowledge_base
        param = self._get_auth_param(delete_knowledge_base)
        assert param is not None

    def test_upload_document_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import upload_document
        param = self._get_auth_param(upload_document)
        assert param is not None

    def test_list_documents_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import list_documents
        param = self._get_auth_param(list_documents)
        assert param is not None

    def test_delete_document_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import delete_document
        param = self._get_auth_param(delete_document)
        assert param is not None

    def test_search_kb_has_auth(self) -> None:
        from app.gateway.routers.knowledge_bases import search_knowledge_base
        param = self._get_auth_param(search_knowledge_base)
        assert param is not None
