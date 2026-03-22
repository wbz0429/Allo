# Report-Driven Fix Contract

> Scope: 全量处理 `/Users/wbz/deer-flow/.dfcode/reports` 下的 report，按领域拆分给并行 worker 进行检查、修复、各自验证；合并后再做一次全局验证与补漏。

## docMode

- `summary`

## Roles

### 1. `auth-foundation`

**Agent**: `worker-backend`

**Owns files/directories**

- `backend/app/gateway/auth.py`
- `backend/app/gateway/app.py`
- `backend/app/gateway/routers/agents.py`
- `backend/app/gateway/routers/uploads.py`
- `backend/app/gateway/routers/artifacts.py`
- `backend/app/gateway/routers/memory.py`
- `backend/app/gateway/routers/mcp.py`
- `backend/app/gateway/routers/skills.py`
- `backend/app/gateway/routers/channels.py`
- `backend/app/gateway/db/models.py`（仅 `Organization` / `OrganizationMember` / auth 相关约束）
- `docker/nginx/nginx.conf`
- `docker/nginx/nginx.local.conf`
- `frontend/src/server/better-auth/config.ts`
- `frontend/src/server/better-auth/server.ts`
- `frontend/src/server/better-auth/index.ts`
- `frontend/src/server/better-auth/client.ts`
- `frontend/src/app/api/auth/[...all]/route.ts`
- `frontend/src/app/(auth)/login/page.tsx`
- `frontend/src/app/(auth)/register/page.tsx`
- `frontend/src/app/(auth)/layout.tsx`
- `frontend/src/middleware.ts`
- auth / nginx 相关测试文件

**Responsibilities**

- 根据 `cr-auth.md` 与 `cr-testing-report.md` 修复认证、注册、租户隔离、nginx API 转发、Better Auth 可信来源与 session 行为问题
- 只在自己拥有的文件内处理 legacy router 的 org 隔离问题
- 若需要改共享接口，必须遵守下方 Shared Interfaces

### 2. `config-wizard`

**Agent**: `worker-frontend`

**Owns files/directories**

- `backend/app/gateway/routers/config.py`
- `backend/app/gateway/db/models.py`（仅 `TenantConfig` 相关）
- `frontend/src/core/config/api.ts`
- `frontend/src/core/config/types.ts`
- `frontend/src/core/config/hooks.ts`
- `frontend/src/core/config/index.ts`
- `frontend/src/components/workspace/setup-wizard/setup-wizard.tsx`
- `frontend/src/components/workspace/setup-wizard/model-selection-step.tsx`
- `frontend/src/components/workspace/setup-wizard/tool-selection-step.tsx`
- `frontend/src/components/workspace/setup-wizard/agent-setup-step.tsx`
- `frontend/src/components/workspace/setup-wizard/completion-step.tsx`
- `frontend/src/app/workspace/setup/page.tsx`
- `frontend/src/app/workspace/setup/layout.tsx`
- config 相关测试文件

**Responsibilities**

- 根据 `cr-config.md` 修复 config API contract、导入导出、类型对齐、setup wizard 缺失/占位逻辑
- 不修改 auth / rag / admin / marketplace 领域文件

### 3. `rag-knowledge`

**Agent**: `worker-backend`

**Owns files/directories**

- `backend/app/gateway/routers/knowledge_bases.py`
- `backend/app/gateway/rag/chunker.py`
- `backend/app/gateway/rag/embedder.py`
- `backend/app/gateway/rag/retriever.py`
- `backend/app/gateway/db/models.py`（仅 `KnowledgeBase` / `KnowledgeDocument` / `KnowledgeChunk`）
- `backend/packages/harness/deerflow/config/agents_config.py`
- `backend/packages/harness/deerflow/agents/lead_agent/prompt.py`
- `frontend/src/core/knowledge/api.ts`
- `frontend/src/core/knowledge/types.ts`
- `frontend/src/core/knowledge/hooks.ts`
- `frontend/src/core/knowledge/api.test.ts`
- `frontend/src/components/workspace/knowledge/kb-card.tsx`
- `frontend/src/components/workspace/knowledge/document-list.tsx`
- `frontend/src/components/workspace/knowledge/document-upload.tsx`
- `frontend/src/components/workspace/knowledge/search-panel.tsx`
- `frontend/src/app/workspace/knowledge/page.tsx`
- `frontend/src/app/workspace/knowledge/[id]/page.tsx`
- `frontend/src/app/workspace/knowledge/layout.tsx`
- RAG / knowledge 相关测试文件

**Responsibilities**

- 根据 `cr-rag.md` 与 `cr-testing-report.md` 修复 KB API shape、上传/搜索链路、embedder/retriever 问题、前端类型与页面问题
- 在自己拥有的 harness 文件中补齐 knowledge-base 绑定 / prompt integration（若当前代码结构允许）

### 4. `admin-usage`

**Agent**: `worker-backend`

**Owns files/directories**

