# Multi-Tenant Implementation Contract

## Overview

Transform Allo (元枢) from single-user local dev to multi-tenant production system.
Scope: Sprint 0 + Sprint 1 + Sprint 2 (core multi-tenant functionality).

## Execution Phases

### Phase 1: Foundation (single worker)
- role: "foundation" — shared interface contracts, Alembic setup, DB models, Redis client, dependencies

### Phase 2: Parallel Implementation (3 workers)
- role: "a-backend" — Gateway API: auth, threads, PG stores, management APIs, nginx config
- role: "a-frontend" — Frontend: auth pages, thread hooks, middleware
- role: "b-harness" — Harness: paths, skills, memory, MCP, soul, make_lead_agent, store registry, sandbox paths, checkpointer

---

## File Ownership (STRICTLY NON-OVERLAPPING)

### foundation (Phase 1)
```
OWNS (creates new):
  backend/packages/harness/deerflow/stores.py
  backend/packages/harness/deerflow/context.py
  backend/packages/harness/deerflow/store_registry.py
  backend/alembic.ini
  backend/alembic/env.py
  backend/alembic/versions/001_baseline.py
  backend/alembic/versions/002_auth_tables.py
  backend/alembic/versions/003_add_user_id.py
  backend/alembic/versions/004_threads.py
  backend/alembic/versions/005_user_data.py
  backend/app/gateway/redis_client.py

MODIFIES:
  backend/pyproject.toml              — add alembic, redis[hiredis], bcrypt, httpx deps
  backend/app/gateway/db/models.py    — add User, Session, Thread, ThreadRun, UserMemory, UserMemoryFact, UserSoul, UserMcpConfig, UserAgent, UserApiKey models
  backend/app/gateway/app.py          — remove Base.metadata.create_all, add Redis shutdown hook
```

### a-backend (Phase 2)
```
OWNS (creates new):
  backend/app/gateway/routers/auth.py
  backend/app/gateway/routers/users.py
  backend/app/gateway/routers/threads.py
  backend/app/gateway/routers/soul.py
  backend/app/gateway/routers/api_keys.py
  backend/app/gateway/services/__init__.py
  backend/app/gateway/services/memory_store_pg.py
  backend/app/gateway/services/soul_store_pg.py
  backend/app/gateway/services/skill_config_store_pg.py
  backend/app/gateway/services/mcp_config_store_pg.py
  backend/app/gateway/services/model_key_resolver_pg.py
  backend/app/gateway/services/store_injection.py
  deploy/nginx/allo.conf

MODIFIES:
  backend/app/gateway/auth.py         — rewrite get_auth_context for cookie→Redis→PG flow
  backend/app/gateway/app.py          — register new routers (auth, users, threads, soul, api_keys), call store injection
  backend/app/gateway/routers/memory.py  — add user_id filtering
  backend/app/gateway/routers/mcp.py     — add user_id filtering
  backend/app/gateway/routers/agents.py  — add user_id filtering
  backend/app/gateway/routers/skills.py  — add user_id filtering
```

### a-frontend (Phase 2)
```
OWNS (creates new):
  frontend/src/core/auth/api.ts
  frontend/src/core/auth/index.ts
  frontend/src/core/threads/threads-api.ts

MODIFIES:
  frontend/src/app/(auth)/login/page.tsx     — switch to Gateway auth API
  frontend/src/app/(auth)/register/page.tsx  — switch to Gateway auth API (if exists, or create)
  frontend/src/middleware.ts                  — update cookie check logic
  frontend/src/core/threads/hooks.ts         — switch to Gateway thread API

DELETES:
  frontend/src/server/better-auth/           — entire directory
  frontend/src/app/api/auth/[...all]/route.ts — Better Auth catch-all route
```

