# 产品改进开发总结 — 2026-04-04/05

## 当前服务器状态

- 分支: `feature/dev_0405`（基于 `feature/skill-upload`）
- 服务: 三个服务正常运行（Gateway:8001, LangGraph:2024, Frontend:3000）
- 已合入 4 个修复 commit，功能 commit 尚未合入

## 已完成的修复（已部署到服务器）

### 1. pyproject.toml 依赖修复 (`448581a1`)
- **问题**: `langgraph-checkpoint-postgres`、`psycopg`、`psycopg-pool` 不在 `pyproject.toml` 里，`uv sync` 每次都会删除它们，导致 LangGraph 启动失败
- **修复**: 将这三个包加入 `pyproject.toml` 的 dependencies
- **状态**: ✅ 已验证，`uv sync` 不再删包

### 2. Thread 创建流程稳定化 (`c0d078b4`)
- **问题**: `ensureLangGraphThread` 在 `createThreadRun` 之后执行，如果 LangGraph thread 不存在，run 记录会成为孤儿
- **修复**:
  - 将 `ensureLangGraphThread` 移到 `createThreadRun` 之前
  - 给 `ensureLangGraphThread` 加了 2 次重试（500ms 间隔）
  - Gateway 的 LangGraph 同步失败改为 `logger.warning` 而不是静默吞掉
- **状态**: ✅ 已验证

### 3. reconnectOnMount 回退 (`c03c82ef`)
- **问题**: 我把 `reconnectOnMount: true` 改成了 `!!onStreamThreadId`，导致新会话时 `useStream` 不跟踪新创建的 thread
- **修复**: 回退为原始的 `reconnectOnMount: true`
- **状态**: ✅ 已验证

### 4. Uploads middleware + context.py RunnableConfig fallback (`0ce6ca7d`)
- **问题**:
  - `uploads_middleware.py` 直接调用 `runtime.context.get("thread_id")`，但 `Runtime.context` 在当前 LangGraph 版本中是 `None`，导致 `AttributeError` 崩溃
  - 上传路由 `uploads.py` 使用旧的非用户隔离路径，文件存到了 agent sandbox 读不到的位置
- **修复**:
  - `uploads_middleware.py` 改用 `get_runtime_thread_id()` / `get_runtime_user_id()` 辅助函数
  - `context.py` 的 `get_runtime_thread_id` 和 `get_runtime_user_id` 增加了从 `var_child_runnable_config`（LangChain RunnableConfig contextvar）读取的 fallback
  - `uploads.py` 的 `get_uploads_dir` 支持 `user_id` 参数，使用用户隔离路径
- **状态**: ✅ 文件上传后 agent 能正常读取

## 未解决的问题

### 欢迎页发消息不跳转（原有 bug，未修复）

**现象**: 用户在 `/workspace/chats/new` 欢迎页发送第一条消息后：
- 左侧 thread 列表出现新 thread
- 但页面不跳转到 thread 对话页面，仍停留在欢迎页
- 需要手动点击左侧 thread 才能进入对话并看到回复

**根因分析**:

1. 用户在 `/workspace/chats/new`，`use-thread-chat.ts` 生成 `threadId=新UUID`，`isNewThread=true`
2. `ChatPage` 传给 `useThreadStream` 的是 `threadId: isNewThread ? undefined : threadId`，即 `undefined`
3. `useStream` 的 `threadId` 是 `undefined`，内部不知道要操作哪个 thread
4. `sendMessage` 里用 `gatewayThreadId`（那个 UUID）创建了 Gateway thread 和 LangGraph thread
5. `thread.submit()` 传了 `threadId: threadId`，但 `useStream` 自身的 `threadId` 是 `undefined`
6. **关键**: `thread.submit()` 没有发出 `runs/stream` 请求——nginx 日志中始终没有 `runs/stream`

**尝试过的方案（均失败）**:

