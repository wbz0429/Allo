# CR Report: Config Wizard + Setup UI (Phase 2)

## Summary

The backend config API is well-structured and largely complete: all four plan-required endpoints are present, every endpoint is auth-gated via `Depends(get_auth_context)`, and config is correctly scoped per-tenant via `org_id`. The `TenantConfig` DB model is solid. However, the frontend is in an early/stub state: two of the four wizard steps (`ToolSelectionStep`, `AgentSetupStep`) are placeholder components with no real functionality, the fourth wizard step (knowledge upload) is entirely absent, the frontend TypeScript types do not match the actual backend API response shapes, and the API client is missing import/export functions. There is also a critical serialization bug in the export endpoint.

---

## Files Reviewed

- `backend/app/gateway/routers/config.py`
- `backend/app/gateway/config.py`
- `backend/app/gateway/db/models.py` (TenantConfig, Organization, related models)
- `frontend/src/app/workspace/setup/page.tsx`
- `frontend/src/app/workspace/setup/layout.tsx`
- `frontend/src/components/workspace/setup-wizard/setup-wizard.tsx`
- `frontend/src/components/workspace/setup-wizard/model-selection-step.tsx`
- `frontend/src/components/workspace/setup-wizard/agent-setup-step.tsx`
- `frontend/src/components/workspace/setup-wizard/tool-selection-step.tsx`
- `frontend/src/components/workspace/setup-wizard/completion-step.tsx`
- `frontend/src/core/config/api.ts`
- `frontend/src/core/config/hooks.ts`
- `frontend/src/core/config/types.ts`

---

## Plan vs Implementation Gap Analysis

| Plan Requirement | Status | Notes |
|---|---|---|
| Step 1: Model selection UI | ⚠️ Partial | UI renders and calls API, but `model.id` and `model.provider` fields don't exist in the backend response (see type mismatch below) |
| Step 2: Tool selection UI | ❌ Missing | `ToolSelectionStep` is a stub — icon + "Continue" button only, no tool cards, no API calls |
| Step 3: Agent creation/selection UI | ❌ Missing | `AgentSetupStep` is a stub — icon + "Continue" button only, no templates, no API calls |
| Step 4: Knowledge upload | ❌ Missing | Replaced with a generic `CompletionStep`; no knowledge upload UI at all |
| `GET /api/config` | ✅ Implemented | Returns merged base+tenant config, org_id scoped |
| `PUT /api/config` | ✅ Implemented | Partial update, org_id scoped |
| `POST /api/config/import` | ✅ Implemented | YAML/JSON import with auto-detect, replaces overrides |
| `GET /api/config/export` | ⚠️ Partial | Endpoint exists but has a serialization bug — returns `str` without `Response(media_type=...)`, so FastAPI JSON-encodes the YAML string |
| Config stored per-tenant (org_id scoped) | ✅ Implemented | `TenantConfig` has `unique=True` FK to `organizations.id`; all endpoints filter by `auth.org_id` |
| YAML/JSON import | ✅ Implemented | Auto-detect, safe_load, validates against `TenantConfigOverrides` |
| YAML export | ⚠️ Partial | YAML is generated correctly but delivered as a JSON-encoded string, not `text/yaml` |
| Frontend API client matches backend | ⚠️ Partial | `listModels`, `updateModelsConfig`, `listToolGroups`, `updateToolsConfig` are present; `importConfig` and `exportConfig` are absent |
| TypeScript types correct and complete | ❌ Incorrect | `ModelInfo` and `ToolGroupInfo` types do not match actual backend response shapes (details below) |
| per-tenant config isolation in harness | ❌ Missing | `_merge_config` calls global `get_app_config()` singleton; plan requires harness adaptation layer so per-tenant config is injected at request time |

---

## Code Quality Issues

### Backend

1. **`export_config` serialization bug** (`routers/config.py:234-242`): The endpoint is annotated `-> str` with no explicit `Response`. FastAPI will serialize the return value as a JSON string (i.e., the YAML content gets double-quoted). Fix: return `Response(content=yaml_str, media_type="application/yaml")`.

2. **Silent data loss in `_parse_overrides`** (`routers/config.py:81-87`): A `JSONDecodeError` is caught and silently returns empty overrides. If `config_json` is corrupted in the DB, the tenant silently loses all their config on the next read. Should at minimum log a warning with the `org_id`.

