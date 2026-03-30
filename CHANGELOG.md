# Changelog

## Multi-tenant refactoring

### Summary

Allo was refactored from a primarily single-user local setup into a multi-tenant architecture with user-scoped authentication, storage, thread lifecycle management, and runtime isolation. The system now separates platform-level configuration from per-user data, routes authenticated LangGraph traffic through nginx header injection, and prepares the stack for production-style deployment with PostgreSQL, Redis, and Alembic-managed schema migrations.

### Sprint 1: infrastructure and auth foundation

- Added Alembic migration infrastructure and baseline/auth migrations for managed schema evolution.
- Added auth data models and tables for `users` and `sessions`.
- Added Redis integration for session caching and rate-limit state.
- Added gateway auth APIs for register, login, logout, session lookup, and nginx auth checks.
- Added users API for reading and updating the current user profile.
- Added nginx auth-request configuration for protecting LangGraph traffic and injecting tenant context.
- Added per-user path helpers and directory conventions under user- and thread-scoped storage roots.
- Updated the skills loader to support public skills plus user custom skills with per-user toggles.
- Updated the memory updater to support store-backed persistence with backward-compatible fallback behavior.
- Updated the MCP cache to support user-scoped cache keys and config loading.
- Updated the checkpointer configuration to support PostgreSQL via `CHECKPOINT_POSTGRES_URI`.

### Sprint 2: data isolation and tenant-aware runtime behavior

- Added thread and thread-run persistence for gateway-managed thread lifecycle operations.
- Added PostgreSQL-backed store implementations for memory, soul, skill config, MCP config, and model key resolution.
- Added management APIs and user filtering for soul, memory, MCP, agents, skills, and API-key workflows.
- Refactored agent startup and prompt-building paths to load soul, memory, skills, and MCP state per user.
- Added thread data middleware support for creating and using per-user thread directories.
- Added virtual path mapping updates for per-user workspaces, uploads, outputs, temp directories, and custom skills, including path traversal protection.
- Replaced frontend Better Auth integration with gateway-based auth APIs.
- Refactored frontend thread hooks to create, list, rename, delete, and track thread runs through gateway APIs while preserving LangGraph streaming.

### Breaking changes

- Removed Better Auth integration from the frontend and auth flow.
- Changed the session cookie name from `better-auth.session_token` to `session_token`.
- Multi-tenant deployments now rely on PostgreSQL and Redis-backed infrastructure rather than local-only auth/session assumptions.

### New dependencies

- `redis[hiredis]>=5.0`
- `bcrypt>=4.0`
- `alembic>=1.13`

### Required environment variables

The multi-tenant setup requires the following environment variables:

- `DATABASE_URL` — PostgreSQL connection string for gateway data and migrations.
- `REDIS_URL` — Redis connection string for session caching and rate limiting.
- `CHECKPOINT_POSTGRES_URI` — PostgreSQL connection string for LangGraph checkpoint persistence.
- `SESSION_SECRET` — session-signing or session-related application secret required by deployment configuration.
- `API_KEY_ENCRYPTION_SECRET` — secret used for encrypting stored user API keys.
