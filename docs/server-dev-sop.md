# Allo 服务器开发与部署 SOP

## 服务器基本信息

| 项目 | 值 |
|------|-----|
| IP | 146.56.239.94 |
| SSH 用户 | ubuntu |
| 项目路径 | /srv/allo |
| 项目文件 owner | allo (uid 998) |
| 环境变量 | /etc/allo/allo.env |
| 日志 | journalctl -u allo-{gateway,langgraph,frontend} |
| Nginx 日志 | /var/log/nginx/allo-{access,error}.log |
| 数据库 | PostgreSQL, 库名 allo, 用户 allo |
| Redis | 127.0.0.1:6379 |

## 服务架构

```
Nginx (:80)
  ├── /api/langgraph/* → LangGraph (:2024)  [需认证，注入 X-User-Id/X-Org-Id]
  ├── /api/*           → Gateway (:8001)
  ├── /health          → Gateway /health
  └── /*               → Frontend (:3000)
```

三个 systemd 服务：

| 服务 | 命令 | 端口 |
|------|------|------|
| allo-gateway | `uv run uvicorn app.gateway.app:app --workers 2` | 8001 |
| allo-langgraph | `uv run langgraph dev --no-browser --allow-blocking` | 2024 |
| allo-frontend | `node .next/standalone/server.js` | 3000 |

## 日常操作命令

```bash
# 所有 git/uv/pnpm 操作必须用 allo 用户
sudo -u allo bash -c 'cd /srv/allo && <command>'

# 查看服务状态
sudo systemctl status allo-gateway allo-langgraph allo-frontend

# 重启服务
sudo systemctl restart allo-gateway allo-langgraph allo-frontend

# 查看日志（实时）
sudo journalctl -u allo-langgraph -f --no-pager
sudo journalctl -u allo-gateway -f --no-pager

# 健康检查
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/     # 200 = frontend OK
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/models  # 401 = gateway OK (需登录)
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2024/ok   # 200 = langgraph OK

# 查看端口监听
sudo ss -tlnp | grep -E '2024|8001|3000'
```

## 代码部署流程

服务器的 git origin 用的是 `gitclone.com` 镜像，同步有延迟。用 `git bundle` 传代码最可靠。

### 步骤

```bash
# === 本地 ===

# 1. 创建 bundle（只包含新 commit）
git bundle create /tmp/update.bundle <branch> --not <base-commit-or-branch>

# 2. 传到服务器
scp /tmp/update.bundle ubuntu@146.56.239.94:/tmp/update.bundle

# === 服务器 ===

# 3. 导入并合并
sudo -u allo bash -c 'cd /srv/allo && \
  git fetch /tmp/update.bundle <branch>:<local-ref> && \
  git merge <local-ref> --ff-only'

# 4. 后端依赖
sudo -u allo bash -c 'cd /srv/allo/backend && uv sync'

# 5. 前端依赖 + 构建（如果前端有改动）
sudo -u allo bash -c 'cd /srv/allo/frontend && CI=true pnpm install && pnpm build'

# 6. 重启受影响的服务
sudo systemctl restart allo-gateway allo-langgraph  # 后端改动
sudo systemctl restart allo-frontend                 # 前端改动

# 7. 健康检查（等 15 秒让 LangGraph 启动）
sleep 15
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2024/ok && echo ' langgraph OK'
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/models && echo ' gateway OK'
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ && echo ' frontend OK'
```

### 数据库迁移

新建表后必须授权给 allo 用户：

```bash
sudo -u postgres psql -d allo -c "CREATE TABLE IF NOT EXISTS <table_name> (...);"
sudo -u postgres psql -d allo -c "GRANT ALL ON TABLE <table_name> TO allo;"
```

当前数据库有 28 张表，`thread_knowledge_bases` 是唯一 owner 为 postgres 的表（已授权）。

## 踩过的坑与教训

### 坑 1: `uv sync` 删除手动安装的包

**现象**: 每次 `uv sync` 后 LangGraph 启动失败，报 `ImportError: langgraph-checkpoint-postgres is required`

