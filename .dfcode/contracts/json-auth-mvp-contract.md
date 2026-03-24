# JSON Auth MVP Contract

> Scope: 为本地开发临时替代当前 Better Auth + SQLite fallback 方案，目标是让注册/登录/workspace MVP 跑通。该方案仅用于本地开发，不作为正式生产认证实现。

## docMode

- `none`

## Roles

### 1. `frontend-auth`

**Agent**: `worker-frontend`

**Owns files/directories**

- `frontend/src/server/better-auth/config.ts`
- `frontend/src/server/better-auth/client.ts`
- `frontend/src/server/better-auth/server.ts`
- `frontend/src/server/better-auth/index.ts`
- `frontend/src/app/api/auth/[...all]/route.ts`
- `frontend/src/app/(auth)/register/page.tsx`
- `frontend/src/app/(auth)/login/page.tsx`
- `frontend/src/middleware.ts`
- `frontend/src/env.js`（仅 auth 开发态开关/环境读取，如有需要）
- `frontend/src/**` 下与本地 auth 存储、session cookie、dev auth API 直接相关的新文件
- `frontend` 侧新增/修改的 auth 相关测试文件

**Responsibilities**

- 用本地 JSON / 文件存储实现开发态注册与登录
- 避免继续依赖 `better-sqlite3` native binding
- 保持页面侧 `authClient.signUp.email` / `signIn.email` 等调用方式可用，或在最小范围内调整调用侧
- 注册时创建本地 user + session + org 基础信息，并设置与 backend 兼容的 cookie
- 若需要开发态分支逻辑，必须限制在 local/dev 模式

### 2. `backend-auth-fallback`

**Agent**: `worker-backend`

**Owns files/directories**

- `backend/app/gateway/auth.py`
- `backend/app/gateway/db/models.py`（仅 auth/org membership 读取契约相关最小改动）
- `backend/tests/test_auth.py`
- `backend/tests/test_router_auth.py`
- `backend/tests/**` 下与 dev JSON auth fallback 直接相关的新测试文件
- `backend/**` 下为读取本地 auth JSON/session 而新增的最小辅助文件

**Responsibilities**

- 为本地开发增加 dev-only 的 cookie/session fallback
- 当常规 DB session 解析失败时，在开发模式下允许从本地 JSON/session 数据中还原 `AuthContext(user_id, org_id, role)`
- 保持现有生产路径优先，避免影响正式 DB auth 路径

### 3. `integration-auth-check`

**Agent**: `worker-tests`

**Owns files/directories**

- 仅为验证 JSON auth MVP 所需的最小测试/集成修补文件

**Responsibilities**

- 在前两者合并后，跑本地开发态 auth MVP 相关验证
- 修复跨前后端的最小集成问题

## Shared Interfaces

### Cookie Contract

- 前后端共识 cookie 名仍优先使用 `better-auth.session_token`，以降低对现有页面/middleware 的改动范围
- cookie value 可以是 dev JSON auth session token，但 backend fallback 必须能识别

### Auth Context Contract

- backend 最终必须输出 `AuthContext(user_id, org_id, role)`
- `request.state.user_id` / `request.state.org_id` 字段名不得修改

### Dev-only Boundary

- JSON auth 替代仅在本地开发模式启用
- 若存在环境开关，默认应保证生产环境不走该分支

## Naming Conventions

- 仅做 MVP 所需最小实现
- 避免重命名现有公共接口
- 如创建本地 JSON 文件/辅助模块，使用 `kebab-case` / `snake_case` 与仓库风格保持一致

## Execution Phases

### Phase A (parallel)

- `frontend-auth`
- `backend-auth-fallback`

### Phase B (after Phase A merge)

- `integration-auth-check`

## Required Verification

### Frontend

- `cd /Users/wbz/deer-flow/frontend && pnpm lint`
- `cd /Users/wbz/deer-flow/frontend && pnpm typecheck`

### Backend

- `cd /Users/wbz/deer-flow/backend && PYTHONPATH=. uv run ruff check .`
- `cd /Users/wbz/deer-flow/backend && PYTHONPATH=. uv run pytest tests/test_auth.py -q`
- `cd /Users/wbz/deer-flow/backend && PYTHONPATH=. uv run pytest tests/test_router_auth.py -q`

### Integration

- 额外运行与注册/登录/dev session fallback 相关的最小测试集

## Must Do

- 先写失败测试或最小可重复验证，再实现
- 本地开发模式下保证注册/登录/workspace 主链路可跑通
- 保持生产路径优先，不破坏现有 DB auth 设计

## Must Not Do

- 不要把 JSON auth 方案扩展成正式生产架构
- 不要做与 auth MVP 无关的大重构
- 不要修改非 auth 领域文件
