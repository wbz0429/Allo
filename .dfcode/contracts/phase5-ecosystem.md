# Phase 5 Contract: Ecosystem + Private Deployment

## Overview
Implement MCP tool marketplace, Skills marketplace, private deployment package, and open API for customer integration.

## Execution Phases
### Phase A (parallel)
- role: "backend-ecosystem" — MCP marketplace API, Skills marketplace API, Docker Compose deployment, open API endpoints, tests
- role: "frontend-ecosystem" — MCP tool marketplace UI, Skills marketplace UI, deployment docs page

---

## Shared Interfaces

### MCP Tool Marketplace API
```
GET    /api/marketplace/tools              # Browse public tool catalog
GET    /api/marketplace/tools/{id}         # Tool detail (schema, docs)
POST   /api/marketplace/tools/{id}/install # Install tool for org
DELETE /api/marketplace/tools/{id}/uninstall # Uninstall tool for org
GET    /api/org/tools                      # List org's installed tools
```

### Skills Marketplace API
```
GET    /api/marketplace/skills             # Browse public skills catalog
GET    /api/marketplace/skills/{id}        # Skill detail
POST   /api/marketplace/skills/{id}/install # Install skill for org
DELETE /api/marketplace/skills/{id}/uninstall # Uninstall skill for org
GET    /api/org/skills                     # List org's installed skills
```

### Marketplace DB Models
```python
class MarketplaceTool(Base):
    __tablename__ = "marketplace_tools"
    id: str
    name: str
    description: str
    category: str        # "search" | "code" | "data" | "communication"
    icon: str
    mcp_config_json: str # MCP server config template
    is_public: bool
    created_at: datetime

class OrgInstalledTool(Base):
    __tablename__ = "org_installed_tools"
    id: str
    org_id: str          # FK organizations
    tool_id: str         # FK marketplace_tools
    config_json: str     # Org-specific config (API keys etc)
    installed_at: datetime

class MarketplaceSkill(Base):
    __tablename__ = "marketplace_skills"
    id: str
    name: str
    description: str
    category: str
    skill_content: str   # SKILL.md content
    is_public: bool
    created_at: datetime

class OrgInstalledSkill(Base):
    __tablename__ = "org_installed_skills"
    id: str
    org_id: str
    skill_id: str
    installed_at: datetime
```

---

## Role: backend-ecosystem

### Owned Files
- `backend/app/gateway/db/models.py` (MODIFY) — add marketplace models
- `backend/app/gateway/routers/marketplace.py` (NEW) — marketplace browse + install API
- `backend/app/gateway/routers/org_tools.py` (NEW) — org tool management
- `backend/app/gateway/app.py` (MODIFY) — register new routers
- `backend/app/gateway/marketplace_seed.py` (NEW) — seed data for marketplace (built-in tools/skills)
- `docker/docker-compose.prod.yml` (NEW) — production Docker Compose for private deployment
- `backend/tests/test_marketplace.py` (NEW) — marketplace API tests
- `backend/tests/test_org_tools.py` (NEW) — org tool management tests

### Must Do
- Marketplace models for tools and skills
- Seed data: at least 5 tools (Tavily Search, Firecrawl, Jina AI, DuckDuckGo, Code Sandbox) and 3 skills
- Install/uninstall endpoints with org_id scoping
- Docker Compose prod config: postgres + redis + backend + frontend + nginx
- Unit tests for all new code
- Follow existing code style

### Must NOT Do
- Do NOT modify harness files
- Do NOT modify frontend files
- Do NOT implement actual MCP server provisioning (just config storage)

---

## Role: frontend-ecosystem

### Owned Files
- `frontend/src/app/workspace/marketplace/` (NEW directory)
  - `layout.tsx`
  - `page.tsx` — marketplace browse page (tools + skills tabs)
  - `tools/[id]/page.tsx` — tool detail page
  - `skills/[id]/page.tsx` — skill detail page
- `frontend/src/core/marketplace/` (NEW directory)
  - `api.ts` — marketplace API client
  - `types.ts` — marketplace types
- `frontend/src/components/workspace/marketplace/` (NEW directory)
  - `tool-card.tsx` — tool card with install button
  - `skill-card.tsx` — skill card with install button
  - `install-dialog.tsx` — config dialog for tool installation
- `frontend/src/components/workspace/workspace-sidebar.tsx` (MODIFY) — add Marketplace nav
- `frontend/src/components/workspace/workspace-nav-chat-list.tsx` (MODIFY if needed)

### Must Do
- Marketplace page with Tabs: Tools | Skills
- Tool cards: icon, name, description, category badge, Install/Uninstall button
- Skill cards: similar layout
- Install dialog: show required config fields (e.g., API key)
- Add "Marketplace" nav item in sidebar with Store icon
- Use Shadcn Tabs, Card, Button, Badge, Dialog, Input
- All fetches include credentials: "include"

### Must NOT Do
- Do NOT modify backend Python files
- Do NOT modify nginx configs