| 方案 | 做法 | 结果 |
|------|------|------|
| 方案A | 在 `thread.submit` 前调用 `handleStreamStart` + `setOnStreamThreadId` | `setOnStreamThreadId` 触发 `useStream` 重新初始化，`submit` 被丢弃 |
| 方案B | 在 `thread.submit` 后调用 `handleStreamStart` + `setOnStreamThreadId` | `submit` 本身就没发出请求，后面的代码不执行 |
| 方案C | 在 `thread.submit` 前只调 `_handleOnStart`（不动 `setOnStreamThreadId`） | `onStart` 触发 `setIsNewThread(false)`，导致 `useThreadStream` 的 `threadId` 从 `undefined` 变成 UUID，`useStream` 重新初始化 |
| 方案D | 始终传 `threadId`（不传 `undefined`），加 `skipHistory` 参数 | `useStream` 有了 `threadId` 但 `thread.submit()` 仍然没发出 `runs/stream` |

**核心难点**:
- `useStream`（来自 `@langchain/langgraph-sdk`）的 `submit` 方法在 `threadId` 为 `undefined` 时不工作
- 但如果传了 `threadId`，`useStream` 会尝试 reconnect/fetch history，对不存在的 thread 会失败
- 任何在 `submit` 前改变 `threadId` 或触发 React 状态更新的操作都会导致 `useStream` 重新初始化，丢弃 `submit`

**建议方向**:
1. 深入研究 `@langchain/langgraph-sdk` 的 `useStream` hook 源码，理解 `submit` 在 `threadId=undefined` 时的行为
2. 可能需要不用 `useStream` 的 `submit`，而是直接用 LangGraph SDK client 发起 streaming，然后手动 feed 给 `useStream`
3. 或者改变前端架构：欢迎页不用 `useThreadStream`，发消息后先 `router.push` 到 `/workspace/chats/{threadId}`，在新页面里再发起 streaming

## 本地已完成但未部署的功能 commits（在 `feature/dev_0404` 分支）

这些功能代码已经写好并通过本地测试，但还没有合入 `feature/dev_0405`：

1. **Token Usage Tracking** (`7c9f57dc`) — UsageRecordStore 接口 + TokenUsageMiddleware + Postgres 实现 + Admin 看板数据
2. **Knowledge Base Agent Integration Backend** (`7feaa4e6`) — KnowledgeBaseSearchStore + knowledge_base_search 工具 + ThreadKnowledgeBase 关联表 + API
3. **i18n Full Coverage** (`fb08d373`) — 6 个翻译 key 组 + 15 个页面接入 i18n
4. **Knowledge Base Frontend Integration** (`c4679920`) — Thread KB 绑定 API + 设置面板 + @mention UI

## 部署 SOP

### 服务器信息
- IP: 146.56.239.94, 用户: ubuntu, 项目路径: /srv/allo
- 项目文件属于 `allo` 用户，操作需要 `sudo -u allo`
- 服务通过 systemd 管理: `allo-gateway`, `allo-langgraph`, `allo-frontend`
- 环境变量: `/etc/allo/allo.env`
- Nginx 反向代理: 80 → frontend:3000 / gateway:8001 / langgraph:2024

### 部署步骤
```bash
# 1. 传代码到服务器（本地）
git bundle create /tmp/update.bundle <branch> --not <base>
scp /tmp/update.bundle ubuntu@146.56.239.94:/tmp/update.bundle

# 2. 在服务器上应用（SSH）
sudo -u allo bash -c 'cd /srv/allo && git fetch /tmp/update.bundle <branch>:<ref> && git merge <ref> --ff-only'

# 3. 安装依赖
sudo -u allo bash -c 'cd /srv/allo/backend && uv sync'
# 注意: uv sync 现在不会删 postgres 包了（已加入 pyproject.toml）

# 4. 如果前端有改动，重新 build
sudo -u allo bash -c 'cd /srv/allo/frontend && pnpm build'

# 5. 重启服务
sudo systemctl restart allo-gateway allo-langgraph allo-frontend

# 6. 健康检查
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/   # 200
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/models  # 401
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2024/ok  # 200
```

### 注意事项
- 服务器用 `gitclone.com` 镜像作为 origin，同步有延迟，用 `git bundle` 传代码更可靠
- `OPENAI_API_BASE` 需要设置为 `https://kkcode.vip/v1`（已配置在 `/etc/allo/allo.env`）
- 新建数据库表后需要 `GRANT ALL ON TABLE <table> TO allo`
- `thread_knowledge_bases` 表已创建并授权
