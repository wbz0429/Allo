# 任务简报：Harness 改造 + Agent 适配 + Sandbox + 搜索引擎

## 你是谁

你负责 Allo（元枢）项目的 Harness/Agent 层改造。另一个人（A）同时在改 Gateway/数据库/前端。你们通过接口契约协作，代码不交叉。

## 项目背景

Allo 是一个 AI 办公助手平台，基于 LangGraph 构建 agent 系统。当前是单用户本地开发状态，所有用户数据（memory、skills、MCP、soul）都是进程级全局单例。你的任务是把 harness 层改造成按 `user_id` 动态加载数据，支持多用户并发。

当前架构：
- Agent 引擎：LangGraph Server（`backend/packages/harness/deerflow/`）
- 业务网关：FastAPI（`backend/app/gateway/`）— A 负责
- 前端：Next.js（`frontend/`）— A 负责

核心问题：
- `load_skills()` 扫描全局目录 → 所有用户共享
- `memory.json` 全局一份 → 所有用户共享
- `extensions_config.json` 全局一份 → 所有用户共享
- `LocalSandboxProvider` 全局单例 → 所有用户共享
- `make_lead_agent(config)` 不知道当前用户是谁

改造后：
- 每次请求通过 `config["configurable"]["x-user-id"]` 拿到 user_id
- 按 user_id 动态加载该用户的 skills、memory、soul、MCP
- 无 user_id 时回退到现有全局行为（兼容本地开发 `make dev`）

## 你的职责边界

你只改这个目录：
- `backend/packages/harness/deerflow/` — agent 核心逻辑

你不动这些目录：
- `backend/app/gateway/` — 这是 A 的领地
- `frontend/` — 这是 A 的领地

唯一例外：`backend/app/gateway/app.py` 中注册 store 的初始化代码，需要和 A 协调。

## 接口契约

### 你定义的接口（A 来实现）

新建 `backend/packages/harness/deerflow/stores.py`：

```python
from abc import ABC, abstractmethod


class MemoryStore(ABC):
    @abstractmethod
    async def get_memory(self, user_id: str) -> dict: ...

    @abstractmethod
    async def save_memory(self, user_id: str, data: dict) -> None: ...

    @abstractmethod
    async def get_facts(self, user_id: str, limit: int = 15) -> list[dict]: ...


class SoulStore(ABC):
    @abstractmethod
    async def get_soul(self, user_id: str) -> str | None: ...


class SkillConfigStore(ABC):
    @abstractmethod
    async def get_skill_toggles(self, user_id: str) -> dict[str, bool]: ...


class McpConfigStore(ABC):
    @abstractmethod
    async def get_user_mcp_config(self, user_id: str) -> dict: ...


class ModelKeyResolver(ABC):
    @abstractmethod
    async def resolve_key(self, run_id: str) -> tuple[str, str | None]: ...
    # returns (api_key, base_url | None)
```

A 会在 `backend/app/gateway/services/` 下提供 PostgreSQL 实现。在 A 的实现就绪之前，你用 mock 或本地文件回退来开发和测试。

### UserContext

新建 `backend/packages/harness/deerflow/context.py`：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class UserContext:
    user_id: str
    org_id: str
    run_id: str | None = None


def get_user_context(config: dict | None = None) -> UserContext | None:
    if not config:
        return None
    configurable = config.get("configurable", )
    user_id = configurable.get("x-user-id") or configurable.get("user_id")
    org_id = configurable.get("x-org-id") or configurable.get("org_id", "default")
    run_id = configurable.get("run_id")
    if user_id:
        return UserContext(user_id=user_id, org_id=org_id, run_id=run_id)
    return None
```

### user_id 怎么到达 harness

```
浏览器发消息 → nginx auth_request → Gateway 验证 cookie
  → nginx 注入 X-User-Id header → LangGraph Server 收到
  → 放入 config["configurable"]["x-user-id"]
  → make_lead_agent(config) 调用 get_user_context(config)
  → 拿到 UserContext(user_id=..., org_id=..., run_id=...)
  → 传给 load_skills / load_memory / load_soul 等函数
```

你不需要关心 auth 怎么做，只需要从 config 里读 user_id。

### Redis key 约定

A 会把解密后的 API Key 写入 Redis：
```
run:{run_id}:key → {"api_key": "sk-xxx", "base_url": "https://..."} JSON, TTL 5min
```

你的 ModelKeyResolver 实现需要从 Redis 读这个 key。本地开发时如果没有 Redis，回退到 config.yaml 中的全局 Key。

### 文件路径约定

```
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/workspace/   — 可写
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/uploads/     — 只读
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/outputs/     — 可写
{base_dir}/users/{user_id}/threads/{thread_id}/user-data/tmp/         — 可写
{base_dir}/users/{user_id}/skills/custom/{skill_name}/                — 用户私有 skill

