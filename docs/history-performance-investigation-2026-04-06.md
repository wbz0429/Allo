# History Performance Investigation - 2026-04-06

## Summary

This document captures the investigation into why thread switching, page refresh, and history loading feel extremely slow even after improving LangGraph run concurrency.

The conclusion is that the main bottleneck has shifted from run queueing to the `/threads/{thread_id}/history` path. History requests currently trigger the full lead-agent graph factory and expensive runtime store resolution, even though history retrieval should be much lighter than a real run.

## User-Visible Symptoms

- switching from one thread to another can take a very long time
- opening a thread while another thread is still running feels blocked
- refreshing a chat page can stall for many seconds
- newly created threads may briefly appear empty or incomplete before state catches up

## What Was Already Improved

LangGraph concurrency was partially improved by changing the service startup flags from:

```bash
langgraph dev --no-browser --allow-blocking
```

to:

```bash
langgraph dev --no-browser --allow-blocking --no-reload --n-jobs-per-worker 4
```

Observed effect:

- background workers increased from `1` to `4`
- `run_queue_ms` dropped from multi-second or 10s+ waits to sub-second waits in the inspected runs

This reduced run queue contention, but thread switching still felt very slow.

## Core Finding

The main bottleneck is now the history path, not the run queue.

### Evidence from logs

Observed on the server:

- `Slow graph load. Accessing graph 'lead_agent' took 24212.22ms` on `POST /threads/{thread_id}/history`
- another history request showed `Slow graph load ... 39119.3ms`
- by comparison, a `runs/stream` graph load in the same environment was around `1098.17ms`

This indicates that history requests are paying a very large graph initialization cost.

## Why History Is Heavy

### Graph entrypoint

`backend/langgraph.json` defines a single graph entrypoint:

```json
"graphs": {
  "lead_agent": "app.langgraph_runtime:make_lead_agent"
}
```

This means both of the following request types go through the same graph factory:

- `POST /threads/{thread_id}/history`
- `POST /threads/{thread_id}/runs/stream`

### Current behavior in `make_lead_agent`

`backend/app/langgraph_runtime.py` currently does all of the following before returning the graph:

- resolve user context from request or thread ownership fallback
- resolve enabled skill catalog
- resolve memory
- resolve soul
- resolve marketplace gating metadata

Then it delegates to `harness_make_lead_agent(config)`, which continues with:

- model resolution
- tool loading
- middleware construction
- prompt construction
- full agent creation

### Prompt-level cost

Inside the harness layer, prompt construction also loads expensive sections such as:

- skills prompt section
- memory context
- soul content

As a result, a history request behaves much more like "initialize the full agent" than "load persisted thread state".

## Verified Difference Between History and Real Runs

Low-risk diagnostics were added briefly to compare the config shape seen by `make_lead_agent()` for both request types.

### History request shape

Observed for `POST /threads/{thread_id}/history`:

- `thread_id` present
- `run_id` absent
- no direct user context in `configurable`
- user context resolved later from the `threads` table fallback

Representative summary:

- `configurable` contained: `thread_id`, `checkpoint_ns`, auth-related fields, runtime internals
- `metadata` was empty
- `run_id` was not present

### Run request shape

Observed for `POST /threads/{thread_id}/runs/stream`:

- `thread_id` present
- `run_id` present in `configurable`
- request metadata also included `run_id`, `thread_id`, `assistant_id`, and related fields

Representative summary:

- `configurable` contained: `thread_id`, `run_id`, `assistant_id`, `graph_id`, timing fields, runtime internals
- `metadata` also contained `run_id`, `thread_id`, `assistant_id`, and request metadata

## Root Cause Statement

The thread history path is expensive because the graph factory does not distinguish history/resume requests from real execution requests.

History requests are entering the same `make_lead_agent()` path and triggering the same expensive skill, memory, soul, marketplace, prompt, and tool resolution that should primarily be needed for actual runs.

## Secondary Issue: New Thread History 404

A separate but related issue still exists for newly created threads:

- first history request can return `404`
- shortly afterward the same thread can successfully start `runs/stream`

This indicates a timing race between:

- Gateway thread creation
- LangGraph thread sync/checkpointer availability
- the first frontend history request

This issue is partially mitigated by the new Gateway-side retry added to LangGraph thread sync, but it is not fully eliminated yet.

## Why This Matters

Because the frontend requests history on thread mount and thread switch, the user experiences history slowness as:

- difficult thread switching
- refreshes that appear hung
- the feeling that concurrent threads block each other even when run queueing has improved

This means history performance is now a user-facing bottleneck, not just a backend implementation detail.

## Recommended Minimal Fix

Introduce a lightweight "history-like" path in `make_lead_agent(config)`.

Based on observed config differences, a practical first-pass condition is:

- `thread_id` exists
- `run_id` does not exist

For this history-like path, skip the expensive pre-resolution steps:

- skill catalog resolution
- memory resolution
- soul resolution
- marketplace gating resolution

Keep:

- thread ownership checks
- user resolution from thread fallback when needed
- normal graph construction delegation

This should reduce the history path cost without changing the actual run path.

## Follow-Up Work

1. Implement the history-like lightweight branch in `backend/app/langgraph_runtime.py`
2. Verify that thread switching latency drops materially
3. Re-test new thread first-load behavior and history completeness
4. Consider enabling isolated background job loops if shared-loop blocking remains a problem

## API-Only Reproduction Strategy

The current issue can be investigated and regression-tested without relying entirely on the browser GUI.

This is useful because the browser path introduces extra noise:

- Next.js route transitions
- RSC requests
- React state timing
- client reconnect behavior

Those are still important for full UX validation, but the backend correctness and performance issues can be reproduced more directly with HTTP calls.

### What API-only tests can cover well

- thread creation correctness
- LangGraph thread sync timing
- history latency and `404` behavior
- run startup latency
- upload visibility and runtime file access
- concurrent thread behavior under load

### What API-only tests do **not** fully replace

- browser navigation UX
- client-side optimistic message behavior
- `useStream` lifecycle edge cases
- Next.js page rendering delays

### Recommended API replay sequence

For a near-browser backend replay, use the same authenticated user context and exercise these calls:

1. `POST /api/threads`
2. `POST /api/langgraph/threads/{thread_id}/history`
3. `POST /api/threads/{thread_id}/runs`
4. `POST /api/langgraph/threads/{thread_id}/runs/stream`
5. Repeat `history` calls while switching between two thread IDs

This reproduces the most important backend behavior of:

- creating threads
- loading thread history
- starting runs
- switching across active threads

### Recommended automation direction

The most practical long-term test harness is a small script-based replay tool that:

- creates one or more threads
- starts runs on multiple threads concurrently
- polls or requests history repeatedly
- optionally uploads a file and asks the agent to read it
- records timing such as:
  - thread create latency
  - history latency
  - queue wait
  - stream start latency
  - success/failure status

This would provide a repeatable regression test for the issues documented here and reduce dependence on manual browser testing for backend diagnosis.

## Files Involved

- `backend/langgraph.json`
- `backend/app/langgraph_runtime.py`
- `backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- `backend/packages/harness/deerflow/agents/lead_agent/prompt.py`
- `frontend/src/core/threads/hooks.ts`
