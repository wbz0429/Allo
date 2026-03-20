# CR Report: Knowledge Base + RAG Pipeline (Phase 3)

## Summary

The Phase 3 RAG implementation covers the core CRUD API, document ingestion pipeline, and frontend KB management UI. All 8 plan-specified API endpoints are present and every endpoint correctly enforces `org_id` isolation via `Depends(get_auth_context)`. The frontend module is well-structured with clean separation across `core/knowledge/{api,hooks,types}.ts` and four focused UI components. However, there are three critical API shape mismatches between the frontend client and the backend that will cause runtime failures, the harness integration layer (knowledge_search tool, AgentConfig extension, prompt injection) is entirely absent, and the retriever uses a full in-memory scan instead of pgvector — making it unsuitable for production scale. These gaps mean Phase 3 is functionally incomplete: the KB management UI and ingestion pipeline work, but the Agent cannot actually use the knowledge bases.

---

## Files Reviewed

- `backend/app/gateway/rag/chunker.py`
- `backend/app/gateway/rag/embedder.py`
- `backend/app/gateway/rag/retriever.py`
- `backend/app/gateway/routers/knowledge_bases.py`
- `backend/app/gateway/db/models.py` (KnowledgeBase, KnowledgeDocument, KnowledgeChunk sections)
- `backend/packages/harness/deerflow/config/agents_config.py`
- `backend/packages/harness/deerflow/agents/lead_agent/prompt.py`
- `backend/packages/harness/deerflow/utils/file_conversion.py`
- `frontend/src/app/workspace/knowledge/page.tsx`
- `frontend/src/app/workspace/knowledge/[id]/page.tsx`
- `frontend/src/app/workspace/knowledge/layout.tsx`
- `frontend/src/components/workspace/knowledge/kb-card.tsx`
- `frontend/src/components/workspace/knowledge/document-list.tsx`
- `frontend/src/components/workspace/knowledge/document-upload.tsx`
- `frontend/src/components/workspace/knowledge/search-panel.tsx`
- `frontend/src/core/knowledge/api.ts`
- `frontend/src/core/knowledge/hooks.ts`
- `frontend/src/core/knowledge/types.ts`
- `frontend/src/core/knowledge/api.test.ts`

---

## Plan vs Implementation Gap Analysis

| Plan Requirement | Status | Notes |
|---|---|---|
| `POST /api/knowledge-bases` | ✅ Implemented | `knowledge_bases.py:152` |
| `GET /api/knowledge-bases` | ✅ Implemented | `knowledge_bases.py:177` |
| `PUT /api/knowledge-bases/{id}` | ✅ Implemented | `knowledge_bases.py:206` |
| `DELETE /api/knowledge-bases/{id}` | ✅ Implemented | `knowledge_bases.py:238` |
| `POST /api/knowledge-bases/{id}/documents` | ✅ Implemented | `knowledge_bases.py:256` |
| `GET /api/knowledge-bases/{id}/documents` | ✅ Implemented | `knowledge_bases.py:340` |
| `DELETE /api/knowledge-bases/{id}/documents/{doc_id}` | ✅ Implemented | `knowledge_bases.py:355` |
| `POST /api/knowledge-bases/{id}/search` | ✅ Implemented | `knowledge_bases.py:381` |
| org_id isolation on all KB endpoints | ✅ Implemented | All routes use `Depends(get_auth_context)` + `org_id` filter |
| RAG pipeline: document parsing → chunking → embedding → storage | ✅ Implemented | Synchronous in upload handler; reuses `deerflow.utils.file_conversion` |
| Reuse existing PDF/PPT/Excel/Word → Markdown conversion | ✅ Implemented | `_convert_to_markdown()` calls `deerflow.utils.file_conversion.convert_file_to_markdown` |
| pgvector integration (or alternative vector DB) | ❌ Missing | Embeddings stored as JSON `Text` column; retriever does full in-memory cosine scan |
| `knowledge_search` tool in harness (`deerflow/tools/builtins/knowledge_search_tool.py`) | ❌ Missing | File does not exist; Agent cannot query knowledge bases |
| `AgentConfig.knowledge_base_ids` field | ❌ Missing | `agents_config.py:AgentConfig` has no `knowledge_base_ids` field |
| System prompt `<knowledge_context>` injection | ❌ Missing | `prompt.py:apply_prompt_template` has no knowledge context block |
| Agent binding to knowledge bases (config UI + backend) | ❌ Missing | Depends on the three harness items above |
| Frontend: create KB | ✅ Implemented | Dialog in `page.tsx` |
| Frontend: upload documents | ✅ Implemented | `document-upload.tsx` with drag-and-drop |
| Frontend: list documents | ✅ Implemented | `document-list.tsx` |
| Frontend: search panel | ✅ Implemented | `search-panel.tsx` |
| Frontend: delete KB | ✅ Implemented | `[id]/page.tsx` |
| Frontend: delete document | ✅ Implemented | `document-list.tsx` |
| Document version management | ❌ Missing | No versioning concept in model or API |
| Document preview | ❌ Missing | No preview endpoint or UI |
| Chunk strategy configuration in create UI | ⚠️ Partial | Backend supports `chunk_size`/`chunk_overlap`/`embedding_model` on create; frontend create dialog only exposes `name` and `description` |
| Edit KB settings UI | ⚠️ Partial | `updateKnowledgeBase` API function exists in `api.ts`; no `useUpdateKnowledgeBase` hook in `hooks.ts`; no UI |

