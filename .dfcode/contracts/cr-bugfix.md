# CR Bug Fix Contract

> Fixes remaining issues from `.dfcode/reports/cr-testing-report.md`

## Context

The CR report identified 11 issues across P0/P1/P2. Several have been fixed already. This contract covers the remaining unfixed issues.

## Roles

### Role: `routers` (Worker 1 — backend-routers)

**Owns these files (create or modify ONLY these):**
- `backend/app/gateway/routers/admin.py` (NEW — create)
- `backend/app/gateway/routers/marketplace.py` (NEW — create)
- `backend/app/gateway/app.py` (modify — add router imports + include_router)
- `backend/app/gateway/routers/__init__.py` (modify — add admin, marketplace exports)
- `backend/tests/test_app_registration.py` (modify — remove xfail markers, fix config test)

**Must NOT touch:** embedder.py, marketplace_seed.py, agents.py, test_router_knowledge_bases.py, or any other existing file not listed above.

### Role: `lint-fixes` (Worker 2 — lint & code fixes)

**Owns these files (modify ONLY these):**
- `backend/app/gateway/rag/embedder.py` (fix: move `response.json()` inside `async with`, remove unused `import json`)
- `backend/app/gateway/marketplace_seed.py` (fix: break long lines > 240 chars)
- `backend/app/gateway/routers/agents.py` (fix: ruff I001 import sorting)
- `backend/tests/test_router_knowledge_bases.py` (fix: remove unused imports F401)
- Any other files with ruff lint errors EXCEPT files owned by Worker 1

**Must NOT touch:** app.py, routers/__init__.py, test_app_registration.py, or create new files.

---

## Shared Interfaces

### AuthContext (read-only — do NOT modify `auth.py`)

```python
from app.gateway.auth import AuthContext, get_auth_context

# AuthContext has: user_id: str, org_id: str, role: str ("admin" | "member")
# Use as FastAPI dependency: auth: AuthContext = Depends(get_auth_context)
```

### Database Session (read-only — do NOT modify `database.py`)

```python
from app.gateway.db.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

# Use as: db: AsyncSession = Depends(get_db_session)
```

### DB Models (read-only — do NOT modify `models.py`)

Worker 1 uses these models:
- `Organization` — fields: id, name, slug, created_at, updated_at; relationship: members
- `OrganizationMember` — fields: id, org_id, user_id, role, created_at
- `UsageRecord` — fields: id, org_id, user_id, record_type, model_name, input_tokens, output_tokens, endpoint, duration_seconds, created_at
- `MarketplaceTool` — fields: id, name, description, category, icon, mcp_config_json, is_public, created_at
- `MarketplaceSkill` — fields: id, name, description, category, skill_content, is_public, created_at
- `OrgInstalledTool` — fields: id, org_id, tool_id, config_json, installed_at; unique constraint: (org_id, tool_id)
- `OrgInstalledSkill` — fields: id, org_id, skill_id, installed_at; unique constraint: (org_id, skill_id)
- `TenantConfig` — fields: id, org_id, config_json, updated_at

### Marketplace Seed Data (read-only — Worker 2 may fix lint but NOT change data)

```python
from app.gateway.marketplace_seed import SEED_TOOLS, SEED_SKILLS
# SEED_TOOLS: list[dict] with 5 tools
# SEED_SKILLS: list[dict] with 3 skills
```

---

## Admin Router Spec (`routers/admin.py`)

Router prefix: `/api/admin`, tags: `["admin"]`

### Platform Admin Endpoints (require role == "admin")

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/organizations` | List all organizations (platform admin only) |
| GET | `/api/admin/organizations/{org_id}` | Get org details with member count |
| GET | `/api/admin/usage` | Get aggregated usage stats across all orgs |

### Enterprise Admin Endpoints (require auth, scoped to auth.org_id)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/org/members` | List members of the authenticated org |
| POST | `/api/admin/org/members` | Add a member to the org (admin only) |
| DELETE | `/api/admin/org/members/{member_id}` | Remove a member (admin only) |
| GET | `/api/admin/org/usage` | Get usage stats for the authenticated org |

### Auth Guards

- Platform admin endpoints: check `auth.role == "admin"` and optionally a platform-admin flag. For now, just check `role == "admin"`.
- Enterprise admin write endpoints (POST/DELETE members): check `auth.role == "admin"`, raise 403 if not.
- Enterprise admin read endpoints (GET members, GET usage): any authenticated user.

### Pydantic Models (define in admin.py)

