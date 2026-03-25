# AGENTS.md

Guidance for AI coding agents working in the Allo（元枢） repository.

## Project Overview

Allo（元枢） is a full-stack AI office assistant platform. Python backend (LangGraph + FastAPI) and Next.js frontend (React 19 + TypeScript). Nginx reverse proxy unifies all services on port 2026.

## Build / Lint / Test Commands

### Bootstrap

```bash
make check      # Verify prerequisites (node, pnpm, python, uv, nginx)
make install    # Install all deps (backend: uv sync, frontend: pnpm install)
```

### Backend (run from `backend/`)

```bash
make lint                  # Lint with ruff
make format                # Auto-fix lint + format with ruff
make test                  # Run all tests: PYTHONPATH=. uv run pytest tests/ -v
make dev                   # Start LangGraph server (port 2024)
make gateway               # Start Gateway API (port 8001)
```

Run a single test file:
```bash
PYTHONPATH=. uv run pytest tests/test_model_factory.py -v
```

Run a single test function:
```bash
PYTHONPATH=. uv run pytest tests/test_model_factory.py::test_create_chat_model_with_valid_name -v
```

### Frontend (run from `frontend/`)

```bash
pnpm lint                  # ESLint
pnpm lint:fix              # ESLint with auto-fix
pnpm typecheck             # tsc --noEmit
pnpm dev                   # Dev server with Turbopack (port 3000)
pnpm build                 # Production build (needs BETTER_AUTH_SECRET)
```

**Do NOT use `pnpm check`** -- it is broken. Run `pnpm lint` and `pnpm typecheck` separately.

No test framework is configured for the frontend.

### Full Application (run from project root)

```bash
make dev       # Start all services (LangGraph + Gateway + Frontend + Nginx)
make stop      # Stop all services
```

### Pre-commit Checklist

1. Backend: `cd backend && make lint && make test`
2. Frontend (if touched): `cd frontend && pnpm lint && pnpm typecheck`
3. Frontend build (if env/auth/routing changed): `BETTER_AUTH_SECRET=local-dev-secret pnpm build`

CI runs backend lint + test on every PR (`.github/workflows/backend-unit-tests.yml`).

## Code Style -- Python (Backend)

### Formatting (ruff)

- **Line length**: 240
- **Target**: Python 3.12
- **Quotes**: double
- **Indent**: spaces
- **Lint rules**: E (pycodestyle), F (pyflakes), I (isort), UP (pyupgrade)

### Imports

Three groups separated by blank lines, enforced by ruff isort:
1. Standard library
2. Third-party
3. First-party (`deerflow.*`, `app.*`)

```python
import logging

from langchain_core.runnables import RunnableConfig

from deerflow.config import get_app_config
```

### Naming

| Entity | Convention | Example |
|---|---|---|
| Files / modules | `snake_case` | `app_config.py` |
| Classes / Pydantic models | `PascalCase` | `AppConfig`, `ThreadState` |
| Functions | `snake_case` | `create_chat_model()` |
| Private | `_snake_case` | `_resolve_model_name()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_CONCURRENT_SUBAGENTS` |
| Tests | `test_<feature>.py`, `test_<desc>()` | `test_model_factory.py` |

### Types

- Use modern Python 3.12+ syntax: `str | None` (not `Optional[str]`)
- Use `Annotated` for custom reducers
- Use `TypedDict` with `NotRequired` for optional fields
- Pydantic v2 API: `BaseModel`, `Field()`, `model_dump()`, `model_validate()`
- Google-style docstrings with `Args:` and `Returns:` sections

### Error Handling

- **Tool functions** return error strings; never raise exceptions.
- **Gateway routers** raise `HTTPException` with appropriate status codes.
- **Optional features** degrade gracefully with `try/except ImportError` + logger.warning.

### Architecture Boundary

Strict dependency direction enforced by `tests/test_harness_boundary.py`:
- `deerflow.*` (harness) -- publishable framework, NEVER imports `app.*`
- `app.*` -- application code, imports `deerflow.*`

## Code Style -- TypeScript (Frontend)

### Formatting

