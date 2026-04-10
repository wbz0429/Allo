# Model Error Propagation & Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three P0 issues: (1) surface model connection errors to users instead of silent failure, (2) fix Kimi/OpenAI-compatible model reasoning_content compatibility for multi-turn tool calls, (3) simplify model acceptance — stop gating on `supports_thinking` and treat all models uniformly.

**Architecture:** The changes span backend model factory, a new middleware for reasoning_content stripping, the lead agent's thinking fallback logic, and frontend error display. The approach is: make the backend tolerant of any OpenAI-compatible model (no thinking/reasoning guards), strip reasoning_content from history before sending to models that didn't produce it, and surface model errors as visible messages in the frontend.

**Tech Stack:** Python (LangGraph middleware, model factory), TypeScript/React (Next.js frontend, `useStream` hook, toast notifications)

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/packages/harness/deerflow/models/factory.py` | Remove `supports_thinking` guard, simplify thinking enable/disable |
| Create | `backend/packages/harness/deerflow/agents/middlewares/reasoning_content_middleware.py` | Strip `reasoning_content` from assistant messages before model call for models that don't understand it |
| Modify | `backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py` | Register new middleware in `_build_runtime_middlewares` |
| Modify | `backend/packages/harness/deerflow/agents/lead_agent/agent.py` | Remove thinking fallback guard, always pass `thinking_enabled` through |
| Modify | `backend/packages/harness/deerflow/config/model_config.py` | Keep `supports_thinking` field but make it purely informational (no behavioral gating) |
| Modify | `frontend/src/core/threads/hooks.ts` | Add `onError` handling to `useStream`, show toast on stream errors |
| Modify | `backend/tests/test_model_factory.py` | Update tests for removed guard |
| Modify | `backend/tests/test_lead_agent_model_resolution.py` | Update test for removed thinking fallback |
| Create | `backend/tests/test_reasoning_content_middleware.py` | Tests for the new middleware |

---

### Task 1: Add reasoning_content stripping middleware (backend)

**Files:**
- Create: `backend/packages/harness/deerflow/agents/middlewares/reasoning_content_middleware.py`
- Create: `backend/tests/test_reasoning_content_middleware.py`
- Modify: `backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py`

This middleware solves the Kimi problem: when a model with thinking enabled produces `reasoning_content` in assistant messages, and those messages are sent back in subsequent turns, models that don't expect it (or the same model in a different state) reject the payload with errors like "reasoning_content is missing in assistant tool call message". The fix: strip `reasoning_content` from `additional_kwargs` on all assistant messages before the model call, so the model never sees stale reasoning data.

- [ ] **Step 1: Write the failing test for reasoning_content stripping**

```python
# backend/tests/test_reasoning_content_middleware.py
"""Tests for ReasoningContentMiddleware."""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from deerflow.agents.middlewares.reasoning_content_middleware import ReasoningContentMiddleware


def _make_ai_message(content: str, *, reasoning_content: str | None = None, tool_calls: list | None = None) -> AIMessage:
    additional_kwargs = {}
    if reasoning_content is not None:
        additional_kwargs["reasoning_content"] = reasoning_content
    return AIMessage(content=content, additional_kwargs=additional_kwargs, tool_calls=tool_calls or [])


def test_strips_reasoning_content_from_ai_messages():
    """reasoning_content should be removed from additional_kwargs before model call."""
    mw = ReasoningContentMiddleware()
    messages = [
        HumanMessage(content="hello"),
        _make_ai_message("thinking response", reasoning_content="I thought about this"),
        HumanMessage(content="follow up"),
    ]

    request = MagicMock()
    request.messages = list(messages)

    captured_request = None

    def handler(req):
        nonlocal captured_request
        captured_request = req
        return MagicMock()

    mw.wrap_model_call(request, handler)

    # The AI message in the request should have reasoning_content stripped
    ai_msg = captured_request.messages[1]
    assert "reasoning_content" not in ai_msg.additional_kwargs