### b-harness (Phase 2)
```
MODIFIES:
  backend/packages/harness/deerflow/config/paths.py                          — add user_dir, user_thread_dir, user_thread_tmp_dir, user_skills_dir
  backend/packages/harness/deerflow/skills/loader.py                         — add user_id param, per-user skill loading
  backend/packages/harness/deerflow/agents/memory/updater.py                 — accept MemoryStore, fallback to JSON
  backend/packages/harness/deerflow/mcp/cache.py                             — add user_id param, per-user cache key
  backend/packages/harness/deerflow/agents/lead_agent/agent.py               — integrate UserContext, stores, per-user loading
  backend/packages/harness/deerflow/agents/lead_agent/prompt.py              — accept soul/memory params for per-user injection
  backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py — per-user directory paths
  backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py   — pass user_id to MemoryUpdater
  backend/packages/harness/deerflow/sandbox/tools.py                         — per-user virtual path mapping
  backend/packages/harness/deerflow/agents/checkpointer/async_provider.py    — ensure postgres reads CHECKPOINT_POSTGRES_URI
  backend/packages/harness/deerflow/config/checkpointer_config.py            — update default config

DOES NOT MODIFY (created by foundation):
  backend/packages/harness/deerflow/stores.py        — READ ONLY, already created
  backend/packages/harness/deerflow/context.py       — READ ONLY, already created
  backend/packages/harness/deerflow/store_registry.py — READ ONLY, already created
```

---

## Shared Interfaces

### 1. Abstract Store Interfaces (stores.py)

```python
# backend/packages/harness/deerflow/stores.py
from abc import ABC, abstractmethod

class MemoryStore(ABC):
    @abstractmethod
    async def get_memory(self, user_id: str) -> dict: ...
    @abstractmethod
    async def save_memory(self, user_id: str, data: dict) -> None: ...
    @abstractmethod
    async def get_facts(self, user_id: str, limit: int = 15) -> list[dict]: ...

class SoulStore(ABC):
    @abstractmethod
    async def get_soul(self, user_id: str) -> str | None: ...

class SkillConfigStore(ABC):
    @abstractmethod
    async def get_skill_toggles(self, user_id: str) -> dict[str, bool]: ...

class McpConfigStore(ABC):
    @abstractmethod
    async def get_user_mcp_config(self, user_id: str) -> dict: ...

class ModelKeyResolver(ABC):
    @abstractmethod
    async def resolve_key(self, run_id: str) -> tuple[str, str | None]: ...
```

### 2. UserContext (context.py)

```python
# backend/packages/harness/deerflow/context.py
from dataclasses import dataclass

@dataclass(frozen=True)
class UserContext:
    user_id: str
    org_id: str
    run_id: str | None = None

def get_user_context(config: dict | None = None) -> UserContext | None:
    if not config:
        return None
    configurable = config.get("configurable", {})
    user_id = configurable.get("x-user-id") or configurable.get("user_id")
    org_id = configurable.get("x-org-id") or configurable.get("org_id", "default")
    run_id = configurable.get("run_id")
    if user_id:
        return UserContext(user_id=user_id, org_id=org_id, run_id=run_id)
    return None
```

### 3. Store Registry (store_registry.py)

```python
# backend/packages/harness/deerflow/store_registry.py
_stores: dict[str, object] = 

def register_store(name: str, impl: object) -> None:
    _stores[name] = impl

def get_store(name: str) -> object | None:
    return _stores.get(name)
```

### 4. AuthContext (existing, to be rewritten)

```python
# backend/app/gateway/auth.py
class AuthContext(BaseModel):
    user_id: str
    org_id: str
    role: str  # "admin" | "member"
```

---

## Integration Points

### A. Cookie-based Auth Flow
```
Browser → cookie "session_token" → Gateway auth.py:
  1. Read cookie
  2. Check Redis session:{token} → hit → return AuthContext
  3. Miss → query PG sessions table → valid → write Redis cache → return AuthContext
  4. Invalid → 401
```

### B. nginx auth_request → LangGraph
```
Browser → nginx /api/langgraph/* →
  auth_request /internal/auth-check →
    Gateway GET /api/auth/check →
      validate cookie → return X-User-Id, X-Org-Id headers
  → nginx injects X-User-Id, X-Org-Id → LangGraph:2024
  → config["configurable"]["x-user-id"] = X-User-Id
```

### C. Store Injection (Gateway → Harness)
```python
# backend/app/gateway/services/store_injection.py
# Called during Gateway app startup (in app.py lifespan)
from deerflow.store_registry import register_store

async def inject_stores(db_session_factory):
    register_store("memory", PostgresMemoryStore(db_session_factory))
    register_store("soul", PostgresSoulStore(db_session_factory))
    register_store("skill", PostgresSkillConfigStore(db_session_factory))
    register_store("mcp", PostgresMcpConfigStore(db_session_factory))
    register_store("key", PostgresModelKeyResolver(db_session_factory))
```

