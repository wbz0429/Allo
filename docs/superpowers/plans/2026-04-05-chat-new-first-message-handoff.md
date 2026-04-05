# Chat New First Message Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/workspace/chats/new` navigate to the real thread page first, then submit the first text message from the mounted thread page.

**Architecture:** Store a one-time pending first-message payload in `sessionStorage` on the welcome page, navigate to the real thread URL, then consume and submit that payload from the mounted thread page once the real thread context is active. Keep the existing `useStream` flow for normal thread pages and avoid the broken welcome-page direct submit path.

**Tech Stack:** Next.js app router, React client hooks, sessionStorage, existing `useThreadStream` hook, node:test

---

### Task 1: Add pending first-message utility

**Files:**

- Create: `frontend/src/core/threads/pending.ts`
- Test: `frontend/src/core/threads/pending.test.ts`

- [ ] Add a tiny serializer/parser for one-time pending chat payloads.
- [ ] Cover serialize/parse/remove behavior with `node:test`.

### Task 2: Route welcome-page submit through handoff

**Files:**

- Modify: `frontend/src/app/workspace/chats/[thread_id]/page.tsx`
- Modify: `frontend/src/components/workspace/chats/use-thread-chat.ts`

- [ ] On `/workspace/chats/new`, if the first submission is text-only, persist the payload and navigate to `/workspace/chats/<threadId>` instead of calling `sendMessage()` immediately.
- [ ] Keep existing direct submit behavior for normal thread pages.

### Task 3: Consume pending payload on mounted thread page

**Files:**

- Modify: `frontend/src/app/workspace/chats/[thread_id]/page.tsx`
- Modify: `frontend/src/core/threads/hooks.test.ts`

- [ ] After the real thread page mounts, read and clear the pending payload for that thread id.
- [ ] Submit it exactly once via the normal `sendMessage(threadId, message)` path.
- [ ] Add a regression test that checks the welcome-page path now uses pending handoff instead of direct submit.

### Task 4: Verify and deploy

**Files:**

- Modify: `frontend/src/core/threads/hooks.test.ts`
- Test: `frontend/src/core/threads/pending.test.ts`

- [ ] Run `node --test` for the new tests.
- [ ] Run `pnpm lint`, `pnpm typecheck`, and `pnpm build`.
- [ ] Deploy the frontend-only change and re-test `/workspace/chats/new` online.
