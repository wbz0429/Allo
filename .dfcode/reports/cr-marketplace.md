# CR Report: Marketplace / Ecosystem (Phase 5)

## Summary

The marketplace module has a solid structural foundation — correct DB models, proper org-scoped install/uninstall endpoints, seed data with the right counts, and a clean frontend card/dialog UI. However, it is **not functional as shipped** due to three critical API contract mismatches between the frontend and backend that will cause silent failures at runtime. Beyond those bugs, the most significant architectural gap is that installing a tool or skill from the marketplace has **no effect on the agent runtime** — installed items are never bridged into the MCP tool system or the Skills filesystem, making the entire install flow decorative. Several plan requirements (pagination/filtering, customer MCP onboarding, private tools) are also missing.

---

## Files Reviewed

- `backend/app/gateway/routers/marketplace.py`
- `backend/app/gateway/marketplace_seed.py`
- `backend/app/gateway/db/models.py` (MarketplaceTool, MarketplaceSkill, OrgInstalledTool, OrgInstalledSkill sections)
- `backend/app/gateway/routers/config.py` (for integration context)
- `backend/app/gateway/routers/mcp.py` (for integration context)
- `backend/app/gateway/routers/skills.py` (for integration context)
- `frontend/src/app/workspace/marketplace/page.tsx`
- `frontend/src/app/workspace/marketplace/layout.tsx`
- `frontend/src/components/workspace/marketplace/tool-card.tsx`
- `frontend/src/components/workspace/marketplace/skill-card.tsx`
- `frontend/src/components/workspace/marketplace/install-dialog.tsx`
- `frontend/src/core/marketplace/api.ts`
- `frontend/src/core/marketplace/types.ts`

---

## Plan vs Implementation Gap Analysis

| Plan Requirement | Status | Notes |
|---|---|---|
| MCP tool marketplace — public tool directory | ✅ Implemented | 5 seed tools, browse API, `is_public` flag |
| Skills marketplace | ✅ Implemented | 3 seed skills, browse API |
| Tenant install management (tools) | ⚠️ Partial | DB + API correct; not bridged to MCP runtime |
| Tenant install management (skills) | ⚠️ Partial | DB + API correct; not bridged to Skills filesystem |
| Seed data: 5 tools | ✅ Implemented | Tavily, Firecrawl, Jina AI, DuckDuckGo, Code Sandbox |
| Seed data: 3 skills | ✅ Implemented | Deep Research, Code Review, Data Analysis |
| Org-scoped installation (org_id isolation) | ✅ Implemented | All install/uninstall queries filter by `auth.org_id` |
| Installed tools/skills activated for org agents | ❌ Missing | No bridge from `OrgInstalledTool` → MCP config; no bridge from `OrgInstalledSkill` → Skills filesystem |
| Browse with filtering / pagination | ❌ Missing | List endpoints return all records; no `category`, `search`, `page`, `limit` params |
| Customer custom MCP Server onboarding | ❌ Missing | Plan item not started |
| Private/org-specific tools in catalog | ❌ Missing | Only `is_public=True` tools are browseable; no org-private tool support |
| Frontend hooks.ts module | ❌ Missing | `core/marketplace/` has only `api.ts` + `types.ts`; no `hooks.ts` per project pattern |
| Tool/skill detail pages | ❌ Missing | Cards link to `/workspace/marketplace/tools/{id}` and `/skills/{id}` — routes don't exist |

---

## Code Quality Issues

### Critical — Runtime Breakage

1. **`listOrgTools()` / `listOrgSkills()` call non-existent endpoints** (`api.ts:59,116`)
   - Frontend calls `GET /api/org/tools` and `GET /api/org/skills`
   - Backend exposes `GET /api/marketplace/installed/tools` and `GET /api/marketplace/installed/skills`
   - The `.catch(() => [])` in `page.tsx:47-48` silently swallows the 404, so `installedTools` and `installedSkills` are always empty arrays — install/uninstall buttons never reflect actual state.

2. **`uninstallTool()` / `uninstallSkill()` call non-existent endpoints** (`api.ts:49,105`)
   - Frontend calls `DELETE /api/marketplace/tools/{id}/uninstall` and `.../skills/{id}/uninstall`
   - Backend route is `DELETE /api/marketplace/tools/{tool_id}/install` (DELETE on the `/install` path, not `/uninstall`)
   - Every uninstall action will 404.

3. **Frontend types don't match backend response shapes** (`types.ts:4-38`)
   - `MarketplaceTool` declares `mcp_config_json` and `created_at` — neither is in `ToolResponse` from the backend. `InstallDialog.parseConfigFields()` reads `tool.mcp_config_json`, which will always be `undefined`, so the config form never renders fields.
   - `MarketplaceSkill` declares `skill_content` and `created_at` — neither is in `SkillResponse`.
   - `OrgInstalledTool` declares `org_id` and `tool_id` at the top level — but `InstalledToolResponse` nests the tool as `{ id, tool: { ... }, config_json, installed_at }`. `isToolInstalled` checks `t.tool_id === toolId` which will always be `undefined`.
   - Same shape mismatch for `OrgInstalledSkill` vs `InstalledSkillResponse`.

### Significant

4. **N+1 query in `list_installed_tools` / `list_installed_skills`** (`marketplace.py:295-341`)
   - For each installed item, a separate `SELECT` fetches the tool/skill row. Should use a single JOIN query or eager-load via SQLAlchemy relationship.