**原因**: `langgraph-checkpoint-postgres`、`psycopg`、`psycopg-pool` 之前是手动 `uv pip install` 装的，不在 `pyproject.toml` 和 `uv.lock` 里。`uv sync` 严格按 lock 文件来，会删除所有不在 lock 里的包。

**修复**: 把这三个包加入 `pyproject.toml` 的 dependencies，然后 `uv lock` 更新 lock 文件。

**教训**: 生产环境需要的包必须在 `pyproject.toml` 里声明，不能只靠手动 `uv pip install`。`uv sync` 是幂等的——lock 文件就是唯一的真相来源。

### 坑 2: `OPENAI_API_BASE` 未配置导致 embedding 超时

**现象**: 知识库上传文档时卡住，日志报 `httpcore.ConnectTimeout`

**原因**: `embedder.py` 默认连 `api.openai.com`，服务器在国内无法直连。模型配置 `config.yaml` 里用了 `https://kkcode.vip/v1` 代理，但 embedder 读的是 `OPENAI_API_BASE` 环境变量。

**修复**: 在 `/etc/allo/allo.env` 末尾加 `OPENAI_API_BASE=https://kkcode.vip/v1`

**教训**: 所有调用 OpenAI API 的地方（模型、embedding、其他）都要走同一个代理。新增 OpenAI 调用时检查是否读了 `OPENAI_API_BASE`。

### 坑 3: 新建数据库表 owner 不对

**现象**: `GET /api/threads/{id}/knowledge-bases` 返回 500，日志报 `InsufficientPrivilegeError: permission denied for table thread_knowledge_bases`

**原因**: 用 `sudo -u postgres psql` 创建的表，owner 是 `postgres`，而 Gateway 用 `allo` 用户连接数据库。

**修复**: `GRANT ALL ON TABLE thread_knowledge_bases TO allo;`

**教训**: 创建表后必须 `GRANT ALL ... TO allo`。或者用 `sudo -u allo` 身份连接数据库创建表（但 allo 用户可能没有 createdb 权限）。最佳实践是用 Alembic migration。

### 坑 4: `Runtime.context` 为 None

**现象**: `uploads_middleware.py` 调用 `runtime.context.get("thread_id")` 时崩溃，报 `AttributeError: 'NoneType' object has no attribute 'get'`

**原因**: 当前 LangGraph 版本的 `Runtime` dataclass 的 `context` 字段默认为 `None`。框架没有把前端传的 context 注入到 `Runtime.context`。但 `RunnableConfig`（通过 `var_child_runnable_config` contextvar）里有完整的 `thread_id`、`user_id` 等信息。

**修复**:
- `context.py` 的 `get_runtime_thread_id` 和 `get_runtime_user_id` 增加了从 `var_child_runnable_config` 读取的 fallback
- `uploads_middleware.py` 改用这些辅助函数而不是直接访问 `runtime.context`

**教训**: 不要直接访问 `runtime.context`，始终用 `get_runtime_thread_id()` / `get_runtime_user_id()` 辅助函数。这些函数会按优先级从多个来源查找。

### 坑 5: 上传文件路径不一致

**现象**: 用户上传文件后，agent 说"目录是空的，读不到文件"

**原因**: 有两套路径：
- 旧路径（无用户隔离）: `.deer-flow/threads/{thread_id}/user-data/uploads/`
- 新路径（有用户隔离）: `.deer-flow/users/{user_id}/threads/{thread_id}/user-data/uploads/`

上传路由 `uploads.py` 用旧路径存文件，agent sandbox 的 `thread_data_middleware` 在有 `user_id` 时用新路径读文件。

**修复**: `uploads.py` 的 `get_uploads_dir` 在有 `user_id` 时使用 `user_sandbox_uploads_dir`。

**教训**: 文件路径必须在上传端和读取端保持一致。改路径逻辑时要同时检查所有读写点：`uploads.py`（写）、`uploads_middleware.py`（读）、`thread_data_middleware.py`（路径解析）、`sandbox/tools.py`（虚拟路径映射）。