def test_strips_reasoning_content_from_tool_call_messages():
    """reasoning_content should be stripped from AI messages that have tool_calls."""
    mw = ReasoningContentMiddleware()
    messages = [
        HumanMessage(content="read the file"),
        _make_ai_message(
            "I'll read that",
            reasoning_content="Let me think about which file",
            tool_calls=[{"id": "call_1", "name": "read_file", "args": {"path": "/tmp/test"}}],
        ),
        ToolMessage(content="file contents here", tool_call_id="call_1", name="read_file"),
        HumanMessage(content="now what?"),
    ]

    request = MagicMock()
    request.messages = list(messages)

    captured_request = None

    def handler(req):
        nonlocal captured_request
        captured_request = req
        return MagicMock()

    mw.wrap_model_call(request, handler)

    ai_msg = captured_request.messages[1]
    assert "reasoning_content" not in ai_msg.additional_kwargs
    # Tool message should be untouched
    assert captured_request.messages[2].content == "file contents here"


def test_no_op_when_no_reasoning_content():
    """Messages without reasoning_content should pass through unchanged."""
    mw = ReasoningContentMiddleware()
    messages = [
        HumanMessage(content="hello"),
        _make_ai_message("response"),
        HumanMessage(content="follow up"),
    ]

    request = MagicMock()
    request.messages = list(messages)

    captured_request = None

    def handler(req):
        nonlocal captured_request
        captured_request = req
        return MagicMock()

    mw.wrap_model_call(request, handler)

    # Should pass through the original request (no override needed)
    assert captured_request is request


def test_preserves_other_additional_kwargs():
    """Other keys in additional_kwargs should not be affected."""
    mw = ReasoningContentMiddleware()
    ai_msg = AIMessage(
        content="response",
        additional_kwargs={"reasoning_content": "thinking", "custom_key": "keep_me"},
    )
    messages = [HumanMessage(content="hi"), ai_msg]

    request = MagicMock()
    request.messages = list(messages)

    captured_request = None

    def handler(req):
        nonlocal captured_request
        captured_request = req
        return MagicMock()

    mw.wrap_model_call(request, handler)

    cleaned_ai = captured_request.messages[1]
    assert "reasoning_content" not in cleaned_ai.additional_kwargs
    assert cleaned_ai.additional_kwargs["custom_key"] == "keep_me"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_reasoning_content_middleware.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deerflow.agents.middlewares.reasoning_content_middleware'`

- [ ] **Step 3: Implement the middleware**

```python
# backend/packages/harness/deerflow/agents/middlewares/reasoning_content_middleware.py
"""Middleware to strip reasoning_content from assistant messages before model calls.

Some OpenAI-compatible models (e.g., Kimi, DeepSeek via gateways) include
reasoning_content in their responses when thinking mode is enabled. When these
messages are sent back in subsequent turns, other models (or the same model in
a different state) may reject the payload because they don't expect
reasoning_content in the message history.

This middleware removes reasoning_content from all AI messages before the model
call, preventing compatibility errors in multi-turn conversations.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)


class ReasoningContentMiddleware(AgentMiddleware[AgentState]):
    """Strip reasoning_content from AI messages before model invocation."""

    def _strip_reasoning_content(self, messages: list) -> list | None:
        """Return cleaned message list, or None if no changes needed."""
        needs_cleaning = False
        for msg in messages:
            if isinstance(msg, AIMessage) and "reasoning_content" in msg.additional_kwargs:
                needs_cleaning = True
                break

        if not needs_cleaning:
            return None

        cleaned = []
        count = 0
        for msg in messages:
            if isinstance(msg, AIMessage) and "reasoning_content" in msg.additional_kwargs:
                new_kwargs = {k: v for k, v in msg.additional_kwargs.items() if k != "reasoning_content"}
                cleaned.append(msg.model_copy(update={"additional_kwargs": new_kwargs}))
                count += 1
            else:
                cleaned.append(msg)

        logger.debug("Stripped reasoning_content from %d AI message(s)", count)
        return cleaned

    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        cleaned = self._strip_reasoning_content(request.messages)
        if cleaned is not None:
            request = request.override(messages=cleaned)
        return handler(request)

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        cleaned = self._strip_reasoning_content(request.messages)
        if cleaned is not None:
            request = request.override(messages=cleaned)
        return await handler(request)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_reasoning_content_middleware.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Register middleware in the runtime middleware chain**

In `backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py`, add the `ReasoningContentMiddleware` to `_build_runtime_middlewares` — it should run before `DanglingToolCallMiddleware` and `ToolErrorHandlingMiddleware`, right after the sandbox/uploads middlewares:

```python
# In _build_runtime_middlewares(), after the uploads/kb block and before dangling tool call:

from deerflow.agents.middlewares.reasoning_content_middleware import ReasoningContentMiddleware

