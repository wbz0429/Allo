# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Allo (元枢) is a full-stack AI office assistant platform built on DeerFlow, a LangGraph-based "super agent harness." Python backend (LangGraph + FastAPI), Next.js frontend (React 19 + TypeScript), with an optional Tauri desktop shell and a separate sync service.

## Build / Lint / Test Commands

### Prerequisites

```bash
make check      # Verify: node >=22, pnpm, python >=3.12, uv, nginx
make install    # Install all deps (backend: uv sync, frontend: pnpm install)
```

### Full Application (from project root)

```bash
make dev        # Start all services (LangGraph + Gateway + Frontend + Nginx)
make stop       # Stop all services
```

App available at `http://localhost:2026` via nginx reverse proxy.

### Backend (from `backend/`)

```bash
make dev                   # LangGraph server (port 2024)
make gateway               # Gateway API (port 8001)
make lint                  # ruff check .
make format                # ruff check --fix + ruff format
make test                  # PYTHONPATH=. uv run pytest tests/ -v
```

Single test file: `PYTHONPATH=. uv run pytest tests/test_model_factory.py -v`
Single test function: `PYTHONPATH=. uv run pytest tests/test_model_factory.py::test_create_chat_model_with_valid_name -v`

### Frontend (from `frontend/`)

```bash
pnpm dev                   # Dev server with Turbopack (port 3000)
pnpm lint                  # ESLint
pnpm lint:fix              # ESLint with auto-fix
pnpm typecheck             # tsc --noEmit
pnpm build                 # Production build (requires BETTER_AUTH_SECRET)
```

**Do NOT use `pnpm check`** — it is broken. Run `pnpm lint` and `pnpm typecheck` separately.

No test framework is configured for the frontend.

### Pre-commit Checklist

1. Backend: `cd backend && make lint && make test`
2. Frontend (if touched): `cd frontend && pnpm lint && pnpm typecheck`
3. Frontend build (if env/auth/routing changed): `BETTER_AUTH_SECRET=local-dev-secret pnpm build`

CI runs backend lint + test on every PR (`.github/workflows/backend-unit-tests.yml`).

## Architecture

### Service Topology

```
Browser → nginx (2026)
            ├── /api/langgraph/* → LangGraph Server (2024)
            ├── /api/*           → Gateway API (8001)
            └── /*               → Next.js Frontend (3000)
```

### Monorepo Layout

- `backend/` — Python backend with two layers (see below)
- `frontend/` — Next.js 16 App Router frontend
- `desktop/` — Tauri v2 desktop shell (bundles standalone frontend + Node + Python sidecar)
- `sync-service/` — Separate FastAPI service for desktop multi-device sync
- `docker/` — Docker Compose configs and nginx
- `skills/` — Agent skill packs (`public/` committed, `custom/` gitignored)
- `scripts/` — Build, deploy, and orchestration scripts

### Backend: Harness / App Split

Strict dependency boundary enforced by `tests/test_harness_boundary.py` (runs in CI):

- **Harness** (`backend/packages/harness/deerflow/`) — Publishable agent framework. Import prefix: `deerflow.*`. Contains agent orchestration, tools, sandbox, models, MCP, skills, config, memory.
- **App** (`backend/app/`) — Application layer. Import prefix: `app.*`. Contains FastAPI Gateway (`app/gateway/`) and IM channel integrations (`app/channels/`).

**Rule**: App imports deerflow. Deerflow NEVER imports app.

Key backend subsystems:
- **Lead Agent** — Entry point `deerflow.agents:make_lead_agent` registered in `langgraph.json`
- **Middleware Chain** — 11 ordered middlewares (thread data, uploads, sandbox, dangling tool calls, summarization, todo list, title, memory, view image, subagent limit, clarification)
- **Sandbox** — Abstract interface with local filesystem and Docker-based providers; virtual path system (`/mnt/user-data/...` → physical paths)
- **Subagents** — `general-purpose` and `bash` built-ins; dual thread pool execution, max 3 concurrent
- **MCP** — Multi-server management with lazy init, mtime-based cache invalidation, OAuth support
- **Memory** — LLM-based fact extraction, debounced queue, atomic file I/O, injected into system prompt
- **IM Channels** — Feishu, Slack, Telegram bridges to LangGraph via langgraph-sdk

