# 知识库功能 — 当前状态与待解决问题

## 已完成的功能

### 后端
- 文件系统优先架构：上传存磁盘 + markdown，不做 embedding
- 4 个 agent 工具：`knowledge_base_list`、`knowledge_base_read`、`knowledge_base_keyword_search`、`knowledge_base_search`
- 工具参数已简化：不需要传 kb_id，内部通过 `ensure_config()` + `get_user_context()` 自动获取 org_id
- KB 上下文注入到 agent 系统提示词（文档文件名列表 + 工具使用指引）
- `langgraph_runtime.py` 预解析 KB 列表，支持 `kb_ids` 过滤
- 新增端点：`POST /index`（按需 embedding）、`POST /keyword-search`、`GET /download`、`GET /content`
- 删除时清理磁盘文件
- `KnowledgeBaseStore` 抽象接口 + Postgres 实现，注册到 gateway 和 langgraph 两个进程
- `_resolve_user_from_auth_id` fallback：从 `organization_members` 表解析 org_id

### 前端
- 输入框工具栏「知识库」按钮，Popover 多选
- 选中的 KB 以 badge 形式显示在输入框上方
- 发送消息时 `kb_ids` 传入 `runContext`
- 消息气泡上方显示 KB badges（DatabaseIcon + 名称）
- KB 管理页面：上传、列表、删除、搜索

### 版本标签
- `v0.5.0-kb-filesystem-first` — 文件系统架构 + 基础 API
- `v0.6.0-kb-mention-tools` — @mention + 简化工具 + 提示词优化

---

## 核心问题：新对话第一条消息 context 丢失

### 现象
用户新建对话，选中知识库，发送第一条消息。agent 看不到选中的知识库，提示词里没有 KB 信息，工具调用返回 "Cannot determine organization context"。

### 根因
LangGraph SDK（`@langchain/langgraph-sdk`）在新建 thread 时，前端通过 `thread.submit(input, { context: runContext })` 传的 `context` 字段**不会**出现在后端的 `config["configurable"]` 里。

具体表现：
- `configurable` 里有 `user_id`、`langgraph_auth_user_id` 等字段，但值为**空字符串**
- 没有 `org_id`、`kb_ids`、`model_name`、`thinking_enabled` 等前端传的字段
- `get_user_context()` 因为 `user_id` 为空返回 None
- 所有 fallback（thread 表查询、auth_id 查询）都因为 user_id 为空而失败
- 整个预解析块（skill、memory、soul、marketplace、KB）被跳过

### 第二条消息开始正常
SDK 在第一条消息后会带上 `checkpoint_id`，此时 `context` 字段能正确传到 `configurable`，所有字段（`kb_ids`、`org_id`、`user_id` 等）都在。

### 已尝试的修复
1. `_resolve_user_from_thread` — 新对话时 thread 还没在 DB 里，返回 None
2. `_resolve_user_from_auth_id` — `langgraph_auth_user_id` 是空字符串，无法查询
3. `org_id == "default"` fallback — ctx 本身就是 None，走不到这个分支

### 可能的解决方向
1. **前端绕过**：在 `sendMessage` 里，新对话第一条消息时先调 gateway API 创建 thread 并写入 metadata（包含 kb_ids），然后 langgraph 从 thread metadata 读取
2. **LangGraph SDK 层面**：调查 `useStream` hook 的 `submit` 方法在新 thread 时为什么不传 context，可能需要升级 SDK 或用不同的 API
3. **Nginx 层面**：nginx 已经注入了 `X-User-Id` 和 `X-Org-Id` header 到 LangGraph API 请求，但 LangGraph Server 的 noop auth 没有把这些 header 映射到 configurable。可以自定义 auth handler 来注入
4. **Gateway 预注入**：在 gateway 的 `createThreadRun` 时，把 `kb_ids` 和 `org_id` 写入 LangGraph thread 的 metadata，langgraph 从 metadata 读取而不是从 configurable

---

## 次要问题

### agent 有时不调用工具
- 提示词已经强化（"你必须调用工具才能看到文件内容"），但某些模型/模式下 agent 仍然选择不调用工具直接回答
- flash 模式（`thinking_enabled: False`）下更容易出现
- 可能需要进一步强化提示词，或在 agent 逻辑层面强制 tool use

### kb_ids 过滤在新对话不生效
- 即使 KB 上下文注入成功（通过 fallback），`kb_ids` 在新对话第一条消息时始终为 None
- 结果是注入全部 KB 而不是用户选中的 KB
- 第二条消息开始 `kb_ids` 正常传递，过滤生效

### 工具内 org_id 解析
- 工具通过 `ensure_config()` 获取 `RunnableConfig`，再用 `get_user_context()` 解析 org_id
- 当 configurable 里 `user_id` 为空时，工具返回 "Cannot determine organization context"
- 这和新对话第一条消息的问题是同一个根因

---

## 2026-04-06 修复进展

### 已验证修复
- **新对话第一条消息选择知识库失效**：已修复
  - 后端新增 `KnowledgeBaseSelectionMiddleware`，从首条消息的 `additional_kwargs.knowledge_bases` 兜底解析已选知识库
  - 前端修复 new chat handoff，跳转到真实 thread 页后会保留并重发 `knowledgeBases`
  - 线上已联调通过：第一条消息已能生效
- **新对话第一条消息上传文件失败**：已修复
  - 前端修复 new chat handoff，首条消息现在会保留并重发 `files`
  - 线上日志已确认：文件成功上传到 thread 对应 uploads 目录，随后 run 创建并执行成功

### 当前版本点
- `796870b0f` — `fix: inject selected KBs into first-message prompt context`
- `98f0e891d` — `fix: preserve selected KBs in new chat handoff`
- `60c5ce979` — `fix: preserve first-message files in new chat handoff`

### 仍待收尾的问题
- `KnowledgeBaseSelectionMiddleware` 日志中仍可能出现 `resolved_count=0 org_id=None`
  - 这不影响首条消息把已选 KB 名称注入提示上下文
  - 但会影响自动展开该 KB 下文件列表的稳定性
- LangGraph 日志里存在独立 warning：
  - `PostgresModelKeyResolver` 在 `resolve_key()` 中错误删除了 `self._async_session_factory`
  - 该问题与 KB / 文件 handoff 无关，但会污染日志并影响 per-run key 解析稳定性