- `backend/app/gateway/routers/admin.py`
- `backend/app/gateway/middleware/usage_tracking.py`
- `backend/app/gateway/middleware/rate_limiter.py`
- `backend/app/gateway/db/models.py`（仅 `UsageRecord` 与 admin/usage 相关 schema）
- `frontend/src/core/admin/api.ts`
- `frontend/src/core/admin/types.ts`
- `frontend/src/core/org/api.ts`
- `frontend/src/core/org/types.ts`
- `frontend/src/app/admin/layout.tsx`
- `frontend/src/app/admin/page.tsx`
- `frontend/src/app/admin/organizations/page.tsx`
- `frontend/src/app/admin/usage/page.tsx`
- `frontend/src/components/admin/org-table.tsx`
- `frontend/src/components/admin/member-table.tsx`
- `frontend/src/components/admin/usage-chart.tsx`
- admin / middleware / org 相关测试文件

**Responsibilities**

- 根据 `cr-admin.md` 与 `cr-testing-report.md` 修复 admin API、frontend endpoint mismatch、usage tracking / rate limiter 行为与注册、enterprise admin 页面接线问题
- 不修改 auth.py；若依赖 auth contract，按 Shared Interfaces 假设其对 request.state 的写入已存在

### 5. `marketplace`

**Agent**: `worker-frontend`

**Owns files/directories**

- `backend/app/gateway/routers/marketplace.py`
- `backend/app/gateway/marketplace_seed.py`
- `backend/app/gateway/db/models.py`（仅 marketplace 相关 schema）
- `frontend/src/core/marketplace/api.ts`
- `frontend/src/core/marketplace/types.ts`
- `frontend/src/app/workspace/marketplace/page.tsx`
- `frontend/src/app/workspace/marketplace/layout.tsx`
- `frontend/src/components/workspace/marketplace/tool-card.tsx`
- `frontend/src/components/workspace/marketplace/skill-card.tsx`
- `frontend/src/components/workspace/marketplace/install-dialog.tsx`
- marketplace 相关测试文件

**Responsibilities**

- 根据 `cr-marketplace.md` 修复 marketplace API contract、installed 状态、install/uninstall 路径、type shape、seed / 列表 / 对话框逻辑
- 这轮优先修 report 中可直接修复的问题；若 activation bridge 需要改共享运行时文件，则仅在不越界的前提下做最小闭环，避免和 `auth-foundation` / `rag-knowledge` 冲突

### 6. `integration-check`

**Agent**: `worker-tests`

**Owns files/directories**

- `backend/tests/**` 中因合并结果需要修复的测试文件
- `frontend` 中仅测试/类型验证相关轻量修复文件（若为验证通过所必需）
- 不得重构业务代码；仅为通过验证所需的最小修正

**Responsibilities**

- 在前五个 worker 合并后，基于 merged code 运行后端/前端验证命令
- 修复跨模块集成问题、补测试、做最小必要修补

## Shared Interfaces

### Auth Contract

- `get_auth_context(request, ...)` 提供 `user_id`, `org_id`, `role`
- 依赖 `request.state.user_id` / `request.state.org_id` / `request.state.auth_role` 的中间件与路由不得擅自改字段名

### Config API Contract

- `GET /api/config` 返回 merged config 结构；若前后端字段不一致，`config-wizard` 负责统一并在其 owned frontend files 内消费

### Knowledge API Contract

- `rag-knowledge` 负责定义并统一 KB list/doc list/search 的响应结构
- 其他 worker 不得修改 knowledge 前后端类型

### Admin API Contract

- `admin-usage` 负责统一 `/api/admin/*` 与 `/api/admin/org/*` 相关响应结构
- 其他 worker 不得修改 admin/org frontend API files

### Marketplace API Contract

- `marketplace` 负责统一 browse/install/uninstall/installed list 的响应结构

### Shared DB Model File Rule

- `backend/app/gateway/db/models.py` 是共享文件，但按 section ownership 严格分区
- 每个 worker 只能修改自己拥有的模型区段
- 不得做全文件格式化或无关 import 重排，避免冲突

## Naming Conventions

- Python: `snake_case`, Pydantic / dataclass / ORM class 用 `PascalCase`
- TypeScript: files 用 `kebab-case`, components 用 `PascalCase`
- import 顺序遵守仓库既有 lint 规则
- 仅做最小必要修复，不做大规模重命名

## Execution Phases

### Phase A — Parallel domain fixes

- `auth-foundation`
- `config-wizard`
- `rag-knowledge`
- `admin-usage`
- `marketplace`

这些 worker 并行执行，各自在 own files 内完成 report-driven 修复与局部验证。

### Phase B — Post-merge integration verification

- `integration-check`

在 Phase A merge 后执行，运行全局验证，修复集成问题。

## Required Verification

### Backend

- `cd /Users/wbz/deer-flow/backend && PYTHONPATH=. uv run ruff check .`
- `cd /Users/wbz/deer-flow/backend && PYTHONPATH=. uv run pytest tests/ -v --ignore=tests/test_client_live.py --ignore=tests/test_checkpointer.py`

### Frontend

- `cd /Users/wbz/deer-flow/frontend && pnpm lint`
- `cd /Users/wbz/deer-flow/frontend && pnpm typecheck`

## Must Do

- 先核对 report 与当前代码的差异，不要盲修已解决的问题
- 只修改自己拥有的文件
- 每个 worker 必须运行与其改动直接相关的验证
- 发现跨域问题时，在提交说明中明确标出，由 `integration-check` 统一收口

## Must Not Do

- 不要修改其他 worker 的 owned files
- 不要做与 report 无关的大重构
- 不要全仓格式化
- 不要引入新的 API contract breakage
