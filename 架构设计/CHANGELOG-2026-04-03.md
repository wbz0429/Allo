# Changelog — 2026-04-03 调试会话

> 分支: `feature/pre_develop_local`
> 基线提交: `b3ad740` (feat: stabilize runtime context and store bootstrap)
> 回归测试: 35 passed | 前端 lint + typecheck 通过

---

## 修复总览

本次会话解决了 4 个阻塞性 bug + 1 个功能缺失，全部经过真实联调验证。

| # | 问题 | 根因 | 修复文件 | 验证状态 |
|---|------|------|----------|----------|
| 1 | history/resume 请求 user_id=None | useStream reconnect 不携带 context | `langgraph_runtime.py` | ✅ 日志确认 |
| 2 | marketplace tool gating "different loop" | sync wrapper 包 async PG store | `langgraph_runtime.py` + `tools.py` | ✅ 无报错 |
| 3 | Memory update failed: 'user' | PG store 返回 `{}` 缺少必需结构 | `memory_store_pg.py` + `updater.py` | ✅ 写入成功 |
| 4 | Memory 设置页 RangeError 崩溃 | `formatTimeAgo("")` → Invalid Date | `datetime.ts` | ✅ 页面正常 |
| 5 | Marketplace skill 安装后不显示 | resolver 只看 filesystem，忽略纯 DB skill | `skill_catalog_resolver.py` + 前端 | ✅ 显示正常 |

附带操作：清理 marketplace_skills 表重复 seed 数据（312 → 3 条）。

---

## Issue 1: history/resume 请求丢失用户上下文

### 现象

```
Lead agent runtime context user_id=None org_id=None run_id=None
Skills prompt section user_id=None ...
```

主消息 run 正常带有 user_id，但刷新页面后的 history/resume 请求全部丢失。

### 根因追踪

**数据流**：

```
前端 useStream({ reconnectOnMount: true, fetchStateHistory: { limit: 1 } })
  → LangGraph SDK 内部发起 POST /threads/{thread_id}/history
  → LangGraph 创建 run，调用 make_lead_agent(config)
  → config 中只有 configurable.thread_id，没有 context.user_id
```

前端 `sendMessage()` 是唯一构建 `runContext`（包含 user_id/org_id）并通过 `thread.submit()` 传入的路径。`useStream` 的 reconnect/history 是 SDK 内部行为，不走 `sendMessage`，因此 config 中永远没有用户上下文。

### 修复逻辑

**文件**: `backend/app/langgraph_runtime.py`

在 `make_lead_agent()` 中，当 `get_user_context(config)` 返回 None 时，新增 fallback：

```python
async def _resolve_user_from_thread(config: dict) -> UserContext | None:
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return None
    # 查 threads 表，用 thread_id 反查 user_id/org_id
    async with runtime_async_session_factory() as session:
        result = await session.execute(
            select(Thread.user_id, Thread.org_id)
            .where(Thread.id == thread_id).limit(1)
        )
        row = result.one_or_none()
        if row:
            return UserContext(user_id=row.user_id, org_id=row.org_id)
```

解析后回注 `config["configurable"]`，让下游 harness 代码（middleware、prompt、tools）都能拿到。

### 为什么这样修

- **不改 harness**：harness 层只消费 config，不感知 thread ownership。这是 app 层的职责。
- **不改前端**：useStream reconnect 是 SDK 内部行为，无法注入 context。
- **thread_id → user_id 是确定性映射**：threads 表有 ownership，查询结果可信。
- **NullPool 隔离**：LangGraph 进程的 PG 连接用 NullPool，不会与 Gateway 的连接池冲突。

### 验证日志

```
Resolved user context from threads table: thread_id=aeb8bebb... user_id=f7bc97b9... org_id=96b33239...
Lead agent runtime context user_id=f7bc97b9... org_id=96b33239... run_id=None
Skills prompt section user_id=f7bc97b9... available_skills=[16 skills]
```

---

## Issue 2: marketplace tool gating 跨 event loop 错误

