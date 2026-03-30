# Allo Multi-Tenant Implementation Contract

## Overview

Transform Allo from single-user local dev to multi-user multi-tenant system.
Sprint 1 (infrastructure + auth + harness foundation) and Sprint 2 (data isolation + thread management + frontend).

## Shared Contracts (already committed)

- `backend/packages/harness/deerflow/stores.py` — Abstract store interfaces (MemoryStore, SoulStore, SkillConfigStore, McpConfigStore, ModelKeyResolver)
- `backend/packages/harness/deerflow/context.py` — UserContext dataclass + get_user_context()
- `backend/packages/harness/deerflow/store_registry.py` — Global store registry (register_store / get_store)

## Runtime Context Fields

```
nginx-injected headers → config["configurable"]:
  x-user-id: str
  x-org-id: str

Frontend-passed fields:
  thread_id, run_id, model_name, agent_name,
  thinking_enabled, is_plan_mode, subagent_enabled
```

## Redis Key Conventions

```
session:{token}       → AuthContext JSON, TTL 5min    (A writes, A reads)
run:{run_id}:key      → {api_key, base_url} JSON, TTL 5min  (A writes, B reads)
rate_limit:{user_id}  → counter, TTL 60s              (A writes, A reads)
```

## File Path Conventions

```
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/workspace/
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/uploads/
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/outputs/
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/tmp/
{base_dir}/users/{user_id}/skills/custom/{skill_name}/
```

Local dev: base_dir = `backend/.deer-flow`

## Database Tables

### Auth (A-sprint1)
- `users` — id(VARCHAR36 PK), email(UNIQUE), password_hash, display_name, avatar_url, locale, is_active, created_at, updated_at
- `sessions` — id(VARCHAR36 PK), user_id(FK users), token(UNIQUE), expires_at, created_at

### Threads (A-sprint2)
- `threads` — id(VARCHAR255 PK), user_id, org_id, title, status, agent_name, default_model, last_model_name, created_at, updated_at, last_active_at
- `thread_runs` — id(VARCHAR36 PK), thread_id, user_id, org_id, model_name, agent_name, sandbox_id, status, started_at, finished_at, error_message

### User Data (A-sprint2)
- `user_memory` — id, user_id, org_id, context_json, updated_at
- `user_memory_facts` — id, user_id, memory_id, content, category, confidence, source, created_at
- `user_souls` — id, user_id, org_id, content, updated_at
- `user_mcp_configs` — id, user_id, org_id, config_json, updated_at
- `user_agents` — id, user_id, org_id, name, description, model, tool_groups_json, soul_content, created_at, updated_at
- `user_api_keys` — id, user_id, org_id, provider, api_key_enc, base_url, is_active, created_at, updated_at

---

## Execution Phases

### Phase 1: Sprint 1 (parallel)

#### Role: a-sprint1 (worker-backend)
**Owner:** `backend/app/gateway/` (all files), `backend/alembic/`, `backend/pyproject.toml`, `deploy/`

Tasks:
1. **A-1 Alembic Init**: Create `backend/alembic.ini`, `backend/alembic/env.py`, generate `001_baseline.py` from existing models. Modify `app.py` to remove `Base.metadata.create_all`.
2. **A-2 Auth Tables**: Create migration `002_auth_tables.py` (users + sessions). Add User, Session models to `db/models.py`.
3. **A-3 Redis Client**: Create `backend/app/gateway/redis_client.py` (get_redis, close_redis_pool). Modify `app.py` lifespan for Redis shutdown. Add `redis[hiredis]>=5.0`, `bcrypt>=4.0` to `pyproject.toml`.
4. **A-4 Auth API**: Create `backend/app/gateway/routers/auth.py` (register, login, logout, session, check endpoints). Rewrite `auth.py` get_auth_context to use cookie→Redis→PG flow. Register auth router in `app.py`.
5. **A-5 Users API**: Create `backend/app/gateway/routers/users.py` (GET/PUT /api/users/me). Register in `app.py`.
6. **A-11 nginx config**: Create `deploy/nginx/allo.conf` with auth_request for LangGraph proxy.