### Frontend Architecture

Stack: Next.js 16, React 19, TypeScript 5.8, Tailwind CSS 4, pnpm

Key source areas under `frontend/src/`:
- `app/` — App Router routes: `/`, `/workspace/chats/[thread_id]`, `/admin`, `/(auth)/login`, `/setup`
- `components/` — `ui/` and `ai-elements/` are auto-generated (Shadcn/MagicUI/Vercel AI) — don't edit manually
- `core/` — Business logic: `threads/` (streaming hooks), `api/` (LangGraph client singleton), `artifacts/`, `i18n/`, `models/`, `memory/`, `skills/`, `mcp/`

Data flow: User input → thread hooks (`core/threads/hooks.ts`) → LangGraph SDK streaming → TanStack Query for server state, localStorage for user settings.

### Auth System

- Frontend uses Better Auth-shaped cookie auth (`better-auth.session_token`)
- Backend validates session token against DB `session` table, resolves org membership
- Two modes controlled by `ALLO_MODE` env var:
  - `development` — local dev JSON session store, optional `SKIP_AUTH=1`
  - `appliance` — strict DB-backed auth only, no dev fallbacks

### Configuration

- `config.yaml` (project root, gitignored) — Main app config. Copy from `config.example.yaml`. Has `config_version` for schema upgrades (`make config-upgrade`).
- `extensions_config.json` (project root, gitignored) — MCP servers and skills config. Copy from `extensions_config.example.json`.
- `.env` (project root) — Environment variables. Note: LangGraph server needs `backend/.env` (symlink or copy).
- `BETTER_AUTH_SECRET` — Required for frontend production builds.

### Database

- PostgreSQL via async SQLAlchemy + asyncpg
- Default: `postgresql+asyncpg://{USER}@localhost:5432/deerflow`
- Schema created via `Base.metadata.create_all()` on gateway startup (no Alembic yet)

## Code Style

### Python (Backend)

- ruff: line length 240, Python 3.12 target, double quotes, spaces
- Imports: stdlib → third-party → first-party (`deerflow.*`, `app.*`), enforced by ruff isort
- Types: `str | None` (not `Optional`), Pydantic v2 API, `TypedDict` with `NotRequired`
- Tool functions return error strings, never raise. Gateway routers raise `HTTPException`.

### TypeScript (Frontend)

- ESLint flat config + Prettier with `prettier-plugin-tailwindcss`, strict TypeScript
- Imports: external → internal (`@/*`) → parent → sibling, alphabetized within groups
- Inline type imports: `import { type Foo }` preferred over `import type { Foo }`
- Files/dirs: `kebab-case`. Components: `PascalCase`. Path alias: `@/*` → `src/*`
- Class names: use `cn()` from `@/lib/utils` (clsx + tailwind-merge)
- `"use client"` only for components with hooks/state

## Gotchas

- `pnpm check` is broken — use `pnpm lint` + `pnpm typecheck` instead
- `make config` aborts if `config.yaml` already exists (by design)
- Proxy env vars can break `pnpm install`
- `.env` path mismatch: `langgraph.json` expects `.env` relative to `backend/`, but `make config` generates it at project root. Symlink `ln -s ../.env backend/.env` if needed.
- `BETTER_AUTH_SECRET` required for frontend prod builds. Workaround: `SKIP_ENV_VALIDATION=1`

## Detailed Documentation

- `backend/CLAUDE.md` — Detailed backend architecture (511 lines)
- `frontend/CLAUDE.md` — Frontend architecture and data flow
- `backend/docs/` — Feature docs (config, API, file upload, plan mode, summarization)
- `.github/copilot-instructions.md` — Verified command sequences and known failure modes