middlewares.append(ReasoningContentMiddleware())
```

The updated function body becomes:

```python
def _build_runtime_middlewares(
    *,
    include_uploads: bool,
    include_dangling_tool_call_patch: bool,
    lazy_init: bool = True,
) -> list[AgentMiddleware]:
    """Build shared base middlewares for agent execution."""
    from deerflow.agents.middlewares.reasoning_content_middleware import ReasoningContentMiddleware
    from deerflow.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
    from deerflow.sandbox.middleware import SandboxMiddleware

    middlewares: list[AgentMiddleware] = [
        ThreadDataMiddleware(lazy_init=lazy_init),
        SandboxMiddleware(lazy_init=lazy_init),
    ]

    if include_uploads:
        from deerflow.agents.middlewares.uploads_middleware import UploadsMiddleware

        middlewares.insert(1, UploadsMiddleware())
        from deerflow.agents.middlewares.kb_selection_middleware import KnowledgeBaseSelectionMiddleware

        middlewares.insert(2, KnowledgeBaseSelectionMiddleware())

    # Strip reasoning_content before model sees the history
    middlewares.append(ReasoningContentMiddleware())

    if include_dangling_tool_call_patch:
        from deerflow.agents.middlewares.dangling_tool_call_middleware import DanglingToolCallMiddleware

        middlewares.append(DanglingToolCallMiddleware())

    middlewares.append(ToolErrorHandlingMiddleware())
    return middlewares
```

- [ ] **Step 6: Run full test suite to verify no regressions**

Run: `cd backend && make test`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/packages/harness/deerflow/agents/middlewares/reasoning_content_middleware.py \
       backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py \
       backend/tests/test_reasoning_content_middleware.py
git commit -m "$(cat <<'EOF'
feat: add ReasoningContentMiddleware to strip reasoning_content from history

Fixes Kimi/OpenAI-compatible model errors where reasoning_content in
assistant tool-call messages causes upstream rejection. The middleware
strips reasoning_content from all AI messages before model invocation.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Simplify model acceptance — remove thinking guards (backend)

**Files:**
- Modify: `backend/packages/harness/deerflow/models/factory.py`
- Modify: `backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- Modify: `backend/tests/test_model_factory.py`
- Modify: `backend/tests/test_lead_agent_model_resolution.py`

Currently the system gates on `supports_thinking`: if a model doesn't declare it, thinking is forcibly disabled and the factory raises `ValueError` if thinking is requested with `when_thinking_enabled` set. The new behavior: treat all models uniformly. If `when_thinking_enabled` is configured, use it. If not, skip it. No guards, no fallbacks. The model either handles it or the error gets caught by existing error handling.

- [ ] **Step 1: Update factory tests — remove the "raises when not supported" tests, update expectations**

In `backend/tests/test_model_factory.py`:

Replace `test_thinking_enabled_raises_when_not_supported_but_when_thinking_enabled_is_set` with a test that shows thinking settings are applied regardless of `supports_thinking`:

```python
def test_thinking_enabled_applies_settings_regardless_of_supports_thinking(monkeypatch):
    """when_thinking_enabled settings should be applied even when supports_thinking=False.
    We no longer gate on supports_thinking — all models are treated uniformly."""
    wte = {"thinking": {"type": "enabled", "budget_tokens": 5000}}
    cfg = _make_app_config([_make_model("no-think", supports_thinking=False, when_thinking_enabled=wte)])
    _patch_factory(monkeypatch, cfg)

    FakeChatModel.captured_kwargs = {}
    factory_module.create_chat_model(name="no-think", thinking_enabled=True)

    assert FakeChatModel.captured_kwargs.get("thinking") == {"type": "enabled", "budget_tokens": 5000}
```

Replace `test_thinking_enabled_raises_for_empty_when_thinking_enabled_explicitly_set` with:

```python
def test_thinking_enabled_with_empty_when_thinking_enabled_is_noop(monkeypatch):
    """Empty when_thinking_enabled with thinking_enabled=True should not crash — just a no-op merge."""
    cfg = _make_app_config([_make_model("no-think-empty", supports_thinking=False, when_thinking_enabled={})])
    _patch_factory(monkeypatch, cfg)

    FakeChatModel.captured_kwargs = {}
    factory_module.create_chat_model(name="no-think-empty", thinking_enabled=True)
    # No crash, model created successfully
    assert FakeChatModel.captured_kwargs.get("model") == "no-think-empty"
```