### 坑 6: `reconnectOnMount` 改动破坏新会话

**现象**: 把 `reconnectOnMount: true` 改成 `!!onStreamThreadId` 后，新建会话发消息不进入 thread 页面

**原因**: 新会话时 `onStreamThreadId` 是 `undefined`，`reconnectOnMount: false` 导致 `useStream` 不跟踪新创建的 thread，`onCreated` 回调不触发。

**修复**: 回退为 `reconnectOnMount: true`

**教训**: `useStream` 的配置参数会影响内部状态机。改动前要理解 `useStream` 的完整生命周期：初始化 → reconnect → submit → stream → finish。

### 坑 7: 前端 build 未更新

**现象**: 后端代码已回退到稳定分支，但前端还是之前的 build，导致行为不一致

**原因**: Next.js standalone build 是静态的，切换 git 分支后必须重新 `pnpm build`

**教训**: 切换分支后，如果前端代码有变化，必须重新 `pnpm build` + `systemctl restart allo-frontend`。

## 未解决的已知问题

### 欢迎页发消息不跳转到 thread 页面

**现象**: 在 `/workspace/chats/new` 发第一条消息后，页面不跳转，需要手动点击左侧 thread 列表

**根因**: `ChatPage` 传给 `useThreadStream` 的是 `threadId: isNewThread ? undefined : threadId`。`useStream` 的 `threadId` 为 `undefined` 时，`thread.submit()` 不发出 `runs/stream` 请求。

**难点**: 改变 `threadId` 或触发 React 状态更新会导致 `useStream` 重新初始化，丢弃 submit。详见 `docs/dev-summary-2026-04-05.md` 的尝试记录。

**建议方向**:
1. 研究 `@langchain/langgraph-sdk` 的 `useStream` 源码
2. 考虑在欢迎页不用 `useStream`，发消息后 `router.push` 到 thread 页面再初始化 streaming
3. 或者用 LangGraph SDK client 直接发起 streaming，绕过 `useStream`

## 环境变量清单

| 变量 | 用途 | 当前值 |
|------|------|--------|
| DATABASE_URL | PostgreSQL 连接 | postgresql+asyncpg://allo:***@127.0.0.1:5432/allo |
| CHECKPOINT_POSTGRES_URI | LangGraph checkpointer | postgresql://allo:***@127.0.0.1:5432/allo |
| REDIS_URL | Redis 连接 | redis://:***@127.0.0.1:6379/0 |
| OPENAI_API_KEY | OpenAI/代理 API Key | sk-*** |
| OPENAI_API_BASE | OpenAI API 代理地址 | https://kkcode.vip/v1 |
| TAVILY_API_KEY | Tavily 搜索 | tvly-*** |
| JINA_API_KEY | Jina AI | jina_*** |
| FIRECRAWL_API_KEY | Firecrawl | fc-*** |
| NODE_ENV | 前端环境 | production |
| SANDBOX_TYPE | Sandbox 类型 | local |
| SKIP_AUTH | 跳过认证 | 0 |
| NEXT_PUBLIC_APP_URL | 前端公开 URL | http://146.56.239.94 |
| NEXT_PUBLIC_GATEWAY_URL | Gateway 公开 URL | http://146.56.239.94/api |
| NEXT_PUBLIC_LANGGRAPH_URL | LangGraph 公开 URL | http://146.56.239.94/api/langgraph |

## 全链路测试 Checklist

每次部署后必须验证：

- [ ] 新建会话，发消息，收到回复（点击左侧 thread 后发消息）
- [ ] 上传文件，agent 能读到文件内容
- [ ] 点击历史 thread，能加载对话记录
- [ ] 切换浏览器语言，页面中英文正确显示（如果 i18n 已部署）
- [ ] Admin 看板有数据（如果 token tracking 已部署）
- [ ] 知识库上传文档不超时（确认 OPENAI_API_BASE 已配置）

## 日志查看与 Debug 指南

