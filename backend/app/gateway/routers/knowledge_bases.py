"""CRUD API for knowledge bases, documents, and semantic search."""

import json
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.gateway.rag.chunker import chunk_markdown
from app.gateway.rag.embedder import embed_text, embed_texts
from app.gateway.rag.retriever import search_chunks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["knowledge-bases"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class KnowledgeBaseCreateRequest(BaseModel):
    """Request body for creating a knowledge base."""

    name: str = Field(..., description="Knowledge base name")
    description: str = Field(default="", description="Optional description")
    chunk_size: int = Field(default=500, ge=100, le=10000, description="Chunk size in characters")
    chunk_overlap: int = Field(default=50, ge=0, le=1000, description="Overlap between chunks")
    embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")


class KnowledgeBaseUpdateRequest(BaseModel):
    """Request body for updating a knowledge base."""

    name: str | None = Field(default=None, description="Updated name")
    description: str | None = Field(default=None, description="Updated description")
    chunk_size: int | None = Field(default=None, ge=100, le=10000, description="Updated chunk size")
    chunk_overlap: int | None = Field(default=None, ge=0, le=1000, description="Updated overlap")
    embedding_model: str | None = Field(default=None, description="Updated embedding model")


class KnowledgeBaseResponse(BaseModel):
    """Response model for a knowledge base."""

    id: str
    org_id: str
    name: str
    description: str
    chunk_size: int
    chunk_overlap: int
    embedding_model: str
    document_count: int = 0
    created_at: str
    updated_at: str


class KnowledgeDocumentResponse(BaseModel):
    """Response model for a knowledge document."""

    id: str
    kb_id: str
    filename: str
    content_type: str
    chunk_count: int
    status: str
    created_at: str


class SearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")


class SearchResultItem(BaseModel):
    """A single search result."""

    id: str
    content: str
    score: float
    chunk_index: int
    doc_id: str


class SearchResponse(BaseModel):
    """Response model for search results."""

    results: list[SearchResultItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kb_to_response(kb: KnowledgeBase, doc_count: int = 0) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(
        id=kb.id,
        org_id=kb.org_id,
        name=kb.name,
        description=kb.description,
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        embedding_model=kb.embedding_model,
        document_count=doc_count,
        created_at=kb.created_at.isoformat() if kb.created_at else "",
        updated_at=kb.updated_at.isoformat() if kb.updated_at else "",
    )


def _doc_to_response(doc: KnowledgeDocument) -> KnowledgeDocumentResponse:
    return KnowledgeDocumentResponse(
        id=doc.id,
        kb_id=doc.kb_id,
        filename=doc.filename,
        content_type=doc.content_type,
        chunk_count=doc.chunk_count,
        status=doc.status,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
    )


async def _get_kb_or_404(db: AsyncSession, kb_id: str, org_id: str) -> KnowledgeBase:
    """Fetch a knowledge base by ID, scoped to org. Raises 404 if not found."""
    stmt = select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == org_id)
    result = await db.execute(stmt)
    kb = result.scalar_one_or_none()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


async def _count_documents(db: AsyncSession, kb_id: str) -> int:
    stmt = select(func.count()).select_from(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id)
    result = await db.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Knowledge Base CRUD
# ---------------------------------------------------------------------------


@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=201, summary="Create Knowledge Base")
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeBaseResponse:
    """Create a new knowledge base for the authenticated organization."""
    if request.chunk_overlap >= request.chunk_size:
        raise HTTPException(status_code=422, detail="chunk_overlap must be less than chunk_size")

    kb = KnowledgeBase(
        org_id=auth.org_id,
        name=request.name,
        description=request.description,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        embedding_model=request.embedding_model,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    logger.info(f"Created knowledge base '{kb.name}' (id={kb.id}) for org={auth.org_id}")
    return _kb_to_response(kb, doc_count=0)


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse], summary="List Knowledge Bases")
async def list_knowledge_bases(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeBaseResponse]:
    """List all knowledge bases for the authenticated organization."""
    stmt = select(KnowledgeBase).where(KnowledgeBase.org_id == auth.org_id).order_by(KnowledgeBase.created_at.desc())
    result = await db.execute(stmt)
    kbs = result.scalars().all()

    responses = []
    for kb in kbs:
        doc_count = await _count_documents(db, kb.id)
        responses.append(_kb_to_response(kb, doc_count=doc_count))
    return responses


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse, summary="Get Knowledge Base")
async def get_knowledge_base(
    kb_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeBaseResponse:
    """Get a specific knowledge base by ID."""
    kb = await _get_kb_or_404(db, kb_id, auth.org_id)
    doc_count = await _count_documents(db, kb.id)
    return _kb_to_response(kb, doc_count=doc_count)


@router.put("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse, summary="Update Knowledge Base")
async def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeBaseResponse:
    """Update a knowledge base's configuration."""
    kb = await _get_kb_or_404(db, kb_id, auth.org_id)

    if request.name is not None:
        kb.name = request.name
    if request.description is not None:
        kb.description = request.description
    if request.chunk_size is not None:
        kb.chunk_size = request.chunk_size
    if request.chunk_overlap is not None:
        kb.chunk_overlap = request.chunk_overlap
    if request.embedding_model is not None:
        kb.embedding_model = request.embedding_model

    # Validate overlap < size after applying updates
    if kb.chunk_overlap >= kb.chunk_size:
        raise HTTPException(status_code=422, detail="chunk_overlap must be less than chunk_size")

    await db.commit()
    await db.refresh(kb)
    doc_count = await _count_documents(db, kb.id)
    logger.info(f"Updated knowledge base '{kb.name}' (id={kb.id})")
    return _kb_to_response(kb, doc_count=doc_count)


@router.delete("/knowledge-bases/{kb_id}", status_code=204, summary="Delete Knowledge Base")
async def delete_knowledge_base(
    kb_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a knowledge base and all its documents and chunks."""
    kb = await _get_kb_or_404(db, kb_id, auth.org_id)
    await db.delete(kb)
    await db.commit()
    logger.info(f"Deleted knowledge base id={kb_id}")


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------


@router.post("/knowledge-bases/{kb_id}/documents", response_model=KnowledgeDocumentResponse, status_code=201, summary="Upload Document")
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeDocumentResponse:
    """Upload a document to a knowledge base.

    Accepts text, markdown, PDF, PPT, and Word files. The file is converted
    to markdown, chunked, embedded, and stored for semantic search.
    """
    kb = await _get_kb_or_404(db, kb_id, auth.org_id)

    filename = file.filename or "untitled"
    content_type = file.content_type or "application/octet-stream"

    # Create document record in "processing" state
    doc = KnowledgeDocument(
        kb_id=kb.id,
        filename=filename,
        content_type=content_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    try:
        # Read file content
        file_bytes = await file.read()

        # Convert to markdown based on file type
        markdown_content = await _convert_to_markdown(filename, file_bytes)

        if not markdown_content.strip():
            doc.status = "error"
            doc.content_md = ""
            await db.commit()
            raise HTTPException(status_code=422, detail="File produced no extractable text content")

        doc.content_md = markdown_content

        # Chunk the content
        chunks_text = chunk_markdown(markdown_content, chunk_size=kb.chunk_size, chunk_overlap=kb.chunk_overlap)

        if not chunks_text:
            doc.status = "ready"
            doc.chunk_count = 0
            await db.commit()
            await db.refresh(doc)
            return _doc_to_response(doc)

        # Generate embeddings
        embeddings = await embed_texts(chunks_text, model=kb.embedding_model)

        # Store chunks with embeddings
        for i, (text, embedding) in enumerate(zip(chunks_text, embeddings)):
            chunk = KnowledgeChunk(
                doc_id=doc.id,
                kb_id=kb.id,
                content=text,
                chunk_index=i,
                embedding=json.dumps(embedding),
                metadata_json=json.dumps({"filename": filename, "chunk_index": i}),
            )
            db.add(chunk)

        doc.chunk_count = len(chunks_text)
        doc.status = "ready"
        await db.commit()
        await db.refresh(doc)

        logger.info(f"Uploaded document '{filename}' to KB {kb_id}: {len(chunks_text)} chunks")
        return _doc_to_response(doc)

    except HTTPException:
        raise
    except Exception as e:
        doc.status = "error"
        await db.commit()
        logger.error(f"Failed to process document '{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[KnowledgeDocumentResponse], summary="List Documents")
async def list_documents(
    kb_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeDocumentResponse]:
    """List all documents in a knowledge base."""
    await _get_kb_or_404(db, kb_id, auth.org_id)

    stmt = select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id).order_by(KnowledgeDocument.created_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [_doc_to_response(d) for d in docs]


@router.delete("/knowledge-bases/{kb_id}/documents/{doc_id}", status_code=204, summary="Delete Document")
async def delete_document(
    kb_id: str,
    doc_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a document and all its chunks from a knowledge base."""
    await _get_kb_or_404(db, kb_id, auth.org_id)

    stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id, KnowledgeDocument.kb_id == kb_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(doc)
    await db.commit()
    logger.info(f"Deleted document {doc_id} from KB {kb_id}")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.post("/knowledge-bases/{kb_id}/search", response_model=SearchResponse, summary="Search Knowledge Base")
async def search_knowledge_base(
    kb_id: str,
    request: SearchRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    """Semantic search over a knowledge base's documents."""
    await _get_kb_or_404(db, kb_id, auth.org_id)

    # Embed the query
    query_embedding = await embed_text(request.query)

    # Search chunks
    results = await search_chunks(db, query_embedding, kb_id, top_k=request.top_k)

    return SearchResponse(
        results=[
            SearchResultItem(
                id=r["id"],
                content=r["content"],
                score=r["score"],
                chunk_index=r["chunk_index"],
                doc_id=r["doc_id"],
            )
            for r in results
        ]
    )


# ---------------------------------------------------------------------------
# File conversion helper
# ---------------------------------------------------------------------------

# Extensions that need markitdown conversion
_CONVERTIBLE_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".xls", ".xlsx", ".doc", ".docx"}


async def _convert_to_markdown(filename: str, file_bytes: bytes) -> str:
    """Convert uploaded file bytes to markdown text.

    For text/markdown files, decodes directly. For PDF/PPT/Word, uses
    the harness file conversion utility.

    Args:
        filename: Original filename (used to determine extension).
        file_bytes: Raw file content.

    Returns:
        Markdown text content.
    """
    ext = Path(filename).suffix.lower()

    # Plain text and markdown: decode directly
    if ext in {".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".json", ".yaml", ".yml"}:
        return file_bytes.decode("utf-8", errors="replace")

    # Convertible document formats
    if ext in _CONVERTIBLE_EXTENSIONS:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            from deerflow.utils.file_conversion import convert_file_to_markdown

            md_path = await convert_file_to_markdown(tmp_path)
            if md_path and md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                md_path.unlink(missing_ok=True)
                return content
            return ""
        finally:
            tmp_path.unlink(missing_ok=True)

    # Fallback: try to decode as text
    return file_bytes.decode("utf-8", errors="replace")