---

## Code Quality Issues

### Critical — Runtime Failures

1. **API shape mismatch: list knowledge bases** (`frontend/src/core/knowledge/api.ts:17-18`)
   - Frontend expects `{ knowledge_bases: KnowledgeBase[] }` (wrapped object).
   - Backend `GET /api/knowledge-bases` returns a bare JSON array (`list[KnowledgeBaseResponse]`).
   - Result: `data.knowledge_bases` is always `undefined`; the KB list page renders empty.

2. **API shape mismatch: list documents** (`frontend/src/core/knowledge/api.ts:80-81`)
   - Frontend expects `{ documents: KnowledgeDocument[] }`.
   - Backend `GET /api/knowledge-bases/{kb_id}/documents` returns a bare JSON array.
   - Result: `data.documents` is always `undefined`; document list never populates.

3. **API shape mismatch: search results** (`frontend/src/core/knowledge/api.ts:128-129`, `search-panel.tsx:55-67`)
   - Frontend `SearchResult` type is `{ chunk: KnowledgeChunk, score: number }` — a nested structure.
   - Backend `SearchResultItem` is flat: `{ id, content, score, chunk_index, doc_id }`.
   - `search-panel.tsx` accesses `result.chunk.id`, `result.chunk.content`, `result.chunk.chunk_index` — all undefined.
   - The `api.test.ts` mock at line 114 also uses the flat backend shape, confirming the frontend type is wrong.

4. **Synchronous document processing blocks HTTP request** (`knowledge_bases.py:283-329`)
   - File conversion, chunking, and embedding all happen inline in the upload handler.
   - For a large PDF with many chunks, the OpenAI embedding API call alone can take 10–30 seconds.
   - No `BackgroundTasks` or task queue used. Large uploads will hit gateway/nginx timeouts.

### Significant

5. **Full in-memory retrieval does not scale** (`retriever.py:62-64`)
   - `search_chunks` loads every `KnowledgeChunk` row for the KB into Python memory, then scores them in a loop.
   - A KB with 10,000 chunks × 1536-float embeddings = ~60 MB per query, deserialized from JSON each time.
   - No index, no ANN, no pgvector. This is a prototype-only approach.

6. **Embeddings stored as JSON text** (`models.py:191`, `retriever.py:72`)
   - `embedding: Mapped[str]` stores a `json.dumps(list[float])` string.
   - Plan explicitly recommended pgvector. Using `Text` means no SQL-level vector operations, no index, and significant storage overhead (~4× vs binary float32).

7. **`content_md` stored in DB** (`models.py:154`)
   - Full markdown content of every document is stored in the `knowledge_documents` table.
   - For large documents this bloats the DB and is never served to the client (not in `KnowledgeDocumentResponse`).
   - Should be stored in object storage (S3/MinIO) with only a reference in the DB.

8. **Embedder hardcoded to OpenAI** (`embedder.py:13-16`)
   - `OPENAI_API_BASE` and `OPENAI_API_KEY` are the only supported provider.
   - `KnowledgeBase.embedding_model` field accepts any string, but the embedder always calls OpenAI regardless.
   - No support for the other providers already configured in the harness (Anthropic, DeepSeek, Google, etc.).