### D. Thread Lifecycle
```
Frontend createThread() → Gateway POST /api/threads →
  1. Create in LangGraph (POST http://127.0.0.1:2024/threads)
  2. Insert into PG threads table (with user_id, org_id)
  3. Create file directories: {base_dir}/users/{user_id}/threads/{thread_id}/user-data/{workspace,uploads,outputs,tmp}
  4. Return thread metadata

Frontend sendMessage() → Gateway POST /api/threads/{id}/runs →
  1. Insert thread_run record
  2. Resolve API key → write to Redis run:{run_id}:key
  3. Frontend streams directly to LangGraph via nginx (with auth_request)
```

### E. Per-User Data Flow in Harness
```
make_lead_agent(config) →
  ctx = get_user_context(config)
  user_id = ctx.user_id if ctx else None

  # Get stores from registry (injected by Gateway)
  memory_store = get_store("memory")
  soul_store = get_store("soul")
  ...

  # Load per-user data (or fallback to global)
  skills = load_skills(user_id=user_id, skill_config_store=skill_config_store)
  mcp_tools = get_cached_mcp_tools(user_id=user_id, mcp_config_store=mcp_config_store)
  soul = await soul_store.get_soul(user_id) if (soul_store and user_id) else default_soul()
  memory = await memory_store.get_memory(user_id) if (memory_store and user_id) else {}
```

---

## Redis Key Conventions

| Key Pattern | Writer | Reader | TTL | Content |
|---|---|---|---|---|
| `session:{token}` | a-backend | a-backend | 5min | AuthContext JSON |
| `run:{run_id}:key` | a-backend | b-harness (via ModelKeyResolver) | 5min | `{api_key, base_url}` JSON |
| `rate_limit:{user_id}` | a-backend | a-backend | 60s | Counter |

---

## File Path Conventions

```
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/workspace/   — read/write
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/uploads/     — read-only
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/outputs/     — read/write
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/tmp/         — read/write
{base_dir}/users/{user_id}/skills/custom/{skill_name}/                — user private skills

skills/public/{skill_name}/                                           — platform public (read-only)
```

Local dev: `base_dir` = `backend/.deer-flow`

Virtual path mapping (sandbox):
```
/mnt/user-data/workspace  → {base_dir}/users/{user_id}/threads/{thread_id}/user-data/workspace
/mnt/user-data/uploads    → ...uploads
/mnt/user-data/outputs    → ...outputs
/mnt/user-data/tmp        → ...tmp
/mnt/skills/public/...    → skills/public/...
/mnt/skills/custom/...    → {base_dir}/users/{user_id}/skills/custom/...
```

---

## Database Schema (All Tables)

### Existing tables (keep as-is):
- organizations, organization_members, tenant_configs
- knowledge_bases, knowledge_documents, knowledge_chunks
- usage_records, marketplace_tools, org_installed_tools
- marketplace_skills, org_installed_skills

### New tables (created by foundation worker):

