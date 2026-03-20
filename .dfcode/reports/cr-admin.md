# CR Report: Admin Dashboard + Usage Tracking (Phase 4)

## Summary

Phase 4 delivers a functional dual-layer admin system with a solid foundation: the backend router, usage tracking middleware, token bucket rate limiter, and frontend admin UI are all present and largely correct. However, there are significant gaps between the plan and the implementation. The most critical issues are: (1) the frontend API client calls endpoints that do not exist in the backend (`/api/admin/usage/summary`, `/api/admin/usage/by-org`, `/api/admin/organizations/{id}/quotas`, `/api/org/members`, `/api/org/members/invite`, `/api/org/members/{id}/role`, `/api/org/usage/by-user`), causing the entire admin UI to be non-functional at runtime; (2) the usage tracking middleware has a fundamental architectural flaw — it reads `request.state` after the route handler runs, but FastAPI dependency injection does not populate `request.state` before the middleware reads it, so token/org context is never captured; (3) LLM token tracking (the primary billing metric) is entirely absent — only `api_call` records are written, never `llm_token` records; (4) the enterprise admin section (member management, org usage view) has no dedicated frontend page; and (5) quota management, department management, and model management are all missing.

---

## Files Reviewed

- `backend/app/gateway/routers/admin.py`
- `backend/app/gateway/middleware/usage_tracking.py`
- `backend/app/gateway/middleware/rate_limiter.py`
- `backend/app/gateway/db/models.py` (UsageRecord and all other models)
- `frontend/src/app/admin/layout.tsx`
- `frontend/src/app/admin/page.tsx`
- `frontend/src/app/admin/organizations/page.tsx`
- `frontend/src/app/admin/usage/page.tsx`
- `frontend/src/components/admin/org-table.tsx`
- `frontend/src/components/admin/member-table.tsx`
- `frontend/src/components/admin/usage-chart.tsx`
- `frontend/src/core/admin/api.ts`
- `frontend/src/core/admin/types.ts`
- `frontend/src/core/org/api.ts`
- `frontend/src/core/org/types.ts`

---

## Plan vs Implementation Gap Analysis