9. **Missing `useUpdateKnowledgeBase` hook** (`hooks.ts`)
   - `updateKnowledgeBase` is exported from `api.ts` but has no corresponding React Query mutation hook.
   - No UI exists to edit chunk size, overlap, or embedding model after creation.

10. **Chunker overlap logic allows slight overrun** (`chunker.py:103`)
    - `if len(candidate) <= chunk_size * 1.2` — overlap prepend can produce chunks up to 20% over `chunk_size`.
    - This is undocumented and inconsistent with the validated `chunk_size` contract.

11. **No file size limit on upload** (`knowledge_bases.py:285`)
    - `await file.read()` reads the entire file into memory with no size cap.
    - A malicious or accidental 500 MB upload will OOM the gateway process.

12. **No pagination on list endpoints** (`knowledge_bases.py:177`, `knowledge_bases.py:340`)
    - Both list endpoints return all rows. An org with thousands of documents will return unbounded results.

---

## Security / Architecture Concerns

- **org_id isolation is correct** on all 8 endpoints. `_get_kb_or_404` always scopes by `org_id`. No cross-tenant data leak path found.
- **No file type validation beyond extension** (`_convert_to_markdown`). A `.pdf` extension with HTML content will be passed to markitdown. Consider MIME type sniffing.
- **Temporary files are cleaned up** in `finally` blocks — no temp file leak.
- **Architecture boundary respected**: `knowledge_bases.py` imports from `deerflow.utils.file_conversion` (harness utility), which is acceptable. The harness does not import `app.*`.
- **Missing harness integration is the biggest architectural gap**: the plan's core value proposition — Agent answers questions using enterprise knowledge — requires `knowledge_search_tool.py`, `AgentConfig.knowledge_base_ids`, and prompt injection. None of these exist. The KB management UI is built but the Agent is completely unaware of knowledge bases.
- **Embedding API key exposure**: `OPENAI_API_KEY` is read directly from env in `embedder.py`. If the per-tenant embedding model is ever configurable, this needs to route through the tenant config system, not a global env var.

---

## Recommendations

1. **[Critical] Fix the three API shape mismatches** before any QA. Either wrap backend list responses in `{ knowledge_bases: [...] }` / `{ documents: [...] }` objects, or fix the frontend to parse bare arrays. Align `SearchResult` frontend type with the flat `SearchResultItem` backend shape.

2. **[Critical] Implement the harness integration layer** — this is the entire point of Phase 3:
   - `deerflow/tools/builtins/knowledge_search_tool.py` — `knowledge_search(query, kb_ids)` calling the retriever
   - `AgentConfig.knowledge_base_ids: list[str] = []` field
   - `prompt.py:apply_prompt_template` — inject `<knowledge_context>` block (mirror the existing `memory_context` pattern)

3. **[High] Move document processing to a background task** using FastAPI `BackgroundTasks` or a task queue (Celery/ARQ). Return the document record immediately in `processing` state; update to `ready`/`error` asynchronously. The frontend already models this with the `status` field.

4. **[High] Add file size limit** to the upload endpoint (e.g. 50 MB). Check `file.size` or use a streaming read with a byte counter before processing.

5. **[High] Migrate to pgvector** for embeddings. Replace the `Text` embedding column with `pgvector.Vector(1536)`, add an HNSW or IVFFlat index, and replace the Python cosine loop in `retriever.py` with a single SQL `<=>` operator query. This is the plan's stated recommendation and is required for any real workload.

6. **[Medium] Add `useUpdateKnowledgeBase` hook** and a settings panel in `[id]/page.tsx` to expose chunk size, overlap, and embedding model editing.

7. **[Medium] Move `content_md` out of the DB** to object storage. Store only a reference path in `KnowledgeDocument`. This also enables document preview via a signed URL.

8. **[Medium] Support non-OpenAI embedding providers**. The `embedding_model` field should map to the harness model factory, not always call OpenAI directly.

9. **[Low] Add pagination** (`limit`/`offset` query params) to both list endpoints.

10. **[Low] Fix chunker overlap overrun** — remove the `* 1.2` multiplier or document it explicitly.
