# Dev Follow-up Summary - 2026-04-05

## Scope

This follow-up captures the fixes applied after `dev-summary-2026-04-05.md`, focused on:

- first-message delivery from `/workspace/chats/new`
- upload path alignment for user-scoped thread storage
- LangGraph runtime compatibility when `Runtime.context` is `None`

## Problems We Hit

### 1. Welcome page first message did not enter the real thread correctly

Observed behavior:

- first message from `/workspace/chats/new` sometimes created an empty thread
- the page did not jump correctly, or the new thread opened without messages

Root causes identified during debugging:

- `useStream` was being triggered too early while the page was still in the `new thread` state
- the first submit path mixed three responsibilities in one step: create thread, navigate, and stream the first message
- this caused thread creation conflicts and unstable SDK lifecycle timing

Resolution:

- changed the welcome-page flow to a handoff model
- on `/workspace/chats/new`, the first text-only message is stored temporarily in `sessionStorage`
- the UI navigates to the real `/workspace/chats/<threadId>` page first
- the real thread page consumes that pending message only after the stream hook is bound to the real thread

Result:

- first-message creation from `/workspace/chats/new` is now logically connected end-to-end
- empty-thread creation caused by the old welcome-page timing path is avoided

### 2. Uploaded files were saved but the agent could not read them

Observed behavior:

- upload API returned success
- files appeared uploaded from the UI perspective
- the agent still could not find or read uploaded files

Root cause:

- write path and read path were inconsistent
- gateway upload routes still wrote to the legacy thread-scoped uploads directory
- middleware and runtime helpers had already been updated to read from user-scoped thread directories

Resolution:

- aligned `backend/app/gateway/routers/uploads.py` with user-scoped paths
- `upload_files`, `list_uploaded_files`, and `delete_uploaded_file` now use `user_sandbox_uploads_dir(user_id, thread_id)` when `user_id` is available
- legacy thread-only fallback is preserved for cases without `user_id`

Result:

- files now land in the same user-scoped path that the runtime middleware reads from

### 3. Multiple runtime crashes caused by `Runtime.context` being `None`

Observed behavior:

- some runs started correctly but failed mid-run or during post-processing
- failures appeared in different middleware stages as the main message chain became healthier

Root cause:

- several middlewares still assumed `runtime.context` was always a dict
- on this LangGraph runtime, `Runtime.context` may be `None`
- as earlier failures were fixed, later middleware stages started to execute and exposed additional old assumptions

Fixes applied:

- `uploads_middleware.py` already used safe runtime helpers
- `sandbox/middleware.py` was updated to guard missing `runtime.context`
- `loop_detection_middleware.py` was updated to use `get_runtime_thread_id(runtime)` instead of `runtime.context.get("thread_id")`

Result:

- the run no longer fails at these two middleware checkpoints because of `NoneType.get(...)`

## Verification Performed

Frontend:

- `node --test src/core/threads/pending.test.ts`
- `node --test src/app/workspace/chats/chat-page-handoff.test.ts`
- `node --test src/core/threads/hooks.test.ts`
- `node --test src/core/api/stream-mode.test.ts`
- `pnpm lint`
- `pnpm typecheck`
- `pnpm build`

Backend:

- `uv run --group dev pytest tests/test_uploads_router.py -q`
- `uv run --group dev pytest tests/test_uploads_middleware_core_logic.py -q`
- `uv run --group dev pytest tests/test_sandbox_middleware.py -q`
- `uv run --group dev pytest tests/test_loop_detection_middleware.py -q`

## Current Status

- first-message handoff from the welcome page is logically connected
- upload storage paths are aligned with user-scoped runtime reads
- known `Runtime.context=None` crashes in sandbox and loop-detection middleware are fixed

## Remaining Operational Concern

The main user-facing issue is now performance rather than correctness.

Observed from server logs:

- LangGraph is running with only `1 background worker`
- runs are serialized, so concurrent threads wait in queue
- some runs show large queue wait times and total durations (tens of seconds)
- graph load is still reported as slow in logs
- the runtime is using shared event loops with blocking operations allowed

This means two active threads can feel very slow even when the logic is functionally correct.