### 日志位置一览

| 来源 | 命令 | 看什么 |
|------|------|--------|
| LangGraph agent | `sudo journalctl -u allo-langgraph` | agent 执行、tool 调用、middleware 错误 |
| Gateway API | `sudo journalctl -u allo-gateway` | API 请求处理、DB 错误、认证问题 |
| Frontend SSR | `sudo journalctl -u allo-frontend` | Next.js 服务端渲染错误 |
| Nginx access | `sudo tail /var/log/nginx/allo-access.log` | HTTP 请求流、状态码、耗时 |
| Nginx error | `sudo tail /var/log/nginx/allo-error.log` | 上游连接失败、超时、502/504 |
| Warmup | `sudo cat /var/log/allo/warmup.log` | LangGraph 首次加载是否成功 |

### 常用日志命令

```bash
# 实时跟踪某个服务的日志
sudo journalctl -u allo-langgraph -f --no-pager

# 查看最近 5 分钟的日志
sudo journalctl -u allo-gateway --since '5 min ago' --no-pager

# 查看某个时间段的日志
sudo journalctl -u allo-langgraph --since '2026-04-05 20:00' --until '2026-04-05 21:00' --no-pager

# 只看错误
sudo journalctl -u allo-langgraph --since '10 min ago' --no-pager | grep -E 'error|Error|Traceback|ValueError'

# 查看某个 thread 的所有日志
sudo journalctl -u allo-langgraph --since '10 min ago' --no-pager | grep '<thread-id>'

# Nginx 最近的 500 错误
sudo tail -200 /var/log/nginx/allo-access.log | grep -E '50[0-9]'

# Nginx 最近的错误日志
sudo tail -50 /var/log/nginx/allo-error.log
```

### 按问题类型排查

#### 问题: 发消息没有回复

排查顺序：

```bash
# 1. 看 nginx access log，确认请求到了哪一步
sudo tail -30 /var/log/nginx/allo-access.log | grep '<thread-id>'
# 正常流程应该有: POST /api/threads → POST /api/langgraph/threads → POST /api/threads/.../runs → runs/stream
# 如果缺少 runs/stream → 前端 thread.submit 没发出请求（前端问题）
# 如果 runs/stream 返回 500 → 后端 agent 执行出错

# 2. 看 LangGraph 日志，确认 agent 是否收到请求
sudo journalctl -u allo-langgraph --since '3 min ago' --no-pager | grep '<thread-id>'

# 3. 看是否有 agent 执行错误
sudo journalctl -u allo-langgraph --since '3 min ago' --no-pager | grep -E 'error|Error|ValueError|Traceback'
```

#### 问题: 上传文件 agent 读不到

```bash
# 1. 确认文件存在哪个路径
sudo find /srv/allo/backend/.deer-flow -name '<filename>' 2>/dev/null

# 2. 确认用户隔离路径下有文件
sudo ls -la /srv/allo/backend/.deer-flow/users/<user-id>/threads/<thread-id>/user-data/uploads/

# 3. 看 uploads middleware 是否报错
sudo journalctl -u allo-langgraph --since '5 min ago' --no-pager | grep -i 'upload\|file\|NoneType'

# 4. 确认 user_id 和 thread_id 能正确解析
sudo journalctl -u allo-langgraph --since '5 min ago' --no-pager | grep 'user_id\|thread_id'
```

#### 问题: LangGraph 启动失败

```bash
# 1. 检查服务状态
sudo systemctl status allo-langgraph

# 2. 看启动日志
sudo journalctl -u allo-langgraph -n 50 --no-pager

# 3. 常见原因:
# - ImportError: langgraph-checkpoint-postgres → uv sync 删了包，重新 uv sync（已修复到 pyproject.toml）
# - 端口 2024 没监听 → uv run 在做依赖解析，等一会或检查 uv.lock
sudo ss -tlnp | grep 2024

# 4. 手动启动看完整错误
sudo -u allo bash -c 'cd /srv/allo/backend && uv run langgraph dev --no-browser --allow-blocking 2>&1' | head -50
```