Files this role MUST NOT touch:
- `backend/packages/harness/deerflow/` (B's territory)
- `frontend/` (frontend workers' territory)

#### Role: b-sprint1 (worker-backend)
**Owner:** `backend/packages/harness/deerflow/` (all files except stores.py, context.py, store_registry.py which are already committed)

Tasks:
1. **B-2 File Paths**: Modify `config/paths.py` — add user_dir(), user_thread_dir(), user_thread_tmp_dir(), user_skills_dir() methods to Paths class. Add ensure_user_thread_dirs() method. All new methods, no breaking changes.
2. **B-3 Skills Loader**: Modify `skills/loader.py` — change load_skills() signature to accept optional user_id and skill_config_store params. When user_id provided: load public + user custom skills + apply DB toggles. When None: existing behavior unchanged.
3. **B-4 Memory Interface**: Modify `agents/memory/updater.py` — make MemoryUpdater accept optional MemoryStore. When provided: use store for read/write. When None: existing JSON file behavior.
4. **B-5 MCP Cache**: Modify `mcp/cache.py` — change get_cached_mcp_tools() to accept optional user_id and mcp_config_store. Per-user cache key. Fallback to global when no user_id.
5. **B-11 Checkpointer**: Modify `agents/checkpointer/async_provider.py` — ensure postgres type reads CHECKPOINT_POSTGRES_URI env var.

Files this role MUST NOT touch:
- `backend/app/gateway/` (A's territory)
- `frontend/` (frontend workers' territory)

**Critical Rule for B:** ALL changes must be backward-compatible. When user_id is None or stores are not registered, behavior MUST be identical to current code. `make dev` must continue to work.

---

### Phase 2: Sprint 2 (parallel, after Phase 1 merge)

#### Role: a-sprint2 (worker-backend)
**Owner:** `backend/app/gateway/` (all files), `backend/alembic/`

Tasks:
1. **Thread Tables**: Create migration `004_threads.py` (threads + thread_runs tables). Add Thread, ThreadRun models to `db/models.py`.
2. **Thread CRUD API**: Create `backend/app/gateway/routers/threads.py` — POST/GET/PATCH/DELETE /api/threads, POST/PATCH thread runs. Use httpx.AsyncClient to call LangGraph:2024 internally.
3. **User Data Tables**: Create migration `005_user_data.py` (user_memory, user_memory_facts, user_souls, user_mcp_configs, user_agents, user_api_keys). Add models.
4. **PG Store Implementations**: Create `backend/app/gateway/services/memory_store_pg.py`, `soul_store_pg.py`, `skill_config_store_pg.py`, `mcp_config_store_pg.py`, `model_key_resolver_pg.py` — implement abstract interfaces from `deerflow.stores`.
5. **Management APIs**: Create `routers/soul.py` (GET/PUT /api/users/me/soul), `routers/api_keys.py` (CRUD for BYOK). Modify existing `routers/memory.py`, `routers/mcp.py`, `routers/agents.py`, `routers/skills.py` to filter by user_id.
6. **Register new routers** in `app.py`. Register PG stores via `deerflow.store_registry.register_store()` in app lifespan.

Files this role MUST NOT touch:
- `backend/packages/harness/deerflow/` (B's territory)
- `frontend/` (frontend workers' territory)

#### Role: b-sprint2 (worker-backend)
**Owner:** `backend/packages/harness/deerflow/agents/`, `backend/packages/harness/deerflow/sandbox/tools.py`

Tasks:
1. **B-6 Soul Loading**: Modify `agents/lead_agent/prompt.py` — change get_agent_soul() and _get_memory_context() to accept optional stores and user_id. Load from SoulStore/MemoryStore when available, fallback to file-based.
2. **B-7 make_lead_agent**: Modify `agents/lead_agent/agent.py` — extract UserContext from config, get stores from registry, pass user_id to load_skills/load_memory/load_soul/get_mcp_tools. Fallback to current behavior when no user_id.
3. **B-8 ThreadData Middleware**: Modify `agents/middlewares/thread_data_middleware.py` — read user_id from runtime.context, create per-user directory structure when user_id present.
4. **B-9 Virtual Path Mapping**: Modify `sandbox/tools.py` — update replace_virtual_path() and related functions to support per-user paths. Add /mnt/skills/custom/* mapping. Add cross-user path traversal prevention.

Files this role MUST NOT touch:
- `backend/app/gateway/` (A's territory)
- `frontend/` (frontend workers' territory)
- `backend/packages/harness/deerflow/config/paths.py` (already modified in Phase 1)
- `backend/packages/harness/deerflow/skills/loader.py` (already modified in Phase 1)
- `backend/packages/harness/deerflow/agents/memory/updater.py` (already modified in Phase 1)
- `backend/packages/harness/deerflow/mcp/cache.py` (already modified in Phase 1)

#### Role: a-frontend-auth (worker-frontend)
**Owner:** `frontend/src/core/auth/`, `frontend/src/app/(auth)/`, `frontend/src/middleware.ts`, `frontend/src/server/`

Tasks:
1. **Delete** `frontend/src/server/better-auth/` directory entirely
2. **Delete** `frontend/src/app/api/auth/[...all]/route.ts` if it exists
3. **Create** `frontend/src/core/auth/api.ts` — register(), login(), logout(), getSession() calling Gateway /api/auth/* endpoints
4. **Modify** `frontend/src/app/(auth)/login/page.tsx` — replace Better Auth calls with Gateway auth API
5. **Modify** `frontend/src/app/(auth)/register/page.tsx` — replace Better Auth calls with Gateway auth API
6. **Modify** `frontend/src/middleware.ts` — change cookie name from "better-auth.session_token" to "session_token", keep redirect logic

Files this role MUST NOT touch:
- `backend/` (backend workers' territory)
- `frontend/src/core/threads/` (threads frontend worker's territory)

#### Role: a-frontend-threads (worker-frontend)
**Owner:** `frontend/src/core/threads/`

Tasks:
1. **Create** `frontend/src/core/threads/threads-api.ts` — createThread(), listThreads(), deleteThread(), updateThread(), createThreadRun(), updateThreadRun() calling Gateway /api/threads/* endpoints
2. **Modify** `frontend/src/core/threads/hooks.ts` — useThreads() calls Gateway GET /api/threads, useDeleteThread() calls Gateway DELETE, useRenameThread() calls Gateway PATCH. Modify sendMessage flow to create thread + thread_run via Gateway before submitting to LangGraph. Add onUpdateEvent title sync and onFinish run status update.

Files this role MUST NOT touch:
- `backend/` (backend workers' territory)
- `frontend/src/core/auth/` (auth frontend worker's territory)
- `frontend/src/app/(auth)/` (auth frontend worker's territory)

---

## Integration Points

### Cookie Convention
- Cookie name: `session_token` (replacing `better-auth.session_token`)
- Format: `session_token={token}; HttpOnly; Path=/; SameSite=Lax; Max-Age=604800`
- Both backend auth.py and frontend middleware.ts must use this name

### Gateway → LangGraph Proxy
- Gateway threads router uses `httpx.AsyncClient("http://127.0.0.1:2024")` to call LangGraph
- nginx auth_request at `/internal/auth-check` calls Gateway `/api/auth/check`
- Gateway check endpoint returns X-User-Id and X-Org-Id headers

### Store Registration (app.py lifespan)
```python
from deerflow.store_registry import register_store
# After DB init, register PG store implementations
register_store("memory", PostgresMemoryStore(async_session_factory))
register_store("soul", PostgresSoulStore(async_session_factory))
register_store("skill", PostgresSkillConfigStore(async_session_factory))
register_store("mcp", PostgresMcpConfigStore(async_session_factory))
register_store("key", PostgresModelKeyResolver(async_session_factory, get_redis))
```

### Frontend API Base
- All frontend API calls use relative paths (e.g. `/api/auth/login`, `/api/threads`)
- Credentials: `credentials: "include"` for cookie-based auth
- LangGraph streaming continues to use SDK directly (not through Gateway)

## Naming Conventions

- Python files: snake_case
- Migration files: `NNN_description.py` (e.g. `002_auth_tables.py`)
- Router files: match resource name (e.g. `auth.py`, `threads.py`, `users.py`)
- Service files: `{resource}_store_pg.py` (e.g. `memory_store_pg.py`)
- Frontend API files: `api.ts` in feature directory
- TypeScript: camelCase functions, PascalCase types

## Error Handling

- Backend routers: raise HTTPException with appropriate status codes
- Auth failures: 401 Unauthorized
- Ownership violations: 403 Forbidden
- Not found: 404
- Frontend: toast.error() for user-facing errors, console.error() for unexpected