| Plan Requirement | Status | Notes |
|---|---|---|
| Token usage metering callback (harness layer) | ❌ Missing | Plan §3.5 requires a LangChain callback injected at model creation time. No `llm_token` UsageRecord is ever written. Only `api_call` records exist. |
| Usage record table with org_id, user_id, tokens_in, tokens_out, model, timestamp | ⚠️ Partial | `UsageRecord` has `org_id`, `user_id`, `input_tokens`, `output_tokens`, `model_name`, `created_at`. Missing: `tokens_in`/`tokens_out` naming is fine (aliased), but `model_name` is never populated since LLM tracking is absent. |
| Platform admin: tenant management (list, quota adjust, enable/disable) | ⚠️ Partial | `GET /api/admin/organizations` and `GET /api/admin/organizations/{org_id}` exist. Quota adjustment (`PUT /api/admin/organizations/{id}/quotas`) and enable/disable are missing. |
| Platform admin: usage statistics (global token consumption, active users, hot agents) | ⚠️ Partial | `GET /api/admin/usage` returns aggregate totals. Missing: per-day breakdown, active user count, hot agent stats, per-org breakdown endpoint. |
| Platform admin: model management (global available models, pricing config) | ❌ Missing | No model management endpoints in `admin.py`. |
| Platform admin: agent template management | ❌ Missing | Not in scope of this router but plan lists it under platform admin. |
| Enterprise admin: member management (invite/remove/role) | ⚠️ Partial | Backend has `GET/POST /api/admin/org/members` and `DELETE /api/admin/org/members/{id}`. Frontend `core/org/api.ts` calls `/api/org/members` (different prefix — mismatch). No invite-by-email flow on backend. No role-update endpoint on backend. |
| Enterprise admin: department management | ❌ Missing | No `Department` model, no department endpoints. |
| Enterprise admin: usage view (own org consumption) | ⚠️ Partial | `GET /api/admin/org/usage` exists. Frontend calls `/api/org/usage` (prefix mismatch). No per-day or per-user breakdown endpoint on backend. |
| Enterprise admin: agent management (publish/unpublish) | ❌ Missing | Not implemented in this phase. |
| Enterprise admin: knowledge base permission control | ❌ Missing | Not implemented in this phase. |
| Rate limiting with Redis backend | ⚠️ Partial | Token bucket algorithm is correctly implemented in-memory. Redis backend is noted as "planned" in comments but absent. In-memory state is lost on restart and not shared across processes/replicas. |
| Rate limiting: per-org quota from DB | ❌ Missing | `org_quotas` dict is static at startup. No mechanism to load per-org RPM from the database dynamically. |
| Usage tracking middleware records token consumption per request | ⚠️ Partial | Middleware records `api_call` type only. LLM token counts are never recorded. The `request.state` read-after-route pattern is architecturally broken (see Security/Architecture section). |
| Frontend: org list page | ✅ Implemented | `admin/organizations/page.tsx` + `OrgTable` component. |
| Frontend: usage charts | ✅ Implemented | `UsageChart` component with stacked bar chart for input/output tokens. |
| Frontend: member management UI | ⚠️ Partial | `MemberTable` component exists with invite/remove/role-change UI. No page wires it up (no `admin/members/page.tsx` or enterprise admin route). |
| Frontend: admin layout with navigation | ✅ Implemented | `layout.tsx` with Dashboard / Organizations / Usage nav. |
| Frontend: dashboard summary stats | ⚠️ Partial | `admin/page.tsx` calls `getUsageSummary()` and `getUsageByOrg()` which hit non-existent backend endpoints. |
| Role-based access control (platform admin vs enterprise admin) | ⚠️ Partial | `_require_admin(auth)` checks `auth.role == "admin"` for platform endpoints. Enterprise endpoints only check `auth.org_id` (any authenticated user can list their org's members). No "enterprise admin" role distinction. |
| Dual-layer admin (platform admin + enterprise admin) | ⚠️ Partial | Backend structure separates the two layers correctly. Frontend only has a platform admin UI at `/admin`. No enterprise admin UI at `/workspace/settings/org` as specified in the plan. |
| Billing integration | ❌ Missing | Plan Phase 4 includes billing integration. Not present. |

---

## Code Quality Issues

- **admin.py:89** — `list_organizations` issues N+1 queries: one `COUNT` query per org to get member count. Should use a single `GROUP BY` query with `func.count()` joined to `organization_members`.
- **admin.py:49-56** — `UsageStatsResponse` has both `total_api_calls` and `record_count` fields that are always identical (both set to `row.record_count`). Redundant field; `total_api_calls` should count only `record_type == "api_call"` rows.
- **admin.py:64-67** — `_require_admin` checks `auth.role == "admin"` but this is the same role used for enterprise admins. There is no `platform_admin` role distinction. A platform admin and an enterprise org admin share the same role string, which means any enterprise admin can call `GET /api/admin/organizations` and see all tenants.
- **usage_tracking.py:45-46** — `request.state.user_id` and `request.state.org_id` are read after `call_next(request)` returns. FastAPI's `Depends(get_auth_context)` runs inside the route handler, not before the middleware's `call_next`. The state will always be `None` unless `set_request_auth_state()` is explicitly called from the auth dependency — but there is no evidence this is wired up in `auth.py`. The helper `set_request_auth_state` exists but is not imported or called anywhere visible.
- **usage_tracking.py:60** — Bare `except Exception` swallows all errors silently. Should at minimum log the exception type.
- **rate_limiter.py:103** — `request.url.path.startswith(self._SKIP_PREFIXES)` passes a tuple to `startswith`, which works in Python but is non-obvious. A comment or explicit loop would be clearer.
- **rate_limiter.py:106-109** — If `org_id` is not set on `request.state`, the request passes through without rate limiting. This means unauthenticated requests bypass the rate limiter entirely, which could allow DoS from unauthenticated callers.
- **core/admin/api.ts:11-17** — `listOrganizations` expects the response to be `{ organizations: OrgSummary[] }` but the backend returns a plain `OrgSummary[]` array. The unwrapping `data.organizations` will always be `undefined`.
- **core/admin/api.ts:47** — `getUsageSummary()` calls `/api/admin/usage/summary` — this endpoint does not exist. Backend only has `/api/admin/usage`.
- **core/admin/api.ts:54** — `getUsageByOrg()` calls `/api/admin/usage/by-org` — this endpoint does not exist.
- **core/admin/api.ts:29-43** — `updateOrgQuotas()` calls `/api/admin/organizations/{id}/quotas` — this endpoint does not exist.
- **core/org/api.ts:10** — `listOrgMembers()` calls `/api/org/members` but backend exposes `/api/admin/org/members`.
- **core/org/api.ts:18** — `inviteMember()` calls `/api/org/members/invite` — no such endpoint exists on the backend.
- **core/org/api.ts:40-54** — `updateMemberRole()` calls `/api/org/members/{userId}/role` — no such endpoint exists.
- **core/org/api.ts:65** — `getOrgUsageByUser()` calls `/api/org/usage/by-user` — no such endpoint exists.
- **core/org/api.ts:14** — Response unwrapping expects `{ members: OrgMember[] }` but backend returns a plain array.
- **admin/types.ts** — `OrgSummary` includes `total_tokens` and `total_api_calls` fields, but the backend `OrgResponse` model does not include these. The frontend will always show 0 for these columns in `OrgTable`.
- **admin/types.ts** — `OrgDetail` includes `quotas: OrgQuotas` and `usage_by_day: DailyUsage[]` but no backend endpoint returns these shapes.
- **member-table.tsx** — `MemberTable` component is fully built but never used in any page. It is dead code from the user's perspective.
- **layout.tsx:10** — `QueryClient` is instantiated at module level outside of React state, which means it is shared across all renders in the same module scope. Should be inside a `useState` or `useMemo` to avoid stale state across hot reloads and tests.

---

## Security / Architecture Concerns

1. **Platform admin role conflation** — `_require_admin` checks `auth.role == "admin"` with no distinction between a platform-level superadmin and an enterprise org admin. An enterprise org admin with `role="admin"` can call `GET /api/admin/organizations` and enumerate all tenants on the platform. The plan explicitly requires two separate admin tiers.

2. **Usage middleware state race** — The middleware reads `request.state.user_id/org_id` after `call_next()` returns. In Starlette/FastAPI, `request.state` is mutable and shared, but FastAPI dependency injection (`Depends`) runs inside the route handler which is called by `call_next`. The state is set during the route execution, so it *should* be readable after `call_next` returns — however, this only works if `set_request_auth_state()` is explicitly called from the auth dependency. If the auth dependency raises an exception (e.g. 401), `call_next` will propagate the exception and the state may not be set. The current code silently skips tracking on any exception, which means failed auth attempts are not tracked. More importantly, there is no evidence `set_request_auth_state` is called from `get_auth_context` in `auth.py`.

3. **In-memory rate limiter not production-safe** — The `_buckets` dict lives in the middleware instance. In a multi-worker deployment (Gunicorn with multiple processes, or Kubernetes with multiple pods), each process has its own bucket state. An org can exceed its quota by a factor of N (number of workers). Redis is required for correctness in production.

4. **No LLM token tracking** — The plan's billing model is primarily token-based. Without `llm_token` UsageRecord entries, there is no basis for billing. The harness-layer LangChain callback described in §3.5 is not implemented.

5. **No quota enforcement** — Even if rate limiting works, there is no enforcement of `max_tokens_per_day` or `max_storage_mb` quotas. The `OrgQuotas` type exists in the frontend but has no backend counterpart.

6. **Unauthenticated requests bypass rate limiter** — If `org_id` is absent from `request.state` (unauthenticated request), the rate limiter passes the request through. This is intentional per the comment, but it means the auth layer is the only protection against unauthenticated flooding.

7. **No pagination on list endpoints** — `list_organizations` and `list_org_members` return unbounded result sets. At scale this will cause memory and latency issues.

---

## Recommendations

1. **[Critical] Fix frontend API endpoint mismatches** — Align `core/admin/api.ts` and `core/org/api.ts` with actual backend routes, or add the missing backend endpoints. At minimum: rename `/api/admin/usage` to `/api/admin/usage/summary` or update the frontend call; add `/api/admin/usage/by-org`; fix the `/api/org/members` vs `/api/admin/org/members` prefix mismatch; fix response unwrapping (plain array vs `{ organizations: [...] }`).

2. **[Critical] Wire up `set_request_auth_state` in `get_auth_context`** — The usage tracking middleware is inert until `set_request_auth_state(request, user_id, org_id)` is called from the auth dependency. Verify this is done in `auth.py` and add a test.

3. **[Critical] Implement LLM token tracking** — Add a LangChain `BaseCallbackHandler` that writes `llm_token` UsageRecord rows on `on_llm_end`. Inject it via the model factory as described in §3.5. This is the core billing data.

4. **[High] Separate platform admin from enterprise admin roles** — Introduce a `platform_admin` role (or a separate boolean flag on the user/member model). `_require_admin` for platform-wide endpoints should check for `platform_admin`, not the generic `admin` role.

5. **[High] Fix N+1 query in `list_organizations`** — Replace per-org `COUNT` queries with a single `LEFT JOIN` + `GROUP BY` query.

6. **[High] Add missing enterprise admin frontend** — Create `/workspace/settings/org` (or `/admin/org`) page that wires up `MemberTable` with `listOrgMembers`, `inviteMember`, `removeMember`, `updateMemberRole`, and `getOrgUsage`. The `MemberTable` component is complete but unused.

7. **[High] Add missing backend endpoints** — `GET /api/admin/usage/summary`, `GET /api/admin/usage/by-org`, `PUT /api/admin/organizations/{id}/quotas`, `POST /api/org/members/invite`, `PUT /api/org/members/{id}/role`, `GET /api/org/usage/by-user`.

8. **[Medium] Replace in-memory rate limiter with Redis** — Use `redis-py` async client with a sliding window or token bucket stored in Redis. The current implementation is not safe for multi-process deployments.

9. **[Medium] Load per-org RPM quotas from DB** — `RateLimiterMiddleware.org_quotas` should be populated from the database (or a cache) rather than being a static dict passed at startup.

10. **[Medium] Add pagination** — Add `limit`/`offset` (or cursor) parameters to `list_organizations` and `list_org_members`.

11. **[Low] Fix `QueryClient` instantiation in layout** — Move `new QueryClient()` inside a `useState` initializer to avoid shared state across renders.

12. **[Low] Deduplicate `formatNumber` helper** — The same function is copy-pasted in `admin/page.tsx`, `admin/usage/page.tsx`, and `org-table.tsx`. Extract to a shared utility.
