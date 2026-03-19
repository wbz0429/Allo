# Phase 2 Contract: Config Wizard + Agent Customization

## Overview
Implement visual configuration wizard, per-tenant config persistence, agent template library, and agent workbench UI.

## Execution Phases

### Phase A (parallel)
- role: "backend-config" — Config API, tenant config DB model, agent templates, per-tenant agent storage, tests
- role: "frontend-config" — Config wizard UI, agent workbench, template gallery, settings enhancement

---

## Shared Interfaces

### Config API Endpoints
```
GET    /api/config                  # Get current tenant config (merged: base + tenant overrides)
PUT    /api/config                  # Update tenant config overrides
POST   /api/config/import           # Import YAML/JSON config
GET    /api/config/export           # Export current config as YAML

GET    /api/config/models           # List available models (from base config)
PUT    /api/config/models           # Set tenant's enabled models + default model

GET    /api/config/tools            # List available tool groups
PUT    /api/config/tools            # Set tenant's enabled tool groups
```

### Agent Template API Endpoints
```
GET    /api/agent-templates                # List all platform templates
GET    /api/agent-templates/{template_id}  # Get template detail (soul_md, tools, model, description)
POST   /api/agents/from-template           # Create agent from template (copies template + allows customization)
```

### Tenant Config DB Model
```python
class TenantConfig(Base):
    __tablename__ = "tenant_configs"
    id: str           # UUID
    org_id: str       # FK -> organizations.id, unique
    config_json: str  # JSON blob of config overrides
    updated_at: datetime

# config_json structure:
{
    "default_model": "gpt-4o",
    "enabled_models": ["gpt-4o", "deepseek-chat", "claude-sonnet"],
    "enabled_tool_groups": ["web_search", "code_execution"],
    "custom_settings": {}
}
```

### Agent Template Data Structure
```python
# Stored as Python dicts in app/gateway/templates/
AGENT_TEMPLATES = [
    {
        "id": "document-assistant",
        "name": "文书助手",
        "description": "专业文书写作、编辑、校对助手",
        "icon": "file-text",
        "category": "office",
        "soul_md": "...",  # SOUL.md content
        "model": None,  # Use tenant default
        "tool_groups": ["web_search"],
        "suggested_skills": [],
    },
    # ... more templates
]
```

### Frontend Config Wizard Flow
```
Step 1: Model Selection
  - Show available models as cards
  - Select default model + enable/disable others
  - Save via PUT /api/config/models

Step 2: Tool Configuration  
  - Show tool groups as toggle cards
  - Enable/disable tool groups
  - Save via PUT /api/config/tools

Step 3: Agent Setup
  - Show template gallery
  - Select template → pre-fill agent creation form
  - Or "Create from scratch"
  - Save via POST /api/agents or POST /api/agents/from-template

Step 4: Done
  - Summary of configuration
  - "Start chatting" button
```

---

## Role: backend-config

### Owned Files
- `backend/app/gateway/db/models.py` (MODIFY) — add TenantConfig model
- `backend/app/gateway/routers/config.py` (NEW) — config CRUD API
- `backend/app/gateway/routers/agents.py` (MODIFY) — add template endpoints, org_id scoping
- `backend/app/gateway/templates/` (NEW directory)
  - `__init__.py` — AGENT_TEMPLATES list
- `backend/app/gateway/app.py` (MODIFY) — register config router
- `backend/tests/test_config_router.py` (NEW) — config API tests
- `backend/tests/test_agent_templates.py` (NEW) — template tests
- `backend/tests/test_tenant_config.py` (NEW) — tenant config model tests

### Must Do
- TenantConfig model with org_id unique constraint
- Config API merges base config (from YAML) with tenant overrides (from DB)
- Agent templates: at least 3 templates (文书助手, 设计助手, 宣发助手)
- Agent CRUD must scope by org_id (agents belong to organizations)
- All new endpoints require AuthContext
- Export endpoint returns YAML format
- Import endpoint accepts both YAML and JSON
- Unit tests for all new code
- Follow existing code style (ruff, Google docstrings)

### Must NOT Do
- Do NOT modify harness files (`packages/harness/deerflow/`)
- Do NOT modify frontend files
- Do NOT modify nginx configs
- Do NOT modify Phase 1 auth files (auth.py, db/database.py) except adding to models.py

---

## Role: frontend-config

### Owned Files
- `frontend/src/app/workspace/setup/` (NEW directory) — setup wizard pages
  - `page.tsx` — main wizard page
  - `layout.tsx` — wizard layout
- `frontend/src/components/workspace/setup-wizard/` (NEW directory)
  - `setup-wizard.tsx` — main wizard component with steps
  - `model-selection-step.tsx` — model cards with selection
  - `tool-selection-step.tsx` — tool group toggles
  - `agent-setup-step.tsx` — template gallery + create form
  - `completion-step.tsx` — summary + start button
- `frontend/src/app/workspace/agents/` (MODIFY existing files)
  - Enhance agent gallery to show templates
  - Add agent config editor (SOUL.md editor, tool/model selection)
- `frontend/src/core/config/` (NEW or MODIFY)
  - `api.ts` — config API client functions
  - `types.ts` — TenantConfig types
- `frontend/src/core/agents/api.ts` (MODIFY) — add template API calls
- `frontend/src/core/agents/types.ts` (MODIFY if exists) — add template types
- `frontend/src/components/workspace/settings/` (MODIFY) — add Models settings section

### Must Do
- Setup wizard with 4 steps (models → tools → agents → done)
- Each step saves independently via API
- Model selection: card grid with model name, description, toggle
- Tool selection: card grid with tool group name, description, toggle
- Agent setup: template gallery (3+ templates) with "Use Template" button
- Agent config editor: textarea for SOUL.md, dropdowns for model/tools
- Use existing Shadcn components (Card, Button, Switch, Tabs, etc.)
- Use existing patterns: cn(), "use client", credentials: "include"
- Responsive layout (works on desktop)
- Add /workspace/setup route

### Must NOT Do
- Do NOT modify backend Python files
- Do NOT modify nginx configs
- Do NOT create test files (no frontend test framework)
- Do NOT implement knowledge base UI (Phase 3)

---

## Naming Conventions
- Backend: snake_case files, PascalCase classes
- Frontend: kebab-case files, PascalCase components
- API paths: kebab-case (/api/agent-templates)
- DB tables: snake_case (tenant_configs)