- [ ] **Step 2: Run tests to verify they fail (old guard still in place)**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_model_factory.py -v`
Expected: The two new tests FAIL because factory still raises `ValueError`

- [ ] **Step 3: Update factory.py — remove supports_thinking guard**

In `backend/packages/harness/deerflow/models/factory.py`, replace lines 48-52:

```python
    # OLD:
    if thinking_enabled and has_thinking_settings:
        if not model_config.supports_thinking:
            raise ValueError(f"Model {name} does not support thinking. Set `supports_thinking` to true in the `config.yaml` to enable thinking.") from None
        if effective_wte:
            model_settings_from_config.update(effective_wte)
```

With:

```python
    # NEW: Apply thinking settings unconditionally — no supports_thinking guard
    if thinking_enabled and has_thinking_settings:
        if effective_wte:
            model_settings_from_config.update(effective_wte)
```

- [ ] **Step 4: Update lead_agent/agent.py — remove thinking fallback**

In `backend/packages/harness/deerflow/agents/lead_agent/agent.py`, remove lines 404-406:

```python
    # OLD:
    if thinking_enabled and not model_config.supports_thinking:
        logger.warning(f"Thinking mode is enabled but model '{model_name}' does not support it; fallback to non-thinking mode.")
        thinking_enabled = False
```

Replace with a simple info log:

```python
    # NEW: Log thinking state for debugging, but don't override the caller's choice
    if thinking_enabled and not model_config.supports_thinking:
        logger.info("Thinking mode requested for model '%s' which does not declare supports_thinking; proceeding anyway.", model_name)
```

- [ ] **Step 5: Update lead agent test**

In `backend/tests/test_lead_agent_model_resolution.py`, update `test_make_lead_agent_disables_thinking_when_model_does_not_support_it`:

```python
def test_make_lead_agent_passes_thinking_through_regardless_of_supports_thinking(monkeypatch):
    """Thinking should be passed through to create_chat_model even when model doesn't declare supports_thinking."""
    app_config = _make_app_config([_make_model("safe-model", supports_thinking=False)])

    import deerflow.tools as tools_module

    monkeypatch.setattr(lead_agent_module, "get_app_config", lambda: app_config)
    monkeypatch.setattr(tools_module, "get_available_tools", lambda **kwargs: [])
    monkeypatch.setattr(lead_agent_module, "_build_middlewares", lambda config, model_name, agent_name=None, **kwargs: [])

    captured: dict[str, object] = {}

    def _fake_create_chat_model(*, name, thinking_enabled, reasoning_effort=None):
        captured["name"] = name
        captured["thinking_enabled"] = thinking_enabled
        captured["reasoning_effort"] = reasoning_effort
        return object()

    monkeypatch.setattr(lead_agent_module, "create_chat_model", _fake_create_chat_model)
    monkeypatch.setattr(lead_agent_module, "create_agent", lambda **kwargs: kwargs)

    result = lead_agent_module.make_lead_agent(
        {
            "configurable": {
                "model_name": "safe-model",
                "thinking_enabled": True,
                "is_plan_mode": False,
                "subagent_enabled": False,
            }
        }
    )

    assert captured["name"] == "safe-model"
    # NEW: thinking_enabled is passed through, not overridden to False
    assert captured["thinking_enabled"] is True
    assert result["model"] is not None