ESLint flat config + Prettier with `prettier-plugin-tailwindcss`. Strict TypeScript (`tsconfig.json` has `strict: true`, `verbatimModuleSyntax: true`).

### Imports

Enforced by ESLint `import/order`: groups separated by blank lines, alphabetized within each group.

1. External (`react`, `@langchain/*`, `@tanstack/*`)
2. Internal via `@/*` alias (`@/components/...`, `@/core/...`)
3. Parent (`../api`)
4. Sibling (`./types`)

Use **inline type imports** (`import { type Foo }` not `import type { Foo }`):
```typescript
import { useCallback, useState, type ComponentProps } from "react";
```

Pure type-only imports may use the `import type` form:
```typescript
import type { AIMessage } from "@langchain/langgraph-sdk";
```

### Naming

| Entity | Convention | Example |
|---|---|---|
| Files / directories | `kebab-case` | `input-box.tsx`, `ai-elements/` |
| Components | `PascalCase` | `InputBox`, `WorkspaceContainer` |
| Hooks | `use` prefix, `camelCase` | `useThreadStream` |
| Functions / variables | `camelCase` | `getAPIClient()`, `threadId` |
| Types / interfaces | `PascalCase` | `AgentThread`, `AgentThreadState` |
| Constants | `UPPER_SNAKE_CASE` | `MOBILE_BREAKPOINT` |
| Unused params | `_` prefix | `_threadId` |

### Error Handling

- User-facing errors: `toast.error(message)` from `sonner`
- Fetch failures: graceful degradation with `.catch(() => fallback)`
- Console: `console.error()` for unexpected errors

### Key Patterns

- Path alias: `@/*` maps to `src/*`
- Class names: use `cn()` from `@/lib/utils` (clsx + tailwind-merge)
- `"use client"` directive only for components with hooks/state
- `components/ui/` and `components/ai-elements/` are auto-generated (Shadcn/MagicUI) -- do not edit manually
- Barrel exports via `index.ts` with named exports (no default exports from business logic)

## Project Structure

```
deer-flow/
  Makefile                          # Root commands (check, install, dev, stop)
  config.yaml                       # Main app config (gitignored, copy from config.example.yaml)
  extensions_config.json            # MCP + skills config (gitignored)
  backend/
    packages/harness/deerflow/      # Harness framework (import: deerflow.*)
    app/gateway/                    # FastAPI Gateway (import: app.*)
    tests/                          # pytest tests (flat: test_<feature>.py)
    ruff.toml                       # Lint/format config
    pyproject.toml                  # Python deps (>=3.12)
    langgraph.json                  # LangGraph entry point
  frontend/
    src/app/                        # Next.js App Router
    src/components/                 # React components
    src/core/                       # Business logic (threads, api, models, etc.)
    eslint.config.js                # ESLint flat config
    tsconfig.json                   # TypeScript config
    package.json                    # pnpm scripts
  skills/public/                    # Built-in agent skills
  docker/                           # Docker + nginx configs
```

## Copilot Instructions Reference

See `.github/copilot-instructions.md` for verified command sequences, known failure modes, and gotchas. Key points:
- `BETTER_AUTH_SECRET` is required for frontend production builds. Set it or use `SKIP_ENV_VALIDATION=1`.
- Proxy env vars can break `pnpm install`.
- `make config` is non-idempotent by design (aborts if config.yaml exists).

## Known Issues / TODOs

- **`.env` path mismatch**: `langgraph.json` declares `"env": ".env"` relative to `backend/`, but `make config` generates `.env` in the project root. LangGraph server cannot read environment variables unless `backend/.env` exists (e.g. via symlink `ln -s ../.env backend/.env`). This should be fixed upstream — either change `langgraph.json` to `"env": "../.env"`, or have `make config` / `configure.py` also create `backend/.env`.

## Additional Documentation

- `backend/CLAUDE.md` -- detailed backend architecture (511 lines)
- `frontend/CLAUDE.md` -- frontend architecture and data flow
- `backend/CONTRIBUTING.md` -- contributor guide
- `backend/docs/` -- feature-specific docs (config, API, file upload, plan mode, summarization)
