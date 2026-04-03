# 任务简报：Gateway + 数据库 + 前端对接

## 你是谁

你负责 Allo（元枢）项目的 Gateway 层改造。另一个人（B）同时在改 Harness/Agent 层。你们通过接口契约协作，代码不交叉。

## 项目背景

Allo 是一个 AI 办公助手平台，当前是单用户本地开发状态。你的任务是把它改造成支持多用户的线上系统。

当前架构：
- 前端：Next.js 16 + React 19（`frontend/`）
- 业务网关：FastAPI（`backend/app/gateway/`）
- Agent 引擎：LangGraph Server（`backend/packages/harness/deerflow/`）
- 认证：本地 JSON 文件存储的 dev 实现（需要替换）

目标架构：
```
浏览器 → nginx → frontend:3000 (页面)
                → gateway:8001 (业务API, 认证, thread管理)
                → langgraph:2024 (agent执行, 通过nginx auth_request鉴权)
                    ↕
              PostgreSQL (所有持久化数据)
              Redis (session缓存, 临时数据)
```

## 你的职责边界

你只改这些目录：
- `backend/app/gateway/` — 所有业务 API
- `backend/alembic/` — 数据库迁移
- `frontend/` — 前端页面和 hooks
- `deploy/` — 部署配置（nginx, systemd, env）

你不动这个目录：
- `backend/packages/harness/deerflow/` — 这是 B 的领地

## 接口契约

B 会在 `backend/packages/harness/deerflow/stores.py` 定义以下抽象接口，你负责提供 PostgreSQL 实现：

```python
class MemoryStore(ABC):
    async def get_memory(self, user_id: str) -> dict: ...
    async def save_memory(self, user_id: str, data: dict) -> None: ...
    async def get_facts(self, user_id: str, limit: int = 15) -> list[dict]: ...

class SoulStore(ABC):
    async def get_soul(self, user_id: str) -> str | None: ...

class SkillConfigStore(ABC):
    async def get_skill_toggles(self, user_id: str) -> dict[str, bool]: ...

class McpConfigStore(ABC):
    async def get_user_mcp_config(self, user_id: str) -> dict: ...

class ModelKeyResolver(ABC):
    async def resolve_key(self, run_id: str) -> tuple[str, str | None]: ...
```

Redis key 约定：
```
session:{token}       → AuthContext JSON, TTL 5min    (你写，你读)
run:{run_id}:key      → {api_key, base_url} JSON, TTL 5min  (你写，B读)
rate_limit:{user_id}  → 计数器, TTL 60s              (你写，你读)
```

## 前置条件

本地需要：
```bash
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis
createdb allo
psql -d allo -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d allo -c "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"
```

环境变量（加到 .env）：
```
DATABASE_URL=postgresql+asyncpg://localhost:5432/allo
REDIS_URL=redis://localhost:6379/0
SESSION_SECRET=local-dev-secret
API_KEY_ENCRYPTION_SECRET=local-dev-key
```

新增 Python 依赖（`backend/pyproject.toml`）：
```
alembic>=1.13
redis[hiredis]>=5.0
bcrypt>=4.0
httpx>=0.27
```

---

## 任务清单（按顺序执行）

### A-1. Alembic 初始化

新建 `backend/alembic.ini` 和 `backend/alembic/env.py`。

从现有 `backend/app/gateway/db/models.py` 生成基线迁移 `001_baseline.py`。

修改 `backend/app/gateway/app.py`，移除 `Base.metadata.create_all` 调用。

验证：`cd backend && PYTHONPATH=. uv run alembic upgrade head` 成功。

### A-2. Auth 数据库表

新建迁移 `002_auth_tables.py`：

```sql
CREATE TABLE users (
    id            VARCHAR(36) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name  VARCHAR(255),
    avatar_url    VARCHAR(512),
    locale        VARCHAR(10) DEFAULT 'zh-CN',
    is_active     BOOLEAN DEFAULT true,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sessions (
    id         VARCHAR(36) PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_user ON sessions(user_id);
```

在 `models.py` 中添加对应的 SQLAlchemy 模型。

### A-3. Redis 客户端

新建 `backend/app/gateway/redis_client.py`：
- `get_redis()` 返回 async Redis 连接（从 `REDIS_URL` 环境变量）
- `close_redis_pool()` 关闭连接池

修改 `app.py` 的 lifespan，在 shutdown 时调用 `close_redis_pool()`。