skills/public/{skill_name}/                                           — 平台公共 skill（只读）
```

本地开发时 `base_dir` = `backend/.deer-flow`。

虚拟路径映射（sandbox 内 agent 看到的路径）：
```
/mnt/user-data/workspace  → {base_dir}/users/{user_id}/threads/{thread_id}/user-data/workspace
/mnt/user-data/uploads    → ...uploads
/mnt/user-data/outputs    → ...outputs
/mnt/user-data/tmp        → ...tmp
/mnt/skills/public/...    → skills/public/...
/mnt/skills/custom/...    → {base_dir}/users/{user_id}/skills/custom/...
```

---

## 核心原则

**所有改动必须向后兼容**：无 user_id 时回退到现有全局行为。`make dev` 必须继续能用。

模式：
```python
def load_skills(user_id: str | None = None, skill_config_store: SkillConfigStore | None = None):
    if user_id and skill_config_store:
        # 多用户模式：public + users/{user_id}/custom + DB 开关
        ...
    else:
        # 本地开发模式：现有全局行为不变
        ...
```

---

## 任务清单（按顺序执行）

### B-1. 接口契约文件

新建 `backend/packages/harness/deerflow/stores.py`（上面的代码）。
新建 `backend/packages/harness/deerflow/context.py`（上面的代码）。

提交。这是和 A 的第一个同步点。

### B-2. 文件路径重构

修改 `backend/packages/harness/deerflow/config/paths.py`，新增方法：

```python
def user_dir(self, user_id: str) -> Path:
    return self.base_dir / "users" / user_id

def user_thread_dir(self, user_id: str, thread_id: str) -> Path:
    return self.user_dir(user_id) / "threads" / thread_id

def user_thread_tmp_dir(self, user_id: str, thread_id: str) -> Path:
    return self.user_thread_dir(user_id, thread_id) / "user-data" / "tmp"

def user_skills_dir(self, user_id: str) -> Path:
    return self.user_dir(user_id) / "skills" / "custom"
```

验证：单元测试，路径生成正确。

### B-3. Skills Loader 改造

修改 `backend/packages/harness/deerflow/skills/loader.py`：

- `load_skills(user_id=None, skill_config_store=None)`
- 有 user_id：
  - 扫描 `skills/public/**/SKILL.md`（平台公共）
  - 扫描 `users/{user_id}/skills/custom/**/SKILL.md`（用户私有）
  - 从 `skill_config_store.get_skill_toggles(user_id)` 读取开关状态
  - 合并：公共 enabled + 用户 custom enabled
- 无 user_id：回退到现有全局行为

验证：
- `make dev` 正常（无 user_id 回退）
- 传入 user_id 时只加载对应目录

### B-4. Memory 接口对接

修改 `backend/packages/harness/deerflow/memory/updater.py`：

- `MemoryUpdater.__init__` 接受可选的 `MemoryStore` 参数
- 有 MemoryStore：通过接口读写
- 无 MemoryStore：回退到现有 JSON 文件读写

验证：传入 mock MemoryStore 能正常工作。

### B-5. MCP 工具加载 per-user

修改 `backend/packages/harness/deerflow/mcp/cache.py`：

- `get_cached_mcp_tools(user_id=None, mcp_config_store=None)`
- 有 user_id：平台默认 `extensions_config.json` + `mcp_config_store.get_user_mcp_config(user_id)` 覆盖
- 缓存 key 从全局改为 `(user_id, config_hash)` 元组
- 无 user_id：回退到现有全局行为

### B-6. Soul 加载

修改 prompt 构建逻辑（`backend/packages/harness/deerflow/agents/lead_agent/prompt.py` 或相关文件）：

- 接受可选的 `SoulStore` 和 `user_id`
- 有 user_id：从 `soul_store.get_soul(user_id)` 读取
- 无 soul 或无 user_id：回退到平台默认 soul 模板或空

### B-7. make_lead_agent 改造（核心）

修改 `backend/packages/harness/deerflow/agents/lead_agent/agent.py`（或 `__init__.py` 中的 `make_lead_agent`）：

```python
def make_lead_agent(config):
    ctx = get_user_context(config)
    user_id = ctx.user_id if ctx else None
    run_id = ctx.run_id if ctx else None

    # 从 registry 获取 store 实现（A 注入的 PG 实现，或 None）
    memory_store = get_store("memory")       # MemoryStore | None
    soul_store = get_store("soul")           # SoulStore | None
    skill_config_store = get_store("skill")  # SkillConfigStore | None
    mcp_config_store = get_store("mcp")      # McpConfigStore | None
    key_resolver = get_store("key")          # ModelKeyResolver | None

    # 解析模型 Key
    if run_id and key_resolver:
        api_key, base_url = await key_resolver.resolve_key(run_id)
    else:
        api_key, base_url = None, None  # 回退到 config.yaml

    model = create_chat_model(name=model_name, api_key=api_key, base_url=base_url, ...)
    skills = load_skills(user_id=user_id, skill_config_store=skill_config_store)
    mcp_tools = get_cached_mcp_tools(user_id=user_id, mcp_config_store=mcp_config_store)
    soul = await soul_store.get_soul(user_id) if (soul_store and user_id) else default_soul()
    memory = await memory_store.get_memory(user_id) if (memory_store and user_id) else {}

    prompt = build_system_prompt(skills=skills, soul=soul, memory=memory, ...)
    tools = collect_tools(builtin_tools + mcp_tools)
    middlewares = build_middlewares(...)

    return create_agent(model, tools, middlewares, prompt, state_schema=ThreadState)
