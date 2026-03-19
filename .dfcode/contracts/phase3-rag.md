# Phase 3 Contract: Enterprise Knowledge Base (RAG)

## Overview
Implement enterprise knowledge base with document upload, vector storage, retrieval, and Agent integration.

## Execution Phases
### Phase A (parallel)
- role: "backend-rag" — Knowledge base models, RAG pipeline, search tool, API endpoints, tests
- role: "frontend-rag" — Knowledge base management UI, document upload, agent binding

---

## Shared Interfaces

### Knowledge Base API
```
POST   /api/knowledge-bases                          # Create KB
GET    /api/knowledge-bases                          # List KBs for org
GET    /api/knowledge-bases/{id}                     # Get KB detail
PUT    /api/knowledge-bases/{id}                     # Update KB config
DELETE /api/knowledge-bases/{id}                     # Delete KB + all docs

POST   /api/knowledge-bases/{id}/documents           # Upload document
GET    /api/knowledge-bases/{id}/documents           # List documents
DELETE /api/knowledge-bases/{id}/documents/{doc_id}  # Delete document

POST   /api/knowledge-bases/{id}/search              # Search (debug/test)
```

### DB Models
```python
class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    id: str              # UUID
    org_id: str          # FK organizations
    name: str
    description: str
    chunk_size: int      # default 500
    chunk_overlap: int   # default 50
    embedding_model: str # default "text-embedding-3-small"
    created_at: datetime
    updated_at: datetime

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: str              # UUID
    kb_id: str           # FK knowledge_bases
    filename: str
    content_type: str
    content_md: str      # Markdown content after conversion
    chunk_count: int
    status: str          # "processing" | "ready" | "error"
    created_at: datetime

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: str              # UUID
    doc_id: str          # FK knowledge_documents
    kb_id: str           # FK knowledge_bases (denormalized for query speed)
    content: str         # Chunk text
    chunk_index: int
    embedding: list[float]  # Store as JSON array (pgvector later)
    metadata_json: str   # Source info
```

### Harness Integration
- New tool: `knowledge_search(query: str, kb_ids: list[str]) -> str`
- Agent config: add `knowledge_base_ids: list[str]` field
- System prompt: inject `<knowledge_context>` block with retrieved chunks

---

## Role: backend-rag

### Owned Files
- `backend/app/gateway/db/models.py` (MODIFY) — add KnowledgeBase, KnowledgeDocument, KnowledgeChunk
- `backend/app/gateway/routers/knowledge_bases.py` (NEW) — full CRUD + search API
- `backend/app/gateway/rag/` (NEW directory)
  - `__init__.py`
  - `chunker.py` — text splitting (RecursiveCharacterTextSplitter)
  - `embedder.py` — embedding via OpenAI API (httpx, no langchain dep)
  - `retriever.py` — cosine similarity search over chunks
- `backend/app/gateway/app.py` (MODIFY) — register knowledge_bases router
- `backend/tests/test_knowledge_base_models.py` (NEW)
- `backend/tests/test_rag_chunker.py` (NEW)
- `backend/tests/test_knowledge_base_router.py` (NEW)

### Must Do
- Use existing file conversion from harness: `deerflow.utils.file_conversion.convert_file_to_markdown()`
- Chunker: split markdown by headers first, then by size. Use langchain `RecursiveCharacterTextSplitter` or implement simple version.
- Embedder: call OpenAI embeddings API via httpx (env var OPENAI_API_KEY). Return list[float].
- Retriever: cosine similarity over stored embeddings. Return top-k chunks.
- Store embeddings as JSON in `embedding` column (simple approach, pgvector migration later).
- All endpoints require AuthContext, filter by org_id.
- Document upload: accept multipart file, convert to markdown, chunk, embed, store.
- Search endpoint: accept query string, return top-k relevant chunks with scores.
- Unit tests for chunker, models, and router auth.
- Follow existing code style.

### Must NOT Do
- Do NOT modify harness files in `packages/harness/deerflow/`
- Do NOT modify frontend files
- Do NOT use pgvector extension (use JSON array + Python cosine similarity for now)
- Do NOT implement the harness-level `knowledge_search` tool yet (Phase 3b)

---

## Role: frontend-rag

### Owned Files
- `frontend/src/app/workspace/knowledge/` (NEW directory)
  - `page.tsx` — knowledge base list page
  - `[id]/page.tsx` — KB detail with document list
  - `layout.tsx`
- `frontend/src/core/knowledge/` (NEW directory)
  - `api.ts` — KB API client
  - `types.ts` — KB types
  - `hooks.ts` — React hooks for KB data
- `frontend/src/components/workspace/knowledge/` (NEW directory)
  - `kb-card.tsx` — knowledge base card component
  - `document-upload.tsx` — file upload component
  - `document-list.tsx` — document list with status
  - `search-panel.tsx` — search test panel
- `frontend/src/components/workspace/workspace-sidebar.tsx` (MODIFY) — add Knowledge nav item

### Must Do
- KB list page: card grid showing name, description, doc count, created date
- Create KB dialog: name + description + optional chunk settings
- KB detail page: document list + upload area + search test panel
- Document upload: drag-and-drop or click, show processing status
- Search panel: input query, show results with relevance scores
- Add "Knowledge Base" nav item in workspace sidebar
- Use existing Shadcn components, credentials: "include" on all fetches
- Follow existing code patterns

### Must NOT Do
- Do NOT modify backend Python files
- Do NOT implement agent-KB binding UI (separate task)
