# Phase 4 Contract: Admin Dashboard + Usage Tracking + Rate Limiting

## Overview
Implement platform admin dashboard, enterprise admin panel, token usage tracking, rate limiting, and billing foundations.

## Execution Phases
### Phase A (parallel)
- role: "backend-admin" — Usage tracking middleware, usage models, admin API, rate limiting, tests
- role: "frontend-admin" — Platform admin dashboard, enterprise admin panel, usage charts

---

## Shared Interfaces

### Usage Tracking DB Models
```python
class UsageRecord(Base):
    __tablename__ = "usage_records"
    id: str
    org_id: str          # FK organizations
    user_id: str
    record_type: str     # "llm_token" | "api_call" | "sandbox_time" | "storage"
    model_name: str      # nullable, for llm_token type
    input_tokens: int    # for llm_token
    output_tokens: int   # for llm_token
    endpoint: str        # for api_call
    duration_seconds: float  # for sandbox_time
    created_at: datetime
```

### Admin API Endpoints
```
# Platform Admin (super admin only)
GET    /api/admin/organizations              # List all orgs with usage summary
GET    /api/admin/organizations/{id}         # Org detail
PUT    /api/admin/organizations/{id}/quotas  # Update org quotas
GET    /api/admin/usage/summary              # Global usage stats
GET    /api/admin/usage/by-org               # Usage breakdown by org

# Enterprise Admin (org admin)
GET    /api/org/members                      # List org members
POST   /api/org/members/invite               # Invite member
DELETE /api/org/members/{user_id}            # Remove member
PUT    /api/org/members/{user_id}/role       # Change role
GET    /api/org/usage                        # Org usage stats
GET    /api/org/usage/by-user                # Usage by user in org
```

### Rate Limiting
- In-memory token bucket per org_id (Redis later)
- Configurable RPM per org tier
- Return 429 with Retry-After header

---

## Role: backend-admin

### Owned Files
- `backend/app/gateway/db/models.py` (MODIFY) — add UsageRecord
- `backend/app/gateway/routers/admin.py` (NEW) — platform admin endpoints
- `backend/app/gateway/routers/org_admin.py` (NEW) — enterprise admin endpoints
- `backend/app/gateway/middleware/` (NEW directory)
  - `__init__.py`
  - `usage_tracking.py` — FastAPI middleware to log API calls
  - `rate_limiter.py` — token bucket rate limiter
- `backend/app/gateway/app.py` (MODIFY) — register admin routers + middleware
- `backend/tests/test_usage_models.py` (NEW)
- `backend/tests/test_admin_router.py` (NEW)
- `backend/tests/test_rate_limiter.py` (NEW)

### Must Do
- UsageRecord model for tracking all usage types
- Usage tracking middleware: log every API call with org_id, user_id, endpoint, timestamp
- Rate limiter: in-memory token bucket, per org_id, configurable RPM
- Platform admin: require role="super_admin" (check auth.role)
- Enterprise admin: require role="admin" within the org
- Usage summary: aggregate by day/week/month
- All new endpoints require AuthContext
- Unit tests for models, middleware, rate limiter

### Must NOT Do
- Do NOT modify harness files
- Do NOT modify frontend files
- Do NOT implement Stripe/payment integration (future)
- Do NOT use Redis (use in-memory for now)

---

## Role: frontend-admin

### Owned Files
- `frontend/src/app/admin/` (NEW directory) — platform admin pages
  - `layout.tsx`
  - `page.tsx` — dashboard overview
  - `organizations/page.tsx` — org list
  - `usage/page.tsx` — global usage charts
- `frontend/src/app/workspace/settings/org/` (NEW directory) — enterprise admin
  - `page.tsx` — org settings (members, usage)
- `frontend/src/core/admin/` (NEW directory)
  - `api.ts` — admin API client
  - `types.ts` — admin types
- `frontend/src/core/org/` (NEW directory)
  - `api.ts` — org admin API client
  - `types.ts` — org types
- `frontend/src/components/admin/` (NEW directory)
  - `usage-chart.tsx` — simple bar/line chart (CSS-only, no chart lib)
  - `org-table.tsx` — organizations table
  - `member-table.tsx` — members table

### Must Do
- Platform admin dashboard: org count, total usage, recent activity
- Org list: table with name, member count, usage, created date
- Usage page: simple bar charts showing daily token usage (CSS-based, no external chart lib)
- Enterprise admin: member list with invite/remove/role change
- Org usage: usage breakdown by user
- Protect /admin/* routes (check if user is super_admin)
- Use Shadcn Table, Card, Button, Badge, Dialog
- All fetches include credentials: "include"

### Must NOT Do
- Do NOT modify backend Python files
- Do NOT install chart libraries (use CSS-based charts)
- Do NOT implement payment/billing UI