```

这是最关键的改动。确保：
- 有 user_id + stores → 多用户模式
- 无 user_id 或无 stores → 现有行为不变

### B-8. ThreadData Middleware 改造

修改 `backend/packages/harness/deerflow/agents/middleware/thread_data.py`：

- 从 `runtime.context` 读取 user_id
- 有 user_id：创建 `users/{user_id}/threads/{thread_id}/user-data/` 目录结构（含 tmp）
- 无 user_id：保持现有行为

### B-9. 虚拟路径映射改造

修改 sandbox 相关的路径解析代码（`sandbox/tools.py` 或类似文件）：

- `/mnt/user-data/*` → `users/{user_id}/threads/{thread_id}/user-data/...`
- `/mnt/skills/public/*` → `skills/public/...`
- `/mnt/skills/custom/*` → `users/{user_id}/skills/custom/...`
- 禁止路径穿越（`..` 或绝对路径跳出用户目录）

### B-10. Store Registry

实现一个简单的全局 store 注册表：

```python
# backend/packages/harness/deerflow/store_registry.py

_stores: dict[str, object] = {}

def register_store(name: str, impl: object) -> None:
    _stores[name] = impl

def get_store(name: str) -> object | None:
    return _stores.get(name)
```

A 会在 Gateway 启动时调用 `register_store("memory", PostgresMemoryStore(...))` 等。

harness 内部通过 `get_store("memory")` 获取。未注册时返回 None，触发回退逻辑。

### B-11. Checkpointer 切换到 PostgreSQL

修改 `backend/packages/harness/deerflow/agents/checkpointer/async_provider.py`：
- 确保 `postgres` 类型读取 `CHECKPOINT_POSTGRES_URI` 环境变量

修改 `config.example.yaml`：
```yaml
checkpointer:
  type: postgres
  uri: ${CHECKPOINT_POSTGRES_URI}
```

验证：LangGraph 启动时连接本地 PG。

### B-12. Sandbox UserSandboxProvider（可后做）

新建 `backend/packages/harness/deerflow/sandbox/user_sandbox_provider.py`：

- 每用户最多 2 个活跃 Docker 容器
- 容器资源限制：512MB 内存, 0.5 CPU, network none
- 空闲 10min 后销毁
- 挂载 thread workspace/uploads/outputs/tmp（可写/只读按约定）
- 挂载用户 custom skills（只读）+ 平台 public skills（只读）
- 注入 `TMPDIR=/mnt/user-data/tmp`

这个任务可以在其他任务都完成后再做。第一版可以先用现有 LocalSandboxProvider 兜底。

### B-13. 搜索引擎可插拔架构（可后做）

新建 `backend/packages/harness/deerflow/tools/search/registry.py`：
- `SearchEngine(ABC)` + `SearchEngineRegistry`

封装现有引擎：
- `tavily_engine.py`
- `jina_engine.py`
- `duckduckgo_engine.py`

新增：
- `volcengine_engine.py`（火山搜索）

修改搜索 tool 实现，改为调用 registry。

---

## 联调检查点

B-1 完成后：提交接口契约文件，通知 A。

B-7 完成后（关键联调）：
- A 把 PG Store 实现注入 harness（通过 store registry）
- 联调完整链路：
  1. 浏览器注册登录（A 的 auth）
  2. 创建 thread（A 的 Gateway API）
  3. 发消息（LangGraph，nginx 注入 X-User-Id）
  4. make_lead_agent 拿到 user_id（你的改造）
  5. 加载该用户的 skills/memory/soul/MCP
  6. 流式返回
- 确认：两个用户的数据互不可见

B-10 完成后：
- 全面回归测试
- `make dev` 仍然正常（无 user_id 回退）
