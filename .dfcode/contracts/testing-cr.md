# Testing & Code Review Contract — DeerFlow B2B SaaS (Phases 1-5)

## Objective
Write comprehensive tests for all new B2B SaaS code (Phases 1-5) and fix existing broken tests. Tests should expose bugs in the implementation.

## Known Issues to Verify via Tests

### Backend Issues
1. **test_custom_agent.py broken** — 19 tests fail with 401 because auth middleware was added but tests don't set SKIP_AUTH=1. Fix: set `SKIP_AUTH=1` env var in conftest.py or per-test.
2. **Config router not registered** — `routers/config.py` exists but is NOT included in `app.py` `create_app()`. Write a test that verifies all routers are registered.
3. **Admin/marketplace routers missing** — No router files exist at `routers/admin.py` or `routers/marketplace.py` despite git commits. Write tests that attempt to import them (will fail, exposing the bug).
4. **Middleware not registered** — `UsageTrackingMiddleware` and `RateLimiterMiddleware` are not added to the FastAPI app. Write tests to verify.
5. **routers/__init__.py outdated** — Only exports 6 routers, missing agents, channels, knowledge_bases, config.
6. **22 lint errors** — Fix import sorting and unused imports in test files.

### Frontend Issues (report only, don't fix)
1. Missing setup wizard components: `agent-setup-step.tsx`, `completion-step.tsx`, `tool-selection-step.tsx`
2. `fetchOptions` type error in `src/core/api/api-client.ts`
3. Missing `pg` type declarations in `src/server/better-auth/config.ts`

## Roles & File Ownership

### Role: backend-test-unit
**Agent**: worker-tests
**Owns**: `backend/tests/test_rag_chunker.py`, `backend/tests/test_rag_retriever.py`, `backend/tests/test_rate_limiter.py`, `backend/tests/test_usage_tracking.py`, `backend/tests/test_new_db_models.py`, `backend/tests/test_templates.py`, `backend/tests/test_marketplace_seed.py`

Tasks:
1. Write unit tests for RAG chunker (`app.gateway.rag.chunker`):
   - `chunk_markdown()` with empty input, short text, long text, multiple headers
   - `_split_by_headers()` edge cases
   - `_split_by_size()` with various chunk sizes and overlaps
   - Validation errors (negative chunk_size, overlap >= size)

2. Write unit tests for RAG retriever (`app.gateway.rag.retriever`):
   - `_cosine_similarity()` with identical vectors, orthogonal vectors, zero vectors, different lengths
   - `search_chunks()` with mocked DB session — empty results, sorted results, invalid embeddings

3. Write unit tests for rate limiter (`app.gateway.middleware.rate_limiter`):
   - `TokenBucket` — consume tokens, refill over time, exhaustion, retry_after calculation
   - `RateLimiterMiddleware` — skip paths, no org_id passthrough, rate limit rejection (429)

4. Write unit tests for usage tracking (`app.gateway.middleware.usage_tracking`):
   - `UsageTrackingMiddleware` — skip paths, no auth state passthrough, record creation
   - `set_request_auth_state()` helper

5. Write unit tests for new DB models (TenantConfig, KnowledgeBase, KnowledgeDocument, KnowledgeChunk, UsageRecord, MarketplaceTool, OrgInstalledTool, MarketplaceSkill, OrgInstalledSkill):
   - Creation with defaults, custom values, repr, tablename, columns, foreign keys, constraints

6. Write unit tests for agent templates (`app.gateway.templates`):
   - AGENT_TEMPLATES structure validation, AGENT_TEMPLATES_BY_ID lookup

7. Write unit tests for marketplace seed data (`app.gateway.marketplace_seed`):
   - SEED_TOOLS and SEED_SKILLS structure validation, JSON parsing of mcp_config_json

### Role: backend-test-integration
**Agent**: worker-tests
**Owns**: `backend/tests/test_app_registration.py`, `backend/tests/test_config_router.py`, `backend/tests/test_kb_router.py`, `backend/tests/conftest.py` (only add SKIP_AUTH fixture, don't remove existing content)

Tasks:
1. **Fix conftest.py**: Add `os.environ["SKIP_AUTH"] = "1"` at the top of conftest.py (BEFORE any app imports) so all existing tests pass. This is critical — the auth module reads SKIP_AUTH at import time.

2. **Fix lint errors**: The test files have import sorting issues. Ensure new test files have properly sorted imports.

3. Write `test_app_registration.py` — tests that verify the FastAPI app is correctly configured:
   - All expected routers are registered (check route paths exist): `/api/models`, `/api/mcp`, `/api/memory`, `/api/skills`, `/api/agents`, `/api/config`, `/api/knowledge-bases`, `/health`
   - Test that `/api/config` routes exist (will FAIL — exposing the missing config router registration bug)
   - Test that config router, admin router, marketplace router are importable (admin/marketplace will FAIL — exposing missing files)
   - Verify health endpoint has no auth dependency

4. Write `test_config_router.py` — tests for the config API:
   - GET /api/config — returns merged config (mock DB + mock get_app_config)
   - PUT /api/config — partial update works
   - POST /api/config/import — YAML and JSON import
   - GET /api/config/export — YAML export
   - GET /api/config/models — list base models
   - PUT /api/config/models — update model config
   - GET /api/config/tools — list tool groups
   - PUT /api/config/tools — update tool config
   - Use httpx.AsyncClient with the FastAPI test app, mock DB session

5. Write `test_kb_router.py` — tests for knowledge base API:
   - POST /api/knowledge-bases — create KB
   - GET /api/knowledge-bases — list KBs (org-scoped)
   - GET /api/knowledge-bases/{id} — get single KB
   - PUT /api/knowledge-bases/{id} — update KB
   - DELETE /api/knowledge-bases/{id} — delete KB
   - POST /api/knowledge-bases/{id}/documents — upload document (mock embedder)
   - GET /api/knowledge-bases/{id}/documents — list documents
   - DELETE /api/knowledge-bases/{id}/documents/{doc_id} — delete document
   - POST /api/knowledge-bases/{id}/search — search (mock embedder)
   - Use httpx.AsyncClient with the FastAPI test app, mock DB session and embedder

## Test Patterns

All tests should follow existing patterns in the codebase:
- Use `pytest` with `pytest.mark.asyncio` for async tests
- Use `unittest.mock.patch`, `MagicMock`, `AsyncMock` for mocking
- Use `httpx.AsyncClient` with `ASGITransport` for API tests (see test_custom_agent.py pattern)
- Import from `app.gateway.*` (not `deerflow.*` for app-layer code)
- Test file naming: `test_<feature>.py`
- Test function naming: `test_<description>()`
- Google-style docstrings for test classes
- Run from backend/ with: `PYTHONPATH=. uv run pytest tests/<file> -v`

## Important Notes

- **SKIP_AUTH must be set BEFORE importing app modules** — the auth module reads `os.getenv("SKIP_AUTH")` at module load time
- **Do NOT modify source code** — only write/fix test files
- **Mock external dependencies** — DB sessions, OpenAI API, file system where needed
- **Use SQLite in-memory for DB model tests** — don't require PostgreSQL
- **Tests that expose bugs should be marked with comments** like `# BUG: this test exposes missing router registration`
- **All tests must be runnable** with `PYTHONPATH=. uv run pytest tests/<file> -v` from backend/

## Verification

After all tests are written, run:
```bash
cd backend && PYTHONPATH=. uv run pytest tests/ -v --tb=short
```

Expected: All NEW tests pass (except those intentionally exposing bugs, which should be clearly commented). All EXISTING tests that were previously failing due to auth should now pass.