```

- [ ] **Step 6: Run all tests**

Run: `cd backend && make test`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/packages/harness/deerflow/models/factory.py \
       backend/packages/harness/deerflow/agents/lead_agent/agent.py \
       backend/tests/test_model_factory.py \
       backend/tests/test_lead_agent_model_resolution.py
git commit -m "$(cat <<'EOF'
feat: remove supports_thinking guard — treat all models uniformly

Models no longer need supports_thinking=true to accept thinking settings.
Any model with when_thinking_enabled configured will receive those settings
when thinking_enabled=True. This simplifies onboarding new OpenAI-compatible
models — if it can handle tool calls and we can parse responses, it works.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Surface model errors to frontend (frontend)

**Files:**
- Modify: `frontend/src/core/threads/hooks.ts`

The current problem: when a model call fails (e.g., `APIConnectionError`), the LangGraph run fails silently. The frontend's `useStream` hook has no `onError` handler, so the user sees nothing — just an empty response. The fix: catch stream errors and show a toast notification.

The `useStream` hook from `@langchain/langgraph-sdk/react` exposes an `error` property and an `onError` callback. We need to use both: `onError` for immediate toast feedback, and watching `thread.error` for errors that occur during reconnection.

- [ ] **Step 1: Add onError to useStream and error effect**

In `frontend/src/core/threads/hooks.ts`, add `onError` callback to the `useStream` configuration (inside the `useStream<AgentThreadState>({...})` call, after the `onFinish` callback):

```typescript
    onError(error) {
      console.error("Stream error:", error);
      const message =
        error instanceof Error ? error.message : "Unknown stream error";
      // Surface connection / model errors to the user
      if (
        message.includes("Connection") ||
        message.includes("connect") ||
        message.includes("timeout") ||
        message.includes("ECONNREFUSED") ||
        message.includes("fetch failed")
      ) {
        toast.error(t.errors?.modelConnectionFailed ?? "Model service connection failed. Please try again later.");
      } else {
        toast.error(t.errors?.streamError ?? `Stream error: ${message}`);
      }
      // Sync failure to backend
      void syncThreadRun({
        status: "failed",
        finished_at: new Date().toISOString(),
        error_message: message,
      });
      currentRunIdRef.current = null;
      setOptimisticMessages([]);
    },
```

- [ ] **Step 2: Add i18n keys for error messages**

Check the i18n files and add error message keys. Find the i18n files:

Run: `find frontend/src/core/i18n -name "*.ts" -o -name "*.json" | head -10`

Then add to both en-US and zh-CN locale files under an `errors` key:

```typescript
// en-US
errors: {
  modelConnectionFailed: "Model service connection failed. Please try again later.",
  streamError: "An error occurred while processing your request.",
}

// zh-CN
errors: {
  modelConnectionFailed: "模型服务连接失败，请稍后重试。",
  streamError: "处理请求时发生错误。",
}
```

- [ ] **Step 3: Run frontend lint and typecheck**

Run: `cd frontend && pnpm lint && pnpm typecheck`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/core/threads/hooks.ts \
       frontend/src/core/i18n/
git commit -m "$(cat <<'EOF'
feat: surface model connection errors to users via toast

When a LangGraph stream fails (e.g., APIConnectionError from model
provider), show a toast notification instead of silent failure.
Connection-related errors get a specific "model service connection
failed" message; other errors show the error detail.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Deploy and verify on server

**Files:** None (operational task following SOP)

Follow the deployment SOP from `docs/server-dev-sop.md`.

- [ ] **Step 1: Create bundle and deploy**

```bash
# Local
git bundle create /tmp/update.bundle main --not a20fbbf
scp /tmp/update.bundle ubuntu@146.56.239.94:/tmp/update.bundle

# Server
sudo -u allo bash -c 'cd /srv/allo && git fetch /tmp/update.bundle main:update-ref && git merge update-ref --ff-only'
sudo -u allo bash -c 'cd /srv/allo/backend && uv sync'
sudo -u allo bash -c 'cd /srv/allo/frontend && CI=true pnpm install && pnpm build'
sudo systemctl restart allo-gateway allo-langgraph allo-frontend
```

- [ ] **Step 2: Health check**

```bash
sleep 15
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2024/ok && echo ' langgraph OK'
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/models && echo ' gateway OK'
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ && echo ' frontend OK'
```

- [ ] **Step 3: Verify error propagation**

Test with a model that has connectivity issues:
1. Send a message using `gpt-5.4` model
2. If `kkcode.vip` is unreachable, verify a toast error appears in the frontend
3. Check logs: `sudo journalctl -u allo-langgraph --since '2 min ago' --no-pager | grep -E 'error|Error'`

- [ ] **Step 4: Verify Kimi compatibility**

1. Send a message using `kimi-for-coding` model
2. Trigger a tool call (e.g., "read the file /mnt/user-data/workspace/test.txt")
3. After tool result returns, verify the model continues without "reasoning_content is missing" error
4. Check logs: `sudo journalctl -u allo-langgraph --since '3 min ago' --no-pager | grep -i 'reasoning_content\|kimi'`

- [ ] **Step 5: Verify model acceptance**

1. Confirm models without `supports_thinking: true` in config still work with thinking enabled from frontend
2. Check logs for the new info-level message instead of the old warning+fallback