### 现象

```
Failed to apply marketplace tool gating: ... attached to a different loop
```

第二条消息或 history run 中频繁出现。

### 根因追踪

**调用链**：

```
make_lead_agent(config)  [async, LangGraph event loop A]
  → get_available_tools(runtime_config=config)  [sync]
    → tools.py:69: _run_coroutine_sync(marketplace_store.get_managed_runtime_tools())
      → 检测到 running loop → ThreadPoolExecutor → asyncio.run() [新 event loop B]
        → AsyncSession 绑定在 loop A → "attached to a different loop"
```

`_run_coroutine_sync()` 在已有 event loop 时启动新线程+新 loop 来执行 async 代码。但 SQLAlchemy `AsyncSession` 绑定创建时的 event loop，跨 loop 使用会报错。

### 修复逻辑

**与 skill/soul/memory 采用相同策略**：在 `langgraph_runtime.py`（async 上下文）预解析，通过 `config.metadata` 传递给 harness。

**文件 1**: `backend/app/langgraph_runtime.py` — 新增预解析

```python
marketplace_store = get_store("marketplace")
if isinstance(marketplace_store, PostgresMarketplaceInstallStore):
    metadata["resolved_managed_tools"] = sorted(
        await marketplace_store.get_managed_runtime_tools()
    )
    metadata["resolved_installed_tools"] = sorted(
        await marketplace_store.get_installed_runtime_tools(ctx.org_id)
    )
```

**文件 2**: `backend/packages/harness/deerflow/tools/tools.py` — 优先消费预解析

```python
resolved_managed = metadata.get("resolved_managed_tools")
if resolved_managed is not None:
    # 使用预解析结果，不调 async store
    managed = set(resolved_managed)
    installed = set(resolved_installed) if resolved_installed else set()
    ...
elif ctx:
    # fallback: 只在没有预解析时走 sync wrapper（兼容非多租户模式）
    ...
```

### 为什么这样修

- **消除 sync-in-async 问题的根本方法是不做 sync wrapper**。所有 async PG store 调用都应在 async 上下文（`langgraph_runtime.py`）完成。
- **保留 fallback**：无预解析时仍可走旧路径，兼容本地开发 `make dev` 不走 `langgraph_runtime.py` 的场景。
- **模式一致**：与 skill_catalog、soul、memory 的预解析方式完全一致。

---

## Issue 3: Memory update failed: 'user'

### 现象

```
Memory update failed: 'user'
Memory update skipped/failed for thread ...
```

Memory timer 触发后写入失败，`/api/memory` 页面始终为空。

### 根因追踪

**调用链**：

```
MemoryMiddleware.after_agent()
  → queue.add(thread_id, messages, memory_store, user_id)
    → [30s debounce]
      → MemoryUpdater.update_memory(messages, thread_id)
        → get_memory_data(memory_store=pg_store, user_id="f7bc...")
          → pg_store.get_memory("f7bc...")
            → user_memory 表无记录 → return {}     ← 问题点
        → current_memory = {}
        → LLM 返回 update_data（含 user.workContext 等）
        → _apply_updates(current_memory={}, update_data)
          → current_memory["user"]["workContext"] = ...
            → KeyError: 'user'                      ← 崩溃点
```

`PostgresMemoryStore.get_memory()` 对新用户返回 `{}`，但 `_apply_updates()` 期望 `current_memory` 包含 `user`、`history`、`facts` 三个必需键。

### 修复逻辑（三层防御）

**第一层 — PG Store 返回正确结构**：

`backend/app/gateway/services/memory_store_pg.py`:
```python
def _empty_memory() -> dict:
    return {
        "version": "1.0", "lastUpdated": "",
        "user": { "workContext": {...}, "personalContext": {...}, "topOfMind": {...} },
        "history": { "recentMonths": {...}, "earlierContext": {...}, "longTermBackground": {...} },
        "facts": [],
    }

async def get_memory(self, user_id):
    ...
    if memory is None:
        return _empty_memory()  # 而不是 {}
```