5. **`_ensure_seed_data` called on every request** (`marketplace.py:94-106`)
   - A DB query runs on every call to any marketplace endpoint. Should be a startup event or a module-level flag. Under concurrent requests at first boot, two requests can both see an empty table and both attempt to insert, causing a unique-constraint violation on `name`.

6. **`_ensure_seed_data` only checks `marketplace_tools`** (`marketplace.py:96`)
   - If tools exist but skills don't (e.g., partial seed failure), skills are never seeded.

7. **`config_json` stores API keys in plaintext** (`models.py:328`, `marketplace.py:203`)
   - MCP tool API keys (Tavily, Firecrawl, Jina) are stored as plain JSON text in `org_installed_tools.config_json`. No encryption at rest.

8. **`InstallToolRequest` body is optional** (`marketplace.py:183`)
   - `request: InstallToolRequest | None = None` — FastAPI will not parse the body if the client omits `Content-Type: application/json`. The frontend always sends a body, but this is fragile.

9. **Unused `cn()` import in `tool-card.tsx` and `skill-card.tsx`**
   - `cn` is imported and used only in a trivially unconditional `className={cn("...")}` call — the conditional logic was removed but the import was not cleaned up.

10. **Missing blank line between import groups in `tool-card.tsx:17`**
    - ESLint `import/order` rule requires a blank line between external and internal import groups; line 17 has no separator before the `@/core/...` import.

---

## Security / Architecture Concerns

1. **Installed tools never activate — the core value proposition is undelivered.**
   The `mcp.py` router reads MCP config from `extensions_config.json` (a global file). Installing a tool via the marketplace writes to `org_installed_tools` in the DB but never touches `extensions_config.json` or any per-tenant MCP config. The LangGraph agent therefore never sees the installed tool. The same applies to skills: `skills.py` reads from the filesystem; marketplace skill installs write only to `org_installed_skills` in the DB and never write a `SKILL.md` file.

2. **No per-tenant MCP config isolation.**
   Even if the bridge were built, `extensions_config.json` is a single global file shared across all tenants. Installing a tool for Org A would expose it to Org B. A per-tenant MCP config store (DB-backed, keyed by `org_id`) is needed before the activation bridge can be safely implemented.

3. **`_ensure_seed_data` race condition under concurrent startup.**
   Two simultaneous requests at first boot can both pass the `result.first() is not None` check and both attempt to insert seed rows, hitting the `UNIQUE` constraint on `marketplace_tools.name`. Should use `INSERT ... ON CONFLICT DO NOTHING` or a startup lifespan event.

4. **Detail page routes linked but not guarded.**
   `ToolCard` and `SkillCard` render `<Link href="/workspace/marketplace/tools/{id}">` — navigating there will hit a Next.js 404. Should either implement the pages or remove the links.

---

## Recommendations

1. **(P0) Fix the three API contract bugs before any other work:**
   - Change `listOrgTools()` URL to `/api/marketplace/installed/tools`
   - Change `listOrgSkills()` URL to `/api/marketplace/installed/skills`
   - Change `uninstallTool()` URL to `DELETE /api/marketplace/tools/{id}/install` (or rename the backend route to `/uninstall` for clarity)
   - Align `types.ts` with actual backend response shapes: remove `mcp_config_json`, `created_at`, `skill_content` from the browse types; fix `OrgInstalledTool` / `OrgInstalledSkill` to match `InstalledToolResponse` / `InstalledSkillResponse`

2. **(P0) Expose `mcp_config_json` in `ToolResponse`** so `InstallDialog` can render config fields. Without this the install dialog is always a no-op config form.

3. **(P1) Build the activation bridge — this is the core deliverable of Phase 5:**
   - For tools: on install, merge the tool's `mcp_config_json` + org-supplied `config_json` into a per-tenant MCP config store (new DB table or extend `TenantConfig`). Modify the agent bootstrap path to load per-tenant MCP servers from the DB instead of (or in addition to) the global file.
   - For skills: on install, write the `skill_content` as a `SKILL.md` file into a per-tenant skills directory (e.g., `skills/orgs/{org_id}/{skill_name}/SKILL.md`), or store skill content in DB and inject it at agent prompt-build time.

4. **(P1) Fix `_ensure_seed_data` race condition** — move seed insertion to the FastAPI `lifespan` startup event using `INSERT ... ON CONFLICT DO NOTHING`, and check both tools and skills tables independently.

5. **(P1) Replace N+1 queries** in `list_installed_tools` / `list_installed_skills` with a single JOIN or by using SQLAlchemy `selectinload` on the `tool` / `skill` relationship.

6. **(P2) Add pagination and category filtering** to `GET /api/marketplace/tools` and `GET /api/marketplace/skills` — query params: `category`, `search`, `page`, `limit`.

7. **(P2) Add `hooks.ts`** to `frontend/src/core/marketplace/` following the project pattern (`useMarketplaceTools`, `useInstalledTools`, etc.) to avoid duplicating fetch logic in the page component.

8. **(P2) Encrypt `config_json`** at rest (or at minimum document that API keys must not be stored in this field without encryption). Consider using a secrets manager reference pattern instead of storing raw keys.

9. **(P3) Implement tool/skill detail pages** at `/workspace/marketplace/tools/[id]` and `/workspace/marketplace/skills/[id]`, or remove the dead links from the cards.

10. **(P3) Design per-tenant MCP config isolation** before enabling the activation bridge in production — the global `extensions_config.json` approach is incompatible with multi-tenancy.