### A-4. Gateway Auth API

新建 `backend/app/gateway/routers/auth.py`：

| 端点 | 功能 |
|------|------|
| `POST /api/auth/register` | 注册（邮箱+密码+显示名），bcrypt 哈希，自动创建个人 Organization + membership，创建 session，返回 cookie |
| `POST /api/auth/login` | 登录，验证密码，创建 session，返回 cookie |
| `POST /api/auth/logout` | 删除 PG session + Redis 缓存 + 清除 cookie |
| `GET /api/auth/session` | 返回当前用户信息 { user_id, email, display_name, org_id } |
| `GET /api/auth/check` | 内部端点，验证 cookie，返回 `X-User-Id` / `X-Org-Id` 响应头（供 nginx auth_request 用） |

Session 机制：
- token = `secrets.token_urlsafe(32)`
- 存 PG sessions 表 + Redis `session:{token}` (TTL 5min)
- cookie: `session_token={token}; HttpOnly; Path=/; SameSite=Lax; Max-Age=604800`

重写 `backend/app/gateway/auth.py` 的 `get_auth_context`：
1. 读 cookie token
2. 查 Redis `session:{token}` → 命中则直接返回 AuthContext
3. 未命中 → 查 PG sessions 表 → 有效则构建 AuthContext 并写回 Redis
4. 无效 → 401

在 `app.py` 中注册 auth router。

验证：
```bash
curl -X POST localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test1234","display_name":"Test"}'

curl -c cookies.txt -X POST localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test1234"}'

curl -b cookies.txt localhost:8001/api/auth/session
curl -b cookies.txt localhost:8001/api/auth/check -v  # 看 X-User-Id 响应头
```

### A-5. 用户 API

新建 `backend/app/gateway/routers/users.py`：
- `GET /api/users/me` — 返回当前用户 profile
- `PUT /api/users/me` — 更新 display_name, avatar_url, locale

### A-6. 前端 Auth 改造

删除：
- `frontend/src/server/better-auth/` 整个目录
- `frontend/src/app/api/auth/[...all]/route.ts`

新建 `frontend/src/core/auth/api.ts`：
- `register(email, password, displayName)` → POST /api/auth/register
- `login(email, password)` → POST /api/auth/login
- `logout()` → POST /api/auth/logout
- `getSession()` → GET /api/auth/session

修改 `frontend/src/app/(auth)/login/page.tsx` 和 `register/page.tsx`：改成调 Gateway auth API。

修改 `frontend/src/middleware.ts`：保留 cookie 存在性检查逻辑。

验证：浏览器注册 → 登录 → 进入 workspace → 登出 → 重定向到 login。

### A-7. Thread 业务表

新建迁移 `004_threads.py`：

```sql
CREATE TABLE threads (
    id               VARCHAR(255) PRIMARY KEY,
    user_id          VARCHAR(36) NOT NULL,
    org_id           VARCHAR(36),
    title            VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    status           VARCHAR(32) NOT NULL DEFAULT 'active',
    agent_name       VARCHAR(255),
    default_model    VARCHAR(255),
    last_model_name  VARCHAR(255),
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now(),
    last_active_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_threads_user ON threads(user_id);
CREATE INDEX idx_threads_last_active ON threads(last_active_at);

CREATE TABLE thread_runs (
    id               VARCHAR(36) PRIMARY KEY,
    thread_id        VARCHAR(255) NOT NULL,
    user_id          VARCHAR(36) NOT NULL,
    org_id           VARCHAR(36),
    model_name       VARCHAR(255),
    agent_name       VARCHAR(255),
    sandbox_id       VARCHAR(255),
    status           VARCHAR(32) NOT NULL DEFAULT 'running',
    started_at       TIMESTAMPTZ DEFAULT now(),
    finished_at      TIMESTAMPTZ,
    error_message    TEXT
);
CREATE INDEX idx_thread_runs_thread ON thread_runs(thread_id);
CREATE INDEX idx_thread_runs_user ON thread_runs(user_id);
```

### A-8. Thread CRUD API

新建 `backend/app/gateway/routers/threads.py`：

