# Phase 1 Contract: Multi-Tenant Auth + Data Isolation

## Overview
Implement user authentication, multi-tenant data isolation, and CORS hardening for the DeerFlow enterprise SaaS product.

## Execution Phases

### Phase A (parallel)
- role: "backend" — DB models, auth middleware, router isolation, nginx, tests
- role: "frontend" — Better Auth config, login/register pages, middleware, API client auth

### Phase B (after Phase A merge)
- role: "integration-tests" — End-to-end auth flow tests

---

## Shared Interfaces

### Auth Session Cookie
- Better Auth manages sessions via HTTP-only cookies
- Cookie name: `better-auth.session_token` (Better Auth default)
- Backend must validate sessions by calling Better Auth's session verification endpoint or by sharing the same DB

### Auth API Endpoints (handled by Better Auth via Next.js)
```
POST /api/auth/sign-up/email     # Register with email+password
POST /api/auth/sign-in/email     # Login with email+password  
POST /api/auth/sign-out          # Logout
GET  /api/auth/get-session       # Get current session
```

### Backend Auth Context (injected via FastAPI Depends)
```python
# app/gateway/auth.py
from pydantic import BaseModel

class AuthContext(BaseModel):
    user_id: str
    org_id: str
    role: str  # "admin" | "member"

async def get_auth_context(request: Request) -> AuthContext:
    """Extract auth context from session cookie or API key header.
    For Phase 1: validate session token against the auth DB.
    Returns AuthContext or raises HTTPException(401).
    """
    ...

# Optional: skip auth for specific routes
async def get_optional_auth_context(request: Request) -> AuthContext | None:
    """Same as above but returns None instead of 401."""
    ...
```

### Database Schema (PostgreSQL via SQLAlchemy)
```python
# app/gateway/db/models.py

class Organization(Base):
    __tablename__ = "organizations"
    id: str  # UUID
    name: str
    slug: str  # unique, URL-safe
    created_at: datetime
    updated_at: datetime

class OrganizationMember(Base):
    __tablename__ = "organization_members"
    id: str  # UUID
    org_id: str  # FK -> organizations.id
    user_id: str  # FK -> better-auth user table
    role: str  # "admin" | "member"
    created_at: datetime

# Better Auth manages its own user/session/account tables.
# We only add Organization and OrganizationMember.
```

### Database Connection
```python
# app/gateway/db/database.py
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/deerflow")

# Provide:
# - async engine (for FastAPI)
# - async session factory
# - get_db_session() dependency for routers
```

### Router Auth Pattern (all routers must follow)
```python
from app.gateway.auth import AuthContext, get_auth_context

@router.get("/api/agents")
async def list_agents(auth: AuthContext = Depends(get_auth_context)):
    # Use auth.org_id to filter data
    # Use auth.user_id for user-specific data
    ...
```

### Nginx CORS Changes
```nginx
# Replace: Access-Control-Allow-Origin: *
# With:
add_header Access-Control-Allow-Origin $http_origin always;
add_header Access-Control-Allow-Credentials true always;
add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-API-Key" always;
```

### Frontend Auth Pattern
```typescript
// All fetch() calls must include credentials
fetch(url, { credentials: "include", ...options })

// LangGraph SDK client must also forward cookies
// via custom fetch wrapper
```

---

## Role: backend

### Owned Files (create or modify)
- `backend/app/gateway/db/` (NEW directory)
  - `__init__.py`
  - `database.py` — async engine, session factory, `get_db_session()` dependency
  - `models.py` — Organization, OrganizationMember SQLAlchemy models
- `backend/app/gateway/auth.py` (NEW) — AuthContext, get_auth_context, get_optional_auth_context
- `backend/app/gateway/app.py` (MODIFY) — add DB lifespan, auth dependency
- `backend/app/gateway/routers/agents.py` (MODIFY) — add auth
- `backend/app/gateway/routers/models.py` (MODIFY) — add auth
- `backend/app/gateway/routers/mcp.py` (MODIFY) — add auth
- `backend/app/gateway/routers/memory.py` (MODIFY) — add auth
- `backend/app/gateway/routers/skills.py` (MODIFY) — add auth
- `backend/app/gateway/routers/artifacts.py` (MODIFY) — add auth
- `backend/app/gateway/routers/uploads.py` (MODIFY) — add auth
- `backend/app/gateway/routers/suggestions.py` (MODIFY) — add auth
- `backend/app/gateway/routers/channels.py` (MODIFY) — add auth (optional auth for IM)
- `backend/pyproject.toml` (MODIFY) — add sqlalchemy, asyncpg, alembic deps
- `backend/tests/test_auth.py` (NEW) — auth middleware tests
- `backend/tests/test_db_models.py` (NEW) — DB model tests
- `backend/tests/test_router_auth.py` (NEW) — router auth integration tests
- `docker/nginx/nginx.local.conf` (MODIFY) — CORS hardening
- `docker/nginx/nginx.conf` (MODIFY) — CORS hardening

