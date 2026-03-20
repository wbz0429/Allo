# CR Report: Auth + Multi-tenant (Phase 1)

## Summary

The Phase 1 auth + multi-tenant implementation is substantially complete and well-structured. The core auth pipeline — Better Auth (PostgreSQL adapter) → session cookie → `get_auth_context` dependency → `AuthContext(user_id, org_id, role)` — is correctly wired end-to-end. All new routers (config, admin, knowledge_bases, marketplace) properly use `Depends(get_auth_context)` and filter queries by `org_id`. However, the four legacy routers (agents, uploads, artifacts, memory/mcp/skills) authenticate the caller but do **not** scope data by `org_id`, leaving a multi-tenancy gap for those resources. Additional gaps: no `api_keys` DB table (plan requirement), no HTTPS, CORS reflects any origin, several new API routes are missing from the nginx config (requests fall through to the frontend), and the frontend middleware only checks cookie presence without server-side validation.

---

## Files Reviewed

- `backend/app/gateway/auth.py`
- `backend/app/gateway/db/models.py`
- `backend/app/gateway/db/database.py`
- `frontend/src/server/better-auth/config.ts`
- `frontend/src/server/better-auth/server.ts`
- `frontend/src/server/better-auth/index.ts`
- `frontend/src/server/better-auth/client.ts`
- `frontend/src/app/(auth)/login/page.tsx`
- `frontend/src/app/(auth)/register/page.tsx`
- `frontend/src/app/(auth)/layout.tsx`
- `frontend/src/app/api/auth/[...all]/route.ts`
- `frontend/src/middleware.ts`
- `backend/app/gateway/routers/agents.py`
- `backend/app/gateway/routers/uploads.py`
- `backend/app/gateway/routers/artifacts.py`
- `backend/app/gateway/routers/models.py`
- `backend/app/gateway/routers/memory.py`
- `backend/app/gateway/routers/mcp.py`
- `backend/app/gateway/routers/skills.py`
- `backend/app/gateway/routers/suggestions.py`
- `backend/app/gateway/routers/channels.py`
- `backend/app/gateway/routers/config.py`
- `backend/app/gateway/routers/admin.py`
- `backend/app/gateway/routers/knowledge_bases.py`
- `backend/app/gateway/routers/marketplace.py`
- `backend/app/gateway/app.py`
- `docker/nginx/nginx.conf`
- `docker/nginx/nginx.local.conf`

---

## Plan vs Implementation Gap Analysis

| Plan Requirement | Status | Notes |
|---|---|---|
| PostgreSQL data model — `organizations` table | ✅ Implemented | `Organization` model with id, name, slug, timestamps |
| PostgreSQL data model — `organization_members` table | ✅ Implemented | Links Better Auth user_id to org with role |
| PostgreSQL data model — `api_keys` table | ❌ Missing | Plan requires it for Phase 1; `auth.py` has a placeholder that always rejects API key auth |
| PostgreSQL data model — `threads` table | ❌ Missing | Plan lists threads as a Phase 1 DB model; threads still live in LangGraph/filesystem |
| Better Auth connected — PostgreSQL adapter | ✅ Implemented | `config.ts` uses `pg.Pool` with `DATABASE_URL` |
| Better Auth connected — email/password auth | ✅ Implemented | `emailAndPassword: { enabled: true }` |
| Better Auth connected — organization plugin | ⚠️ Partial | No `organization` plugin in Better Auth config; org creation is a manual `/api/auth/create-org` call that has no corresponding backend route |
| Better Auth connected — invitation system | ❌ Missing | Plan mentions enterprise invite codes; not implemented |
| Gateway auth middleware — session → user_id + org_id | ✅ Implemented | `get_auth_context` joins `session` + `organization_members` via raw SQL |
| Gateway auth middleware — SKIP_AUTH dev mode | ✅ Implemented | `SKIP_AUTH=1` returns a fixed dev context |
| Data isolation — new routers filter by org_id | ✅ Implemented | `config`, `admin`, `knowledge_bases`, `marketplace` all scope queries to `auth.org_id` |
| Data isolation — legacy routers filter by org_id | ❌ Missing | `agents`, `uploads`, `artifacts`, `memory`, `mcp`, `skills` authenticate but do not scope data by org_id |
| Frontend login page | ✅ Implemented | Functional form using `authClient.signIn.email`, redirects to `/workspace` |
| Frontend register page | ✅ Implemented | Functional form with org name field; calls `authClient.signUp.email` |
| Frontend register — org creation after signup | ⚠️ Broken | Calls `POST /api/auth/create-org` which does not exist in the backend; org creation silently fails |
| Frontend middleware protects `/workspace` | ✅ Implemented | `middleware.ts` redirects unauthenticated users to `/login` with `callbackUrl` |
| HTTPS | ❌ Missing | Both nginx configs are HTTP-only on port 2026; no TLS termination |
| CORS tightening | ⚠️ Partial | Nginx reflects `$http_origin` (not `*`), but allows any origin; no allowlist |
| Checkpointer switch to PostgreSQL | ⚠️ Not verified | Out of scope for this review; not visible in reviewed files |
| Nginx routes for new API endpoints | ❌ Missing | `/api/config`, `/api/admin`, `/api/knowledge-bases`, `/api/marketplace`, `/api/channels`, `/api/user-profile` have no nginx location blocks; requests fall through to the frontend |