**第二层 — get_memory_data() 校验返回值**：

`backend/packages/harness/deerflow/agents/memory/updater.py`:
```python
if not isinstance(memory_data, dict) or not memory_data:
    return _create_empty_memory()
if "user" not in memory_data or "history" not in memory_data:
    base = _create_empty_memory()
    base.update(memory_data)
    return base
```

**第三层 — _apply_updates() 防御性检查**：

```python
if "user" not in current_memory:
    current_memory["user"] = { ... }
if "history" not in current_memory:
    current_memory["history"] = { ... }
if "facts" not in current_memory:
    current_memory["facts"] = []
```

### 为什么三层

- **第一层**修的是数据源——PG store 不应该返回不完整的结构。
- **第二层**修的是消费者——`get_memory_data()` 作为 harness 内部函数，不应假设外部 store 一定返回正确结构。
- **第三层**修的是写入逻辑——`_apply_updates()` 是最终操作点，必须保证自身不崩。

三层独立，任何一层单独生效都能防止崩溃。

### 验证日志

```
Memory save path decision: store=True user_id=f7bc97b9... thread_id=aeb8bebb...
Saving memory via MemoryStore for user f7bc97b9...
Memory updated successfully for thread aeb8bebb...
```

---

## Issue 4: Memory 设置页 RangeError 崩溃

### 现象

```
Runtime RangeError: Invalid time value
  at formatTimeAgo (src/core/utils/datetime.ts:23:29)
  at memoryToMarkdown (memory-settings-page.tsx:62:54)
```

点击设置 → Memory 页面白屏崩溃。

### 根因

`memoryToMarkdown()` 行 62：
```tsx
formatTimeAgo(memory.lastUpdated)
```

新用户 memory 的 `lastUpdated` 是空字符串 `""`。`new Date("")` 返回 Invalid Date，`formatDistanceToNow(Invalid Date)` 抛 RangeError。

### 修复逻辑

**文件**: `frontend/src/core/utils/datetime.ts`

```typescript
export function formatTimeAgo(date: Date | string | number, locale?: Locale): string {
  if (!date && date !== 0) return "—";
  const parsed = date instanceof Date ? date : new Date(date);
  if (isNaN(parsed.getTime())) return "—";
  // ... 原有逻辑
  return formatDistanceToNow(parsed, { ... });
}
```

空字符串、null、undefined、Invalid Date 统一返回 `"—"`。

---

## Issue 5: Marketplace skill 安装后不显示

### 现象

用户在 Marketplace 安装 "Code Review"，安装成功显示 installed。但设置 → Skills 页面看不到。

### 根因追踪

**"Code Review" 在 marketplace_skills 表中 `runtime_skill_name` 为空字符串**：

```
skill-code-review | Code Review | (empty)
```

`skill_catalog_resolver.py` 的解析流程：
1. Step 1: `load_skills()` 从 filesystem 发现 skills → 没有 `code-review/SKILL.md`
2. Step 2: `managed_skills` = 有 `runtime_skill_name` 的 marketplace skills → 空字符串被 `if name` 过滤
3. Step 5: 遍历 filesystem skills 做 gating → Code Review 不在 filesystem 中，永远不会进入循环

**结论**：纯 marketplace skill（无 filesystem 对应）在 resolver 中是不可见的。

### 修复逻辑

**后端 — resolver 新增 Step 6**：

`backend/app/gateway/services/skill_catalog_resolver.py`:

```python
# Step 6: Add marketplace-only installed skills (no filesystem counterpart)
for row in installed_marketplace_rows:
    runtime_name = row.runtime_skill_name or ""
    if runtime_name and runtime_name in filesystem_skill_names:
        continue  # 已在 Step 5 处理

    skill_name = runtime_name or row.id
    final_catalog.append(Skill(
        name=skill_name,
        description=row.description or row.name,
        ...
        category="marketplace",
    ))
```

**前端 — 新增 Marketplace tab**：

