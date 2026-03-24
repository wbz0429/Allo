# Full MVP Reconcile Contract

> Scope: 在本地开发环境下，把 DeerFlow 当前 B2B SaaS MVP 除 auth 外的主要模块真正跑通。已确认本地 PostgreSQL 可用（database: `deerflow`），接下来修复 nginx 路由、数据库配置、middleware 挂载、以及 config / knowledge / admin / marketplace 的前后端 API contract 对齐问题。

## docMode

- `none`

## Roles

### 1. `infra-runtime`

**Agent**: `worker-backend`

**Owns files/directories**

- `.env`
- `frontend/.env`（如确有必要）
- `docker/nginx/nginx.local.conf`
- `docker/nginx/nginx.conf`
- `backend/app/gateway/app.py`
- `backend/app/gateway/middleware/rate_limiter.py`
- `backend/app/gateway/middleware/usage_tracking.py`
- `backend/app/gateway/db/database.py`
- `backend/app/gateway/db/models.py`（仅基础 runtime / table creation / shared DB wiring 相关最小改动）
- 相关基础验证测试文件

**Responsibilities**

- 配置本地 PostgreSQL `DATABASE_URL`
- 确保 backend 启动时能连上 `deerflow` 数据库并创建所需表
- 补齐 nginx 对 `/api/config`、`/api/admin`、`/api/knowledge-bases`、`/api/marketplace` 的代理路由
- 挂载 rate limiter / usage tracking middleware（若当前实现可安全启用）
- 不修改各业务域 frontend API contract 文件

### 2. `config-align`

**Agent**: `worker-frontend`

**Owns files/directories**

- `backend/app/gateway/routers/config.py`
- `frontend/src/core/config/api.ts`
- `frontend/src/core/config/types.ts`
- `frontend/src/core/config/hooks.ts`
- `frontend/src/core/config/index.ts`
- `frontend/src/components/workspace/setup-wizard/**`
- `frontend/src/app/workspace/setup/**`
- config 相关测试文件

**Responsibilities**

- 对齐 config/setup wizard 的前后端 API 路径、请求响应结构、类型定义
- 把 setup wizard 至少修到“页面可用、模型配置可读写、其余步骤不因 contract mismatch 报错”

### 3. `knowledge-align`

**Agent**: `worker-backend`

**Owns files/directories**

- `backend/app/gateway/routers/knowledge_bases.py`
- `backend/app/gateway/rag/**`
- `frontend/src/core/knowledge/api.ts`
- `frontend/src/core/knowledge/types.ts`
- `frontend/src/core/knowledge/hooks.ts`
- `frontend/src/components/workspace/knowledge/**`
- `frontend/src/app/workspace/knowledge/**`
- knowledge 相关测试文件

**Responsibilities**

- 对齐 knowledge base / document list / search 的 API 路径与响应结构
- 修复前端解析 backend response 时的 shape mismatch
- 保持知识库 CRUD / 上传 / 搜索最小可用

### 4. `admin-align`

**Agent**: `worker-backend`

**Owns files/directories**

- `backend/app/gateway/routers/admin.py`
- `frontend/src/core/admin/api.ts`
- `frontend/src/core/admin/types.ts`
- `frontend/src/core/org/api.ts`
- `frontend/src/core/org/types.ts`
- `frontend/src/app/admin/**`
- `frontend/src/components/admin/**`
- admin / org / usage 相关测试文件

**Responsibilities**

- 对齐 admin dashboard 的 URL、响应结构、前端类型
- 如前端依赖 backend 缺失端点，则在 backend 最小补齐，或将前端改到现有端点
- 确保管理台至少能读取组织列表、组织成员、usage 概览

### 5. `marketplace-align`

**Agent**: `worker-frontend`

**Owns files/directories**

- `backend/app/gateway/routers/marketplace.py`
- `backend/app/gateway/marketplace_seed.py`
- `frontend/src/core/marketplace/api.ts`
- `frontend/src/core/marketplace/types.ts`
- `frontend/src/app/workspace/marketplace/**`
- `frontend/src/components/workspace/marketplace/**`
- marketplace 相关测试文件

**Responsibilities**

- 对齐 marketplace browse/install/uninstall/installed list 的 API 路径和响应结构
- 修复 frontend 当前调用了不存在 endpoint 的问题
- 保证 marketplace 页面最小可用

### 6. `integration-mvp-check`

**Agent**: `worker-tests`

**Owns files/directories**

- 仅为集成验证与最小修补所需文件

**Responsibilities**

- 在前五个 worker merge 后，运行统一验证
- 做最小跨模块修补，确保当前主工作区达到可运行 MVP 状态

## Shared Interfaces

### Runtime / Env Contract

- 本地 PostgreSQL 连接串统一使用：`postgresql+asyncpg://postgres@localhost:5432/deerflow`
- 若某 worker需要在 frontend 直连 backend，应优先使用现有环境变量和 nginx 代理，不得各自发明不同 base URL 方案

### Nginx Contract

- 新增 API 路由需统一代理到 `gateway`
- 不要改变既有 `/api/auth/*` 由 Next.js 处理的本地 JSON auth 方案

### Auth Contract

- 当前 auth 已可用；其他 worker 不得破坏 `better-auth.session_token` cookie 约定
- backend 继续输出 `AuthContext(user_id, org_id, role)`

### DB Ownership Rule

- `backend/app/gateway/db/models.py` 为共享文件，只允许 `infra-runtime` 做基础 runtime wiring 相关最小改动
- 业务域 worker 尽量避免修改 models.py，除非确有必要且不与 infra 冲突

## Execution Phases

### Phase A (parallel)

- `infra-runtime`
- `config-align`
- `knowledge-align`
- `admin-align`
- `marketplace-align`

### Phase B (after Phase A merge)

- `integration-mvp-check`

## Required Verification

### Backend

- `cd /Users/wbz/deer-flow/backend && PYTHONPATH=. uv run ruff check .`
- `cd /Users/wbz/deer-flow/backend && PYTHONPATH=. uv run pytest tests/ -q --ignore=tests/test_client_live.py --ignore=tests/test_checkpointer.py`

### Frontend

- `cd /Users/wbz/deer-flow/frontend && pnpm lint`
- `cd /Users/wbz/deer-flow/frontend && pnpm typecheck`

### Runtime smoke checks

- config page loads and reaches `/api/config`
- knowledge page loads and reaches `/api/knowledge-bases`
- admin page loads and reaches `/api/admin`
- marketplace page loads and reaches `/api/marketplace`

## Must Do

- 只做把 MVP 跑通所需的最小修复
- 保持 auth 链路不被破坏
- 对齐前后端 contract，而不是让一侧继续猜测另一侧格式

## Must Not Do

- 不要做无关重构
- 不要引入新的认证体系
- 不要把本地开发修复扩展成复杂生产架构重写