#### 问题: Gateway 500 错误

```bash
# 1. 看 Gateway 完整 traceback
sudo journalctl -u allo-gateway --since '5 min ago' --no-pager | grep -A 20 'Traceback'

# 2. 常见原因:
# - UndefinedTableError → 数据库表不存在，需要创建并授权
# - InsufficientPrivilegeError → 表存在但 allo 用户没权限，需要 GRANT
# - ConnectTimeout → 外部 API 超时（检查 OPENAI_API_BASE）

# 3. 检查数据库表
sudo -u postgres psql -d allo -c '\dt'

# 4. 检查表权限
sudo -u postgres psql -d allo -c "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public';"
```

#### 问题: 前端 Application Error

```bash
# 这是客户端 JS 渲染错误，服务端日志通常看不到
# 排查方向:

# 1. 看 nginx access log 有没有 500 的 API 请求
sudo tail -50 /var/log/nginx/allo-access.log | grep -E '50[0-9]'

# 2. 看 nginx error log 有没有上游连接失败
sudo tail -20 /var/log/nginx/allo-error.log

# 3. 确认三个服务都在运行
sudo ss -tlnp | grep -E '2024|8001|3000'

# 4. 如果某个 API 返回 500，按上面的 Gateway/LangGraph 排查
# 5. 如果所有 API 正常但前端还是报错 → 需要看浏览器 console（让用户截图）
```

### Debug 技巧

#### 临时加日志

在 Python 文件里加 `logger.warning(...)` 或 `print(...)`，LangGraph dev 模式会自动热重载：

```bash
# 编辑文件
sudo -u allo vim /srv/allo/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py

# LangGraph dev 模式会自动检测文件变化并重载（看日志确认）
sudo journalctl -u allo-langgraph -f --no-pager | grep 'changes detected\|Reloading'

# Gateway 需要手动重启
sudo systemctl restart allo-gateway
```

#### 写文件 debug（当 logger 输出被 traceback 吞掉时）

```python
# 在代码里写文件，绕过日志系统
with open('/srv/allo/backend/debug.json', 'w') as f:
    import json
    f.write(json.dumps({'var': str(some_var)}, indent=2))
```

然后查看：`sudo cat /srv/allo/backend/debug.json`

#### 检查 RunnableConfig（排查 context 传递问题）

```python
# 在 middleware 的 before_agent 里加这段
from langchain_core.runnables.config import var_child_runnable_config
rc = var_child_runnable_config.get()
logger.warning("RunnableConfig: configurable=%s", rc.get("configurable", {}) if rc else "None")
```

#### 数据库快速查询

```bash
# 查看最近的 thread
sudo -u postgres psql -d allo -c "SELECT id, title, status, created_at FROM threads ORDER BY created_at DESC LIMIT 5;"

# 查看某个 thread 的 runs
sudo -u postgres psql -d allo -c "SELECT id, status, model_name, created_at FROM thread_runs WHERE thread_id='<thread-id>' ORDER BY created_at DESC LIMIT 5;"

# 查看 usage records
sudo -u postgres psql -d allo -c "SELECT record_type, model_name, input_tokens, output_tokens, created_at FROM usage_records ORDER BY created_at DESC LIMIT 10;"

# 查看用户信息
sudo -u postgres psql -d allo -c "SELECT id, name, email FROM users;"
```

#### Nginx 请求流分析

```bash
# 追踪某个 thread 的完整请求流（从创建到 streaming）
sudo tail -200 /var/log/nginx/allo-access.log | grep '<thread-id>' | awk '{print $4, $6, $7, $9}'
# 输出格式: [时间] METHOD /path 状态码
# 正常流程:
#   POST /api/threads                              201
#   POST /api/langgraph/threads                    200  (ensureLangGraphThread)
#   POST /api/threads/<id>/runs                    201
#   POST /api/langgraph/threads/<id>/runs/stream   200  (streaming)
#   POST /api/langgraph/threads/<id>/history        200
```