`frontend/src/components/workspace/settings/skill-settings-page.tsx`:

```tsx
const hasMarketplace = useMemo(
  () => skills.some((skill) => skill.category === "marketplace"),
  [skills],
);
// ...
{hasMarketplace && <TabsTrigger value="marketplace">Marketplace</TabsTrigger>}
```

### 为什么这样修

- **不侵入 harness 边界**：harness 的 `load_skills()` 只负责 filesystem 发现。Marketplace 是 app 层概念，resolver（app 层）负责补全。
- **Skill 是 harness 定义的数据容器**：app 层构造 Skill 对象不违反依赖方向（app → deerflow ✓）。
- **category="marketplace"** 区分来源：filesystem skills 是 "public"/"custom"，marketplace-only skills 用独立 category。

### 验证结果

```
GET /api/skills → 18 skills:
  17 × category=public (含新安装的 data-analysis)
   1 × category=marketplace (skill-code-review)
```

---

## 附带操作：清理 seed 重复数据

### 问题

`marketplace_skills` 表从 3 条膨胀到 312 条。每次 Gateway 启动时 `_ensure_seed_data()` 在特定条件下重复插入。

### 清理

```sql
DELETE FROM org_installed_skills WHERE skill_id NOT IN ('skill-code-review', 'skill-deep-research', 'skill-data-analysis');
DELETE FROM marketplace_skills WHERE id NOT IN ('skill-code-review', 'skill-deep-research', 'skill-data-analysis');
-- 312 → 3 条
```

### 待办

Seed 幂等化需要单独处理（Alembic migration 或 upsert 逻辑），不在本次会话范围内。

---

## 修改文件清单

| 文件 | 改动量 | 改动类型 |
|------|--------|----------|
| `backend/app/langgraph_runtime.py` | +55 | thread fallback + marketplace 预解析 |
| `backend/packages/harness/deerflow/tools/tools.py` | +31/-14 | 消费预解析，保留 fallback |
| `backend/app/gateway/services/memory_store_pg.py` | +31/-4 | 空结构 + 部分数据补全 |
| `backend/packages/harness/deerflow/agents/memory/updater.py` | +34/-2 | 三层防御 |
| `backend/app/gateway/services/skill_catalog_resolver.py` | +47/-6 | Step 6 marketplace-only skills |
| `frontend/src/components/workspace/settings/skill-settings-page.tsx` | +7 | Marketplace tab |
| `frontend/src/core/utils/datetime.ts` | +9/-3 | Invalid Date 防御 |

---

## 当前多租户完成度

| 模块 | 完成度 | 本次变化 |
|------|--------|----------|
| Auth + Session | 100% | — |
| Thread CRUD + 隔离 | 100% | — |
| Per-user 文件路径 | 100% | — |
| Sandbox 路径 + 防穿越 | 100% | — |
| Rate Limiting | 100% | — |
| Memory PG 读写 | 95% | 🆕 从 0% 提升 |
| History/Resume 上下文 | 95% | 🆕 从 0% 提升 |
| Marketplace tool gating | 95% | 🆕 从 30% 提升 |
| Skill Catalog 决议 | 95% | 🆕 从 70% 提升（含 marketplace-only skill 支持） |
| Marketplace seed 幂等 | 100% | 🆕 merge() + 模块级标志 + 测试不泄漏 |
| Nginx auth_request | 100% | 🆕 已验证 401/200 |
| MCP per-user | 80% | 🆕 从 60% 提升（get_cached_mcp_tools 传 user_id） |
| Skills custom per-user | 80% | 🆕 从 65% 提升（全链路 user_id 已接通） |
| 本地开发体验 | 100% | 🆕 固定 ID dev 账号 + 自动 install marketplace skills |
| Soul per-user | 70% | — |

---

## 第二阶段修复（P0/P1 推进 + 本地开发体验）

### Issue 6: Marketplace seed 每次重启重复插入