### Must Do
- Use SQLAlchemy 2.0 async API with asyncpg driver
- All new code must have unit tests (pytest)
- Auth middleware must support both session cookies AND API key header (`X-API-Key` or `Authorization: Bearer df-...`)
- Routers that currently work without auth should still work in dev mode with an env flag `SKIP_AUTH=1` for backward compatibility
- Follow existing code style: ruff formatting, Google docstrings, snake_case
- Organization data isolation: every query that returns tenant-specific data must filter by org_id
- Health endpoint (`/health`) must remain unauthenticated
- Tests must be runnable with: `PYTHONPATH=. uv run pytest tests/test_auth.py tests/test_db_models.py tests/test_router_auth.py -v`

### Must NOT Do
- Do NOT modify any files in `packages/harness/deerflow/` — harness is off-limits
- Do NOT modify frontend files
- Do NOT add actual database migration files (Alembic setup is Phase 2 scope)
- Do NOT implement billing or usage tracking
- Do NOT change the LangGraph Server auth (out of scope for Phase 1)

---

## Role: frontend

### Owned Files (create or modify)
- `frontend/src/server/better-auth/config.ts` (MODIFY) — add PostgreSQL database adapter
- `frontend/src/server/better-auth/client.ts` (MODIFY) — configure auth client
- `frontend/src/server/better-auth/server.ts` (MODIFY) — enhance getSession
- `frontend/src/app/(auth)/` (NEW directory)
  - `login/page.tsx` — login page with email/password form
  - `register/page.tsx` — register page with email/password + org name
  - `layout.tsx` — auth pages layout (centered card)
- `frontend/src/middleware.ts` (NEW) — Next.js middleware for route protection
- `frontend/src/core/api/api-client.ts` (MODIFY) — add credentials: "include"
- `frontend/src/core/agents/api.ts` (MODIFY) — add credentials: "include"
- `frontend/src/core/models/api.ts` (MODIFY) — add credentials: "include"
- `frontend/src/core/skills/api.ts` (MODIFY) — add credentials: "include"
- `frontend/src/core/mcp/api.ts` (MODIFY) — add credentials: "include"
- `frontend/src/core/memory/api.ts` (MODIFY) — add credentials: "include"
- `frontend/src/core/uploads/api.ts` (MODIFY) — add credentials: "include"
- `frontend/src/components/workspace/workspace-sidebar.tsx` (MODIFY) — add logout button
- `frontend/package.json` (MODIFY) — add better-auth pg adapter dep if needed
- `frontend/src/env.js` (MODIFY) — add DATABASE_URL env var

### Must Do
- Login page: email + password form, error handling, redirect to /workspace on success
- Register page: email + password + organization name, creates user + org
- Use existing UI patterns: Shadcn components, cn() for classnames, Tailwind CSS
- middleware.ts: protect /workspace/* routes, redirect to /login if no session
- All fetch() calls must include `credentials: "include"` for cookie forwarding
- LangGraph SDK client must use a custom fetch that includes credentials
- Add a user menu or logout button in the workspace sidebar
- Follow existing code style: kebab-case files, PascalCase components, camelCase functions
- Use `"use client"` directive only for components with hooks/state
- Better Auth config must use PostgreSQL adapter with `DATABASE_URL` env var

### Must NOT Do
- Do NOT modify any backend Python files
- Do NOT modify nginx configs
- Do NOT add a full user profile page (Phase 2 scope)
- Do NOT implement organization management UI (Phase 4 scope)
- Do NOT add SSO/OAuth providers (Phase 5 scope)

---

## Naming Conventions
- Backend: snake_case files, PascalCase classes, snake_case functions
- Frontend: kebab-case files, PascalCase components, camelCase functions
- Database tables: snake_case plural (organizations, organization_members)
- API paths: kebab-case (/api/knowledge-bases)

## Integration Points
1. Frontend Better Auth ↔ PostgreSQL: same DATABASE_URL, Better Auth manages user/session tables
2. Backend auth middleware ↔ PostgreSQL: reads Better Auth session table + organization_members table
3. Frontend fetch ↔ Backend: cookies forwarded via `credentials: "include"` + nginx CORS
4. Nginx: must allow credentials and specific origins (not wildcard)
