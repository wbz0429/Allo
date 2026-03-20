# Code Review Contract — DeerFlow B2B SaaS Plan Implementation

## Purpose
Each worker reviews one module's implementation against the plan in `.dfcode/plans/1773904984543-neon-wizard.md`.
Workers produce a **review report only** — no code changes.

## Output Format (MANDATORY for all workers)
Each worker writes its report to the path specified in its role section below.

Report structure:
```
# CR Report: <Module Name>

## Summary
One paragraph overall assessment.

## Files Reviewed
List of files actually read.

## Plan vs Implementation Gap Analysis
| Plan Requirement | Status | Notes |
|---|---|---|
| ... | ✅ Implemented / ⚠️ Partial / ❌ Missing | ... |

## Code Quality Issues
- Issue description, file:line if applicable

## Security / Architecture Concerns
- Any concerns

## Recommendations
- Prioritized list of improvements
```

---

## Roles

### Role: auth
- Owner: review auth + multi-tenant module (Phase 1)
- Report output: `.dfcode/reports/cr-auth.md`
- Key files to review:
  - `backend/app/gateway/auth.py`
  - `backend/app/gateway/db/models.py`
  - `backend/app/gateway/db/database.py`
  - `frontend/src/server/better-auth/` (all files)
  - `frontend/src/app/(auth)/` (login, register pages)
  - `frontend/src/app/api/auth/[...all]/route.ts`
  - `frontend/src/middleware.ts`
  - All routers in `backend/app/gateway/routers/` — check org_id isolation
- Plan section: Module A (Section 3.2, Phase 1 in Section 3.6)

### Role: config
- Owner: review config wizard + setup UI (Phase 2)
- Report output: `.dfcode/reports/cr-config.md`
- Key files to review:
  - `backend/app/gateway/routers/config.py`
  - `backend/app/gateway/config.py`
  - `frontend/src/app/workspace/setup/` (all files)
  - `frontend/src/components/workspace/setup-wizard/` (all files)
  - `frontend/src/core/config/` (api.ts, hooks.ts, types.ts)
- Plan section: Module B (Section 3.2, Phase 2 in Section 3.6)

### Role: rag
- Owner: review knowledge base + RAG pipeline (Phase 3)
- Report output: `.dfcode/reports/cr-rag.md`
- Key files to review:
  - `backend/app/gateway/rag/chunker.py`
  - `backend/app/gateway/rag/embedder.py`
  - `backend/app/gateway/rag/retriever.py`
  - `backend/app/gateway/routers/knowledge_bases.py`
  - `backend/app/gateway/db/models.py` (KnowledgeBase, KnowledgeDocument, KnowledgeChunk models)
  - `frontend/src/app/workspace/knowledge/` (all files)
  - `frontend/src/components/workspace/knowledge/` (all files)
  - `frontend/src/core/knowledge/` (api.ts, hooks.ts, types.ts)
- Plan section: Module C (Section 3.2, Phase 3 in Section 3.6)

### Role: admin
- Owner: review admin dashboard + usage tracking + rate limiting (Phase 4)
- Report output: `.dfcode/reports/cr-admin.md`
- Key files to review:
  - `backend/app/gateway/routers/admin.py`
  - `backend/app/gateway/middleware/usage_tracking.py`
  - `backend/app/gateway/middleware/rate_limiter.py`
  - `backend/app/gateway/db/models.py` (UsageRecord model)
  - `frontend/src/app/admin/` (all files)
  - `frontend/src/components/admin/` (all files)
  - `frontend/src/core/admin/` (api.ts, types.ts)
  - `frontend/src/core/org/` (api.ts, types.ts)
- Plan section: Module E (Section 3.2, Phase 4 in Section 3.6)

### Role: marketplace
- Owner: review marketplace / ecosystem (Phase 5)
- Report output: `.dfcode/reports/cr-marketplace.md`
- Key files to review:
  - `backend/app/gateway/routers/marketplace.py`
  - `backend/app/gateway/marketplace_seed.py`
  - `backend/app/gateway/db/models.py` (MarketplaceTool, MarketplaceSkill, OrgInstalledTool, OrgInstalledSkill)
  - `frontend/src/app/workspace/marketplace/` (all files)
  - `frontend/src/components/workspace/marketplace/` (all files)
  - `frontend/src/core/marketplace/` (api.ts, types.ts)
- Plan section: Phase 5 (Section 3.6)

---

## Shared Context
- Plan file: `/Users/wbz/deer-flow/.dfcode/plans/1773904984543-neon-wizard.md`
- Architecture boundary: `deerflow.*` (harness) must NEVER import `app.*`
- Auth pattern: every router must use `Depends(get_auth_context)` and filter by `org_id`
- Frontend pattern: each feature module has `core/<module>/{api,hooks,types}.ts`
- Code style: see `/Users/wbz/deer-flow/AGENTS.md`
- No tests needed — review only