**根因**: `_ensure_seed_data()` 只检查 `MarketplaceTool` 表是否为空，不检查 `MarketplaceSkill`。且每次 API 调用都触发检查。

**修复**: 改用 `db.merge()`（按 PK upsert），加模块级 `_seed_done` 标志避免重复 DB 查询。

**文件**: `backend/app/gateway/routers/marketplace.py`

### Issue 7: 测试数据泄漏到生产数据库

**根因**: `test_skill_catalog_resolver.py` 的 `db_session` fixture 在 `commit()` 后 `rollback()` 无效，每次测试留下 3 条 `MarketplaceSkill` 行。

**修复**: 使用 connection-level transaction + SAVEPOINT 模式。测试内的 `commit()` 只提交到 savepoint，fixture teardown 时 rollback 整个外层事务。

**文件**: `backend/tests/test_skill_catalog_resolver.py`

### Issue 8: 本地开发账号每次重启丢失状态

**现象**: 每次 `make dev` 重启后，用 `dev@allo.local` 登录看不到之前安装的 marketplace skills。

**根因链**:
1. 用户之前手动注册 `dev@allo.local`，每次注册创建新 user + 新 org（设计预期）
2. Session 过期后无法登录 → 重新注册 → 新 org → install 记录绑在旧 org 上
3. 28 个孤立的 "Local Dev's Organization" 累积在数据库中

**修复（三层）**:

1. **`dev_seed.py`**: Gateway 启动时自动确保 `dev@allo.local` 存在，使用固定 ID：
   - `user_id = 00000000-0000-0000-0000-000000000001`
   - `org_id = 00000000-0000-0000-0000-000000000001`
   - 如果邮箱已存在但 ID 不匹配，自动迁移到固定 ID

2. **自动 install marketplace skills**: 每次启动时检查 dev org 是否缺少 marketplace install，自动补全。

3. **仅开发环境生效**: `ALLO_ENV != 'production'` 时才运行。

**验证**: 无痕浏览器登录 → 安装 skill → 关闭浏览器 → 重新登录 → skill 仍在 ✅

### Issue 9: Nginx auth_request 验证

**状态**: `nginx.local.conf` 已配置 `/_auth/langgraph` internal location，LangGraph 路由已启用 `auth_request`。

**验证**:
```
curl http://localhost:2026/api/langgraph/info          → 401
curl -H "Cookie: session_token=..." http://...         → 200
```

### Issue 10: MCP per-user 接通

**修复**: `tools.py` 中 `get_cached_mcp_tools()` 调用时传入 `ctx.user_id`，启用 per-user MCP 缓存隔离。

**文件**: `backend/packages/harness/deerflow/tools/tools.py`

### Issue 11: Skills custom 目录全链路确认

**验证结果**: `load_skills(user_id=...)` 在以下三个调用点都正确传递了 user_id：
- `skill_catalog_resolver.py:43` — Gateway API
- `prompt.py:407` — Runtime prompt 构建
- `agent.py:416,448` — Agent 构建

全链路已接通，`users/{user_id}/skills/custom/` 目录会被正确发现。

---

## 完整提交记录

```
d9df5f0 fix: dev seed auto-installs all marketplace skills for dev org
86aa06b fix: dev seed handles email conflict by migrating to fixed ID
2f06f5f fix: stable dev account with fixed IDs and test data isolation
ca6f662 fix: prevent test data leaking into production DB and harden seed idempotency
a48e610 fix: marketplace seed idempotency and per-user MCP tool loading
0ef509b docs: add detailed changelog for 2026-04-03 debugging session
aad425b fix: resolve history context loss, memory write failure, marketplace loop, and skill visibility
```

## 下一步优先级

1. **P1**: Soul per-user 完善（runtime 预解析已接入，需验证端到端）
2. **P2**: Sandbox Docker per-user pool
3. **P2**: 生产部署（systemd + HTTPS + 域名）
4. **P2**: 备份策略
5. **P3**: 新用户注册时自动 install 免费 marketplace skills（产品体验优化）