---

## Code Quality Issues

- **`auth.py:53`** — Raw SQL string for session lookup. The query uses camelCase column names (`"userId"`, `"expiresAt"`) that are Better Auth's internal schema. If Better Auth changes its schema these will silently break. Consider a comment documenting the dependency on Better Auth's internal table structure.

- **`auth.py:95`** — API key extraction has an off-by-one: `auth_header[len("Bearer "):]` correctly strips the prefix, but the guard `if auth_header.startswith("Bearer df-")` means only `df-` prefixed tokens are attempted. A plain `Bearer <key>` header is silently ignored and falls through to the 401. This is fine for Phase 1 but should be documented.

- **`models.py:52`** — `OrganizationMember.user_id` is a bare `String(36)` with no foreign key to a `user` table. Better Auth manages the `user` table, so there is no SQLAlchemy model for it. This means referential integrity is not enforced at the DB level. A raw FK to `"user"."id"` (Better Auth's table) would be safer.

- **`models.py` — `__init__` duplication** — Every model manually re-implements default injection in `__init__` (e.g., `if "id" not in kwargs: kwargs["id"] = str(uuid.uuid4())`). This duplicates what `insert_default` already does at the column level. The `__init__` overrides are redundant and could be removed.

- **`database.py`** — No connection pool configuration (`pool_size`, `max_overflow`, `pool_timeout`). The default asyncpg pool is 5 connections. Under load this will exhaust quickly. Should be configurable via env vars.

- **`app.py:52-58`** — `Base.metadata.create_all` at startup is acceptable for Phase 1 but the comment says "Alembic migrations in Phase 2." This should be tracked as a hard blocker before any production deployment.

- **`register/page.tsx:49`** — `POST /api/auth/create-org` is called after signup but this route does not exist. The `catch` block silently swallows the error. Users will register successfully but have no organization, causing all subsequent `get_auth_context` calls to return `None` (no org membership row) and result in 401s everywhere.

- **`middleware.ts:16-23`** — Cookie presence check only. The middleware does not validate the session token against the database or Better Auth's session API. An expired or revoked token will still pass the middleware check. The actual 401 will only surface when the first API call hits `get_auth_context`. This is a UX issue (user sees workspace briefly before being kicked) and a minor security concern.

- **`better-auth/config.ts`** — No `trustedOrigins` configured. Better Auth defaults to allowing requests from any origin for its own endpoints. Should be locked to the app's domain in production.

- **`better-auth/config.ts`** — No `session` configuration (expiry, cookie options). Default session lifetime and cookie flags (Secure, SameSite) are not explicitly set. In production, `Secure: true` and `SameSite: Lax` should be enforced.

---

## Security / Architecture Concerns

1. **No org_id isolation on legacy routers.** `agents`, `uploads`, `artifacts`, `memory`, `mcp`, and `skills` all authenticate the caller but operate on global filesystem paths (`get_paths()` returns a single shared base dir). Any authenticated user from any org can read/write any other org's agents, uploads, and artifacts by guessing thread IDs or agent names. This is the most critical security gap for a multi-tenant deployment.

2. **Nginx missing routes for new API prefixes.** `/api/config`, `/api/admin`, `/api/knowledge-bases`, `/api/marketplace`, `/api/channels` are not in either nginx config. Requests to these endpoints will be proxied to the Next.js frontend, which will return 404. The new features are effectively unreachable through nginx.

3. **CORS reflects any origin.** `add_header 'Access-Control-Allow-Origin' $http_origin always` combined with `add_header 'Access-Control-Allow-Credentials' 'true' always` is equivalent to `*` with credentials, which browsers reject — but it also means any origin can make credentialed requests if the browser allows it. An explicit allowlist (`$allowed_origin` map) is needed.

4. **No HTTPS.** Both nginx configs are HTTP-only. Session cookies transmitted over HTTP are vulnerable to interception. The `better-auth.session_token` cookie should have `Secure` flag set, which requires HTTPS.

5. **`/api/auth/create-org` endpoint missing.** The register flow calls this endpoint but it doesn't exist. New users end up with no org membership, making the entire auth system non-functional for new registrations in production.

6. **Platform admin check is role-based, not user-based.** `_require_admin` in `admin.py` checks `auth.role == "admin"` which is the org-level role. This means any org admin can call `GET /api/admin/organizations` and see all organizations on the platform. There is no distinction between "platform superadmin" and "org admin." The plan describes a two-tier admin model; the current implementation conflates them.

7. **`OrganizationMember.user_id` has no unique constraint per org.** A user could theoretically be added to the same org multiple times, and `_resolve_session_from_db` uses `LIMIT 1` which would return an arbitrary row. A `UniqueConstraint("org_id", "user_id")` should be added.

8. **`database.py` DATABASE_URL default.** The default `postgresql+asyncpg://postgres:postgres@localhost:5432/deerflow` has hardcoded credentials. If `DATABASE_URL` is not set in production, the app will attempt to connect with these credentials. Should fail loudly if not set.

---

## Recommendations

Prioritized by severity:

1. **[Critical] Add `/api/auth/create-org` backend endpoint** — Without this, new user registration is broken. Should create an `Organization` + `OrganizationMember(role="admin")` row for the newly registered user. Can be a simple POST handler in a new `routers/orgs.py` or added to `admin.py`.

2. **[Critical] Add nginx location blocks for all new API prefixes** — Add `location /api/config`, `location /api/admin`, `location /api/knowledge-bases`, `location /api/marketplace`, `location /api/channels` to both `nginx.conf` and `nginx.local.conf` pointing to the gateway upstream. Consider a single catch-all `location /api/` block to avoid this class of omission in the future.

3. **[Critical] Scope legacy routers by org_id** — `agents`, `uploads`, `artifacts` need `get_paths()` to accept an `org_id` prefix (the plan already calls this out in Section 3.5 — `config/paths.py` tenant prefix). Until then, data from different orgs is co-mingled on the filesystem.

4. **[High] Add `api_keys` DB table** — Required by Phase 1 plan. The placeholder in `auth.py` already has the hook; the table and CRUD endpoints just need to be built.

5. **[High] Add `UniqueConstraint("org_id", "user_id")` to `OrganizationMember`** — Prevents duplicate memberships and makes the session lookup deterministic.

6. **[High] Fix middleware to validate session server-side** — Either call `auth.api.getSession()` in middleware or use Better Auth's `betterFetch` to verify the token. Cookie presence alone is not sufficient.

7. **[Medium] Add nginx CORS allowlist** — Replace `$http_origin` with a map-based allowlist of known frontend origins. This is especially important before HTTPS is enabled.

8. **[Medium] Configure Better Auth `trustedOrigins` and session cookie options** — Set `Secure: true`, `SameSite: "lax"`, and explicit session expiry in `config.ts`.

9. **[Medium] Separate platform superadmin from org admin** — Add a `is_platform_admin` flag to the user table (or a separate `platform_admins` table) and check it in `admin.py` for cross-org endpoints like `GET /api/admin/organizations`.

10. **[Medium] Add connection pool config to `database.py`** — Expose `pool_size`, `max_overflow` via env vars. Default of 5 connections is too low for production.

11. **[Low] Remove redundant `__init__` methods from DB models** — `insert_default` at the column level is sufficient; the manual `__init__` overrides add noise without benefit.

12. **[Low] Plan HTTPS before production** — Add TLS termination to nginx (Let's Encrypt or cert-manager). This is a hard requirement before any real user data is stored.