3. **`_merge_config` is synchronous but called from async handlers** (`routers/config.py:90-131`): `get_app_config()` does file I/O on first call. Not a correctness bug today (it's cached after first load), but worth noting for future hot-reload scenarios.

4. **`TenantConfig` model missing `created_at`** (`db/models.py:70-100`): All other models have both `created_at` and `updated_at`. `TenantConfig` only has `updated_at`. Minor, but inconsistent.

5. **`import_config` silently drops unknown keys** (`routers/config.py:219`): The dict comprehension `{k: v for k, v in data.items() if k in TenantConfigOverrides.model_fields}` silently ignores unrecognized fields. This is safe but could confuse users who import a full `config.yaml` expecting all fields to be stored. A warning response field would help.

### Frontend

6. **`ModelInfo.id` and `ModelInfo.provider` don't exist in backend response** (`types.ts:1-6`, `routers/config.py:253`): The backend `GET /api/config/models` returns `{"name": ..., "display_name": ..., "description": ...}`. The frontend `ModelInfo` type declares `id` and `provider` fields that are never populated. `model-selection-step.tsx` uses `model.id` (line 33, 109, 110) and `model.provider` (line 129) — these will be `undefined` at runtime, breaking model toggle and default selection.

7. **`ToolGroupInfo` fields mismatch** (`types.ts:8-13`, `routers/config.py:294`): Backend returns `{"name": tg.name}` only. Frontend type declares `id`, `description`, and `tools: string[]` — none of which exist in the response.

8. **`TenantConfig` frontend type vs backend response shape mismatch** (`types.ts:15-20`): Frontend `TenantConfig` has `enabled_models: string[]` (non-optional array), but backend `TenantConfigOverrides` has `enabled_models: list[str] | None`. The `MergedConfigResponse` returned by `GET /api/config` has `models: list[dict]` and `tool_groups: list[dict]` at the top level — not `enabled_models`/`enabled_tool_groups`. The frontend type maps to the overrides sub-object, not the merged response.

9. **`ToolSelectionStep` uses raw `<button>` instead of `Button` component** (`tool-selection-step.tsx:19`): Inconsistent with the rest of the wizard which uses `@/components/ui/button`. Same issue in `AgentSetupStep` (`agent-setup-step.tsx:19`).

10. **`model-selection-step.tsx` state initialization pattern** (lines 32-36): Setting state during render (`setEnabledModels`, `setDefaultModel`, `setInitialized`) is an anti-pattern that causes an extra render cycle. Should use `useEffect` or `useState` initializer with a function.

11. **`hooks.ts` missing `useTenantConfig`, `useImportConfig`, `useExportConfig`** (`hooks.ts`): The hooks file only covers models and tool groups. There are no hooks for the top-level config, import, or export operations, making those backend endpoints unreachable from the frontend.

12. **`api.ts` missing `importConfig` and `exportConfig` functions** (`api.ts`): The two advanced-mode endpoints (`POST /api/config/import`, `GET /api/config/export`) have no corresponding frontend API functions.

---

## Security / Architecture Concerns

1. **Global singleton base config shared across all tenants**: `_merge_config` calls `get_app_config()` which loads from the global `config.yaml`. The plan explicitly requires a harness adaptation layer so per-tenant config is injected at request time (Section 3.5, "配置加载适配"). This is not yet implemented — all tenants see the same base model/tool list, which is only filtered by their overrides. A tenant with no overrides gets the full global config.

2. **No input size limit on `import_config`**: The `content` field in `ConfigImportRequest` has no `max_length` constraint. A malicious user could POST a very large YAML/JSON payload. Add `Field(..., max_length=65536)` or similar.

3. **`yaml.safe_load` is used correctly** — no arbitrary code execution risk. Good.

4. **`GatewayConfig.cors_origins` defaults to `["http://localhost:3000"]`** (`config.py:11`): This is fine for dev but the plan calls for CORS tightening in Phase 1. Ensure production deployment sets `CORS_ORIGINS` env var.

5. **No role-based access control on config endpoints**: Any authenticated org member can call `PUT /api/config` and change the tenant's model/tool configuration. The plan's data model includes `admin`/`member` roles. Config writes should be restricted to `admin` role.

---

## Recommendations

1. **(Critical) Fix `ModelInfo` type and backend response shape**: Either add `id` (use `name` as id) and `provider` fields to the backend model response, or update the frontend `ModelInfo` type to match what the backend actually returns. The wizard is broken at runtime without this fix.

2. **(Critical) Fix `export_config` serialization**: Change the return to `return Response(content=yaml_str, media_type="application/yaml")` and import `Response` from `fastapi`.

3. **(High) Implement `ToolSelectionStep`**: Wire it to `useToolGroups()` and `useUpdateToolsConfig()` — the hooks and API already exist. Render tool group cards with toggles, mirroring the model selection pattern.

4. **(High) Implement `AgentSetupStep`**: Connect to the existing agents API (`/api/agents`). Show template cards and allow creating an agent from a template. This is the core Phase 2 deliverable.

5. **(High) Add knowledge upload step**: Replace or augment `CompletionStep` with a step 4 that links to knowledge base creation, or embed a minimal upload flow. This is explicitly listed in the plan as wizard step 4.

6. **(High) Add `importConfig`/`exportConfig` to `api.ts` and corresponding hooks**: The backend endpoints exist but are unreachable from the frontend.

7. **(Medium) Add admin role check to config write endpoints**: `PUT /api/config`, `PUT /api/config/models`, `PUT /api/config/tools`, `POST /api/config/import` should verify `auth.role == "admin"` before mutating.

8. **(Medium) Fix `model-selection-step.tsx` state initialization**: Replace the render-time state setter pattern with `useEffect(() => { if (!initialized && models.length > 0) { ... } }, [models, initialized])`.

9. **(Medium) Add `max_length` to `ConfigImportRequest.content`**: Prevent oversized payloads.

10. **(Low) Add `created_at` to `TenantConfig` model**: Consistent with all other models in `db/models.py`.

11. **(Low) Log a warning in `_parse_overrides` on `JSONDecodeError`**: Prevents silent data loss going unnoticed in production.