| 端点 | 功能 |
|------|------|
| `POST /api/threads` | 创建 thread：调 LangGraph `POST /threads` + 写业务表 + 创建文件目录 |
| `GET /api/threads` | 列出当前用户 threads（查业务表，不调 LangGraph） |
| `GET /api/threads/{id}` | 获取单个 thread（校验 ownership） |
| `PATCH /api/threads/{id}` | 更新标题/状态 |
| `DELETE /api/threads/{id}` | 校验 ownership + 调 LangGraph 删 checkpoint + 删业务表 + 删文件目录 |
| `POST /api/threads/{id}/runs` | 记录 run 开始 + 解析 API Key 写入 Redis |
| `PATCH /api/threads/{id}/runs/{run_id}` | 更新 run 状态 |

Gateway 调 LangGraph 用 `httpx.AsyncClient("http://127.0.0.1:2024")`。

创建 thread 时的文件目录（base_dir 从 config 读取，本地默认 `backend/.deer-flow`）：
```
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/workspace/
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/uploads/
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/outputs/
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/tmp/
```

### A-9. 前端 Thread Hooks 改造

新建 `frontend/src/core/threads/threads-api.ts`：
- `createThread(params)` → POST /api/threads
- `listThreads()` → GET /api/threads
- `deleteThread(id)` → DELETE /api/threads/{id}
- `updateThread(id, params)` → PATCH /api/threads/{id}
- `createThreadRun(threadId, params)` → POST /api/threads/{id}/runs
- `updateThreadRun(threadId, runId, params)` → PATCH /api/threads/{id}/runs/{runId}

修改 `frontend/src/core/threads/hooks.ts`：
- `useThreads` → 改成调 Gateway `GET /api/threads`
- `useDeleteThread` → 改成调 Gateway `DELETE`
- `useRenameThread` → 改成调 Gateway `PATCH`
- `sendMessage` → submit 前加 Gateway 创建 thread（仅新 thread）+ 创建 thread_run
- `onUpdateEvent` → 检测 title 变化时调 Gateway `PATCH` 同步标题
- `onFinish` → 调 Gateway 更新 thread_run 状态

注意：`useStream`（SDK 流式消息）保持不变，继续直连 LangGraph。只有 thread 管理操作改走 Gateway。

### A-10. Per-User 数据表 + Store 实现

新建迁移 `005_user_data.py`：
- user_memory, user_memory_facts, user_souls, user_mcp_configs, user_agents, user_api_keys 表

新建 Store 实现（实现 B 定义的抽象接口）：
- `backend/app/gateway/services/memory_store_pg.py` → PostgresMemoryStore
- `backend/app/gateway/services/soul_store_pg.py` → PostgresSoulStore
- `backend/app/gateway/services/skill_config_store_pg.py` → PostgresSkillConfigStore
- `backend/app/gateway/services/mcp_config_store_pg.py` → PostgresMcpConfigStore
- `backend/app/gateway/services/model_key_resolver_pg.py` → PostgresModelKeyResolver

新建/修改对应的管理 API：
- `routers/soul.py` — GET/PUT /api/users/me/soul
- `routers/memory.py` — 按 user_id 查询
- `routers/mcp.py` — per-user 配置
- `routers/agents.py` — per-user CRUD
- `routers/skills.py` — per-user 开关
- `routers/api_keys.py` — BYOK 管理（加密存储）

### A-11. nginx auth_request 配置

新建 `deploy/nginx/allo.conf`：

```nginx
server {
    listen 80;

    location / {
        proxy_pass http://127.0.0.1:3000;
    }

    location /api/langgraph/ {
        auth_request /internal/auth-check;
        auth_request_set $x_user_id $upstream_http_x_user_id;
        auth_request_set $x_org_id  $upstream_http_x_org_id;

        rewrite ^/api/langgraph/(.*) /$1 break;
        proxy_pass http://127.0.0.1:2024;
        proxy_set_header X-User-Id $x_user_id;
        proxy_set_header X-Org-Id  $x_org_id;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
    }

    location = /internal/auth-check {
        internal;
        proxy_pass http://127.0.0.1:8001/api/auth/check;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Cookie $http_cookie;
    }
}
```

---

## 联调检查点

A-4 完成后，通知 B 可以开始联调 auth_request → X-User-Id 注入。

A-8 + A-10 完成后，和 B 做关键联调：
1. 浏览器注册登录
2. 创建 thread（走 Gateway）
3. 发消息（走 LangGraph，带 X-User-Id）
4. 确认 B 的 harness 能拿到 user_id 并加载对应数据
5. 两个用户互相看不到对方数据