```sql
-- 002_auth_tables.py
CREATE TABLE users (
    id            VARCHAR(36) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name  VARCHAR(255),
    avatar_url    VARCHAR(512),
    locale        VARCHAR(10) DEFAULT 'zh-CN',
    is_active     BOOLEAN DEFAULT true,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sessions (
    id         VARCHAR(36) PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_user ON sessions(user_id);

-- 004_threads.py
CREATE TABLE threads (
    id               VARCHAR(255) PRIMARY KEY,
    user_id          VARCHAR(36) NOT NULL,
    org_id           VARCHAR(36),
    title            VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    status           VARCHAR(32) NOT NULL DEFAULT 'active',
    agent_name       VARCHAR(255),
    default_model    VARCHAR(255),
    last_model_name  VARCHAR(255),
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now(),
    last_active_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_threads_user ON threads(user_id);
CREATE INDEX idx_threads_last_active ON threads(last_active_at);

CREATE TABLE thread_runs (
    id               VARCHAR(36) PRIMARY KEY,
    thread_id        VARCHAR(255) NOT NULL,
    user_id          VARCHAR(36) NOT NULL,
    org_id           VARCHAR(36),
    model_name       VARCHAR(255),
    agent_name       VARCHAR(255),
    sandbox_id       VARCHAR(255),
    status           VARCHAR(32) NOT NULL DEFAULT 'running',
    started_at       TIMESTAMPTZ DEFAULT now(),
    finished_at      TIMESTAMPTZ,
    error_message    TEXT
);
CREATE INDEX idx_thread_runs_thread ON thread_runs(thread_id);
CREATE INDEX idx_thread_runs_user ON thread_runs(user_id);

-- 005_user_data.py
CREATE TABLE user_memory (
    id           VARCHAR(36) PRIMARY KEY,
    user_id      VARCHAR(36) NOT NULL,
    org_id       VARCHAR(36),
    context_json TEXT NOT NULL DEFAULT '{}',
    updated_at   TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX idx_user_memory_user ON user_memory(user_id);

CREATE TABLE user_memory_facts (
    id         VARCHAR(36) PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL,
    memory_id  VARCHAR(36) REFERENCES user_memory(id) ON DELETE CASCADE,
    content    TEXT NOT NULL,
    category   VARCHAR(50) DEFAULT 'context',
    confidence FLOAT DEFAULT 0.5,
    source     VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_user_memory_facts_user ON user_memory_facts(user_id);

CREATE TABLE user_souls (
    id         VARCHAR(36) PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL,
    org_id     VARCHAR(36),
    content    TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX idx_user_souls_user ON user_souls(user_id);

CREATE TABLE user_mcp_configs (
    id          VARCHAR(36) PRIMARY KEY,
    user_id     VARCHAR(36) NOT NULL,
    org_id      VARCHAR(36),
    config_json TEXT NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX idx_user_mcp_configs_user ON user_mcp_configs(user_id);

CREATE TABLE user_agents (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    org_id          VARCHAR(36),
    name            VARCHAR(255) NOT NULL,
    description     TEXT DEFAULT '',
    model           VARCHAR(255),
    tool_groups_json TEXT DEFAULT '[]',
    soul_content    TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_user_agents_user ON user_agents(user_id);

CREATE TABLE user_api_keys (
    id          VARCHAR(36) PRIMARY KEY,
    user_id     VARCHAR(36) NOT NULL,
    org_id      VARCHAR(36),
    provider    VARCHAR(100) NOT NULL,
    api_key_enc TEXT NOT NULL,
    base_url    VARCHAR(512),
    is_active   BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX idx_user_api_keys_user_provider ON user_api_keys(user_id, provider);
```

---

## Naming Conventions

### Python (Backend)
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case()`
- Constants: `UPPER_SNAKE_CASE`
- Line length: 240

### TypeScript (Frontend)
- Files: `kebab-case.tsx` / `kebab-case.ts`
- Components: `PascalCase`
- Functions: `camelCase()`
- Hooks: `use` prefix
- Inline type imports: `import { type Foo }`

### API Endpoints
- All under `/api/` prefix
- RESTful: `GET /api/threads`, `POST /api/threads`, `PATCH /api/threads/{id}`
- Auth: `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/session`, `/api/auth/check`

---

## Critical Constraints

1. **Backward Compatibility**: All harness changes MUST add `if user_id` branches. Without user_id, fall back to existing global behavior. `make dev` MUST continue to work.

2. **Architecture Boundary**: `deerflow.*` (harness) NEVER imports `app.*` (gateway). Direction is always `app → deerflow`.

3. **Store Injection**: Harness gets store implementations via `store_registry.get_store()`. Gateway injects them at startup via `register_store()`.

4. **Cookie Name**: Change from `better-auth.session_token` to `session_token` (simpler, no dependency on Better Auth).

5. **Session Token**: `secrets.token_urlsafe(32)`, stored in PG + cached in Redis.

6. **Password Hashing**: `bcrypt` with default rounds.

7. **LangGraph SDK Streaming**: Frontend continues to stream directly to LangGraph via nginx. Only thread management CRUD goes through Gateway.

8. **Config file**: `config.example.yaml` checkpointer section should document postgres option with `CHECKPOINT_POSTGRES_URI` env var.
