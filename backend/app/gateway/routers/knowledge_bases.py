"""CRUD API for knowledge bases, documents, and semantic search."""

import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.auth import AuthContext, get_auth_context
from app.gateway.db.database import get_db_session
from app.gateway.db.models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.gateway.rag.chunker import chunk_markdown
from app.gateway.rag.embedder import embed_text, embed_texts
from app.gateway.rag.retriever import search_chunks
from deerflow.config.paths import get_paths

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
    file_size: int = 0
    index_status: str = "none"
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


class KeywordSearchRequest(BaseModel):
    """Request body for keyword search."""

    query: str = Field(..., description="Keyword search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")


class KeywordSearchResultItem(BaseModel):
    """A single keyword search result."""

    doc_id: str
    filename: str
    snippet: str
    score: float


class KeywordSearchResponse(BaseModel):
    """Response model for keyword search results."""

    results: list[KeywordSearchResultItem]


class BuildIndexResponse(BaseModel):
    """Response model for build index operation."""

    indexed: int
    failed: int
    skipped: int


class DocumentContentResponse(BaseModel):
    """Response model for reading document markdown content."""

    content: str
    filename: str


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
        file_size=doc.file_size or 0,
        index_status=doc.index_status or "none",
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

    # Clean up disk directory for the entire KB
    try:
        kb_dir = get_paths().kb_dir(auth.org_id, kb.id)
        shutil.rmtree(kb_dir, ignore_errors=True)
    except Exception:
        logger.warning(f"Failed to clean disk directory for KB {kb_id}", exc_info=True)

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

    Saves the original file and converted markdown to disk. No embedding is
    performed — use the /index endpoint to generate embeddings on demand.
    """
    kb = await _get_kb_or_404(db, kb_id, auth.org_id)

    filename = Path(file.filename or "untitled").name  # sanitize
    content_type = file.content_type or "application/octet-stream"

    # Enforce file size limit (50 MB)
    max_size = 50 * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {max_size // (1024 * 1024)} MB")

    paths = get_paths()
    originals_dir = paths.kb_originals_dir(auth.org_id, kb.id)
    markdown_dir = paths.kb_markdown_dir(auth.org_id, kb.id)
    originals_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    # Save original file to disk
    original_path = originals_dir / filename
    original_path.write_bytes(file_bytes)

    try:
        # Convert to markdown
        markdown_content = await _convert_to_markdown(filename, file_bytes)

        if not markdown_content.strip():
            original_path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail="File produced no extractable text content")

        # Save markdown to disk
        stem = Path(filename).stem
        md_filename = f"{stem}.md"
        md_path = markdown_dir / md_filename
        md_path.write_text(markdown_content, encoding="utf-8")

        # Compute relative paths (relative to base_dir)
        base = paths.base_dir
        rel_original = str(original_path.relative_to(base))
        rel_markdown = str(md_path.relative_to(base))

        # Create document record — no chunking/embedding
        doc = KnowledgeDocument(
            kb_id=kb.id,
            filename=filename,
            content_type=content_type,
            content_md=markdown_content,
            file_path=rel_original,
            markdown_path=rel_markdown,
            file_size=len(file_bytes),
            index_status="none",
            chunk_count=0,
            status="ready",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        logger.info(f"Uploaded document '{filename}' to KB {kb_id} (file-system mode, no embedding)")
        return _doc_to_response(doc)

    except HTTPException:
        raise
    except Exception as e:
        original_path.unlink(missing_ok=True)
        logger.error("Failed to process document '%s': %s", filename, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process document. Please try again or use a different file format.")


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

    # Clean up disk files
    base = get_paths().base_dir
    for rel_path in (doc.file_path, doc.markdown_path):
        if rel_path:
            try:
                (base / rel_path).unlink(missing_ok=True)
            except Exception:
                logger.warning(f"Failed to delete disk file {rel_path}", exc_info=True)

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
# Build Index (on-demand embedding)
# ---------------------------------------------------------------------------


@router.post("/knowledge-bases/{kb_id}/index", response_model=BuildIndexResponse, summary="Build Index")
async def build_index(
    kb_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> BuildIndexResponse:
    """Generate embeddings for all unindexed documents in a knowledge base."""
    kb = await _get_kb_or_404(db, kb_id, auth.org_id)

    stmt = select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id, KnowledgeDocument.index_status != "indexed")
    result = await db.execute(stmt)
    docs = list(result.scalars().all())

    indexed = 0
    failed = 0
    skipped = 0

    for doc in docs:
        content = doc.content_md
        if not content and doc.markdown_path:
            md_file = get_paths().base_dir / doc.markdown_path
            if md_file.exists():
                content = md_file.read_text(encoding="utf-8")

        if not content or not content.strip():
            skipped += 1
            continue

        try:
            doc.index_status = "indexing"
            await db.commit()

            chunks_text = chunk_markdown(content, chunk_size=kb.chunk_size, chunk_overlap=kb.chunk_overlap)
            if not chunks_text:
                doc.index_status = "indexed"
                doc.chunk_count = 0
                await db.commit()
                skipped += 1
                continue

            embeddings = await embed_texts(chunks_text, model=kb.embedding_model)

            # Delete old chunks for this document
            old_chunks_stmt = select(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.id)
            old_result = await db.execute(old_chunks_stmt)
            for old_chunk in old_result.scalars().all():
                await db.delete(old_chunk)

            # Create new chunks
            for i, (text, embedding) in enumerate(zip(chunks_text, embeddings)):
                chunk = KnowledgeChunk(
                    doc_id=doc.id,
                    kb_id=kb.id,
                    content=text,
                    chunk_index=i,
                    embedding=json.dumps(embedding),
                    metadata_json=json.dumps({"filename": doc.filename, "chunk_index": i}),
                )
                db.add(chunk)

            doc.chunk_count = len(chunks_text)
            doc.index_status = "indexed"
            await db.commit()
            indexed += 1
            logger.info(f"Indexed document '{doc.filename}' ({len(chunks_text)} chunks)")

        except Exception as e:
            doc.index_status = "error"
            await db.commit()
            failed += 1
            logger.error(f"Failed to index document '{doc.filename}': {e}", exc_info=True)

    return BuildIndexResponse(indexed=indexed, failed=failed, skipped=skipped)


# ---------------------------------------------------------------------------
# Keyword Search
# ---------------------------------------------------------------------------


@router.post("/knowledge-bases/{kb_id}/keyword-search", response_model=KeywordSearchResponse, summary="Keyword Search")
async def keyword_search(
    kb_id: str,
    request: KeywordSearchRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> KeywordSearchResponse:
    """Full-text keyword search across documents (no index needed)."""
    await _get_kb_or_404(db, kb_id, auth.org_id)

    query = request.query.strip()
    if not query:
        return KeywordSearchResponse(results=[])

    stmt = select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id, KnowledgeDocument.content_md.ilike(f"%{query}%"))
    result = await db.execute(stmt)
    docs = result.scalars().all()

    results: list[KeywordSearchResultItem] = []
    for doc in docs:
        content = doc.content_md or ""
        # Count occurrences for scoring
        count = len(re.findall(re.escape(query), content, re.IGNORECASE))
        # Extract snippet around first match
        match = re.search(re.escape(query), content, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 200)
            snippet = content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(content):
                snippet = snippet + "..."
        else:
            snippet = content[:400]

        results.append(KeywordSearchResultItem(doc_id=doc.id, filename=doc.filename, snippet=snippet, score=float(count)))

    results.sort(key=lambda r: r.score, reverse=True)
    return KeywordSearchResponse(results=results[: request.top_k])


# ---------------------------------------------------------------------------
# File Access (download + content)
# ---------------------------------------------------------------------------


@router.get("/knowledge-bases/{kb_id}/documents/{doc_id}/download", summary="Download Original File")
async def download_document(
    kb_id: str,
    doc_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    """Download the original uploaded file."""
    await _get_kb_or_404(db, kb_id, auth.org_id)

    stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id, KnowledgeDocument.kb_id == kb_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.file_path:
        raise HTTPException(status_code=404, detail="Original file not available")

    file_path = (get_paths().base_dir / doc.file_path).resolve()
    # Path traversal check
    if not str(file_path).startswith(str(get_paths().base_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(path=str(file_path), filename=doc.filename, media_type=doc.content_type)


@router.get("/knowledge-bases/{kb_id}/documents/{doc_id}/content", response_model=DocumentContentResponse, summary="Read Document Content")
async def read_document_content(
    kb_id: str,
    doc_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentContentResponse:
    """Read a document's markdown content."""
    await _get_kb_or_404(db, kb_id, auth.org_id)

    stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id, KnowledgeDocument.kb_id == kb_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    content = doc.content_md
    if not content and doc.markdown_path:
        md_file = get_paths().base_dir / doc.markdown_path
        if md_file.exists():
            content = md_file.read_text(encoding="utf-8")

    return DocumentContentResponse(content=content or "", filename=doc.filename)


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