```python
class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    member_count: int
    created_at: str

class MemberResponse(BaseModel):
    id: str
    user_id: str
    role: str
    created_at: str

class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "member"

class UsageStatsResponse(BaseModel):
    total_api_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_sandbox_seconds: float
    record_count: int
```

---

## Marketplace Router Spec (`routers/marketplace.py`)

Router prefix: `/api/marketplace`, tags: `["marketplace"]`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/marketplace/tools` | Browse public tools catalog |
| GET | `/api/marketplace/skills` | Browse public skills catalog |
| GET | `/api/marketplace/tools/{tool_id}` | Get tool details |
| GET | `/api/marketplace/skills/{skill_id}` | Get skill details |
| POST | `/api/marketplace/tools/{tool_id}/install` | Install a tool for the org |
| DELETE | `/api/marketplace/tools/{tool_id}/install` | Uninstall a tool |
| POST | `/api/marketplace/skills/{skill_id}/install` | Install a skill for the org |
| DELETE | `/api/marketplace/skills/{skill_id}/install` | Uninstall a skill |
| GET | `/api/marketplace/installed/tools` | List org's installed tools |
| GET | `/api/marketplace/installed/skills` | List org's installed skills |

### Seed Data Loading

On first request or at startup, check if `marketplace_tools` table is empty. If so, insert `SEED_TOOLS` and `SEED_SKILLS` from `marketplace_seed.py`. Use a simple check-and-insert pattern (not upsert).

### Pydantic Models (define in marketplace.py)

```python
class ToolResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    is_public: bool

class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    is_public: bool

class InstalledToolResponse(BaseModel):
    id: str
    tool: ToolResponse
    config_json: str
    installed_at: str

class InstalledSkillResponse(BaseModel):
    id: str
    skill: SkillResponse
    installed_at: str

class InstallToolRequest(BaseModel):
    config_json: str = "{}"
```

---

## app.py Registration (Worker 1)

Add to imports:
```python
from app.gateway.routers import admin, marketplace
```

Add to `create_app()` after the knowledge_bases router:
```python
# Admin API is mounted at /api/admin
app.include_router(admin.router)

# Marketplace API is mounted at /api/marketplace
app.include_router(marketplace.router)
```

Add to `openapi_tags`:
```python
{"name": "admin", "description": "Platform and enterprise administration"},
{"name": "marketplace", "description": "MCP tool and skill marketplace"},
```

---

## routers/__init__.py Update (Worker 1)

Change the import line to include `admin` and `marketplace`:
```python
from . import admin, agents, artifacts, channels, config, knowledge_bases, marketplace, mcp, memory, models, skills, suggestions, uploads
```

---

## test_app_registration.py Updates (Worker 1)

1. Remove `@pytest.mark.xfail` from `test_config_routes_registered` — config router IS registered now
2. Remove `@pytest.mark.xfail` from `test_admin_router_importable` — admin router will exist
3. Remove `@pytest.mark.xfail` from `test_marketplace_router_importable` — marketplace router will exist
4. Add new tests:
   - `test_admin_routes_registered` — check `/api/admin` prefix exists
   - `test_marketplace_routes_registered` — check `/api/marketplace` prefix exists

---

## Embedder Fix (Worker 2)

File: `backend/app/gateway/rag/embedder.py`

1. Remove `import json` (unused, F401)
2. Move `data = response.json()` and subsequent lines INSIDE the `async with` block:

```python
async with httpx.AsyncClient(timeout=60.0) as client:
    response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

# Sort by index to ensure correct ordering
embeddings_data = sorted(data["data"], key=lambda x: x["index"])
return [item["embedding"] for item in embeddings_data]
```

---

## Ruff Lint Fixes (Worker 2)

After making manual fixes, run:
```bash
cd backend && PYTHONPATH=. uv run ruff check . --fix
```

Then check for remaining unfixable errors and fix manually (e.g., long lines in marketplace_seed.py).

For marketplace_seed.py long lines: break the `skill_content` strings using string concatenation or multi-line strings.

---

## Naming Conventions

- Router files: `snake_case.py`
- Router variable: `router = APIRouter(prefix="/api/...", tags=["..."])`
- Pydantic models: `PascalCase`
- Endpoint functions: `snake_case`
- Follow existing patterns in `config.py` and `knowledge_bases.py`

---

## Verification

After all fixes, these commands must pass:
```bash
cd backend && PYTHONPATH=. uv run ruff check .
cd backend && PYTHONPATH=. uv run pytest tests/ -v --ignore=tests/test_client_live.py --ignore=tests/test_checkpointer.py
```
