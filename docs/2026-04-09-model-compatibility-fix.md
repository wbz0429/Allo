# 模型兼容性与错误回传修复记录

日期：2026-04-09

## 问题背景

线上三个 P0 问题：

1. **Thread `33734f98` 无回复** — `gpt-5.4 -> kkcode.vip/v1` 发生 `APIConnectionError`，用户看到空白页面
2. **Thread `7f0f5dde` 很快结束** — `kimi-for-coding` 在 thinking + tool-call 多轮时，上游报 `thinking is enabled but reasoning_content is missing in assistant tool call message`
3. **模型接入门槛过高** — `supports_thinking` 守卫导致不声明该字段的模型被强制降级

## 根因分析

### 问题 1：前端无错误反馈

`useStream` hook 没有 `onError` 回调。LangGraph run 失败时，前端不知道，用户只看到空白。

### 问题 2：Kimi reasoning_content 丢失（核心难点）

排查链路：

1. 初始假设：middleware 层剥离 reasoning_content → **否决**，因为 middleware 操作 LangChain message 对象，无法影响 HTTP payload
2. 第二假设：做 `PatchedChatOpenAI` override `_get_request_payload()` 回填 → **部分正确**，但部署后发现 `additional_kwargs` 里根本没有 reasoning_content
3. 加调试日志确认：`_get_request_payload` 被调用了，但 `has_reasoning=False`
4. 最终根因：LangChain `ChatOpenAI` 的 streaming chunk 解析函数 `_convert_delta_to_message_chunk` **完全忽略** `reasoning_content` 字段。它只处理 `content`、`function_call`、`tool_calls`，不会把 streaming delta 里的 `reasoning_content` 存进 `additional_kwargs`
5. 对比：`ChatDeepSeek` 有自己的 chunk 解析逻辑会保留 reasoning_content，所以 `PatchedChatDeepSeek` 能工作

### 问题 3：supports_thinking 守卫

`factory.py` 里 `if not model_config.supports_thinking: raise ValueError` 阻止了不声明该字段的模型使用 thinking 设置。`lead_agent/agent.py` 里还有一层 `thinking_enabled = False` 降级。

### 部署踩坑：双 config.yaml

项目有两个 config.yaml：
- `/srv/allo/config.yaml` — 项目根目录
- `/srv/allo/backend/config.yaml` — backend 目录

LangGraph 从 `backend/` 启动，加载的是后者。我们一开始改的是前者，导致配置不生效。

### Kimi API 端点

Kimi Code 的 API 端点不是 `api.moonshot.cn`，而是 `api.kimi.com/coding/v1`，模型名 `kimi-for-coding`。

## 修复方案

### Commit 1: `600b645` — 主体修复

- **PatchedChatOpenAI**（`models/patched_openai.py`）：override `_get_request_payload()` 从 `additional_kwargs` 回填 reasoning_content 到 HTTP payload
- **移除 supports_thinking 守卫**：`factory.py` 删除 ValueError，`agent.py` 改为 info log
- **前端 onError**：`useStream` 加 `onError` 回调，显示 toast

### Commit 2: `5b7cbc3` — 模型 fallback

当前端传来的 model_name 不在 config 里时（如旧 thread 引用已删除的模型），fallback 到默认模型而不是 raise ValueError。

### Commit 3: `450202e` — 流式 reasoning_content 捕获（关键修复）

Override `_convert_chunk_to_generation_chunk()`，从 streaming delta 的 `reasoning_content` 字段提取内容存入 `AIMessageChunk.additional_kwargs`。没有这一步，`_get_request_payload` 的回填逻辑是空转的。

## 验证结果

- kimi-for-coding 多轮 tool-call 对话正常，不再报 reasoning_content 错误
- 模型连接失败时前端显示 toast 提示
- 不声明 supports_thinking 的模型正常工作

## 受影响文件

```
backend/packages/harness/deerflow/models/patched_openai.py    # 新建
backend/packages/harness/deerflow/models/factory.py           # 移除 thinking 守卫
backend/packages/harness/deerflow/agents/lead_agent/agent.py  # 移除降级 + 加 fallback
backend/tests/test_patched_openai.py                          # 新建
backend/tests/test_model_factory.py                           # 更新测试
backend/tests/test_lead_agent_model_resolution.py             # 更新测试
frontend/src/core/threads/hooks.ts                            # onError 回调
frontend/src/core/i18n/locales/{types,en-US,zh-CN}.ts         # 错误提示 i18n
```
