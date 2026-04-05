import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import test from "node:test"

void test("new chat page saves pending first message before navigating", async () => {
  const file = new URL("./[thread_id]/page.tsx", import.meta.url)
  const source = await readFile(file, "utf8")

  assert.equal(source.includes("savePendingThreadMessage(window.sessionStorage"), true)
  assert.equal(source.includes("void sendMessage(threadId, message);"), true)
  assert.equal(
    source.includes("if (isNewThread && message.files.length === 0 && typeof window !== \"undefined\")"),
    true,
  )
})

void test("mounted thread page consumes pending first message once", async () => {
  const file = new URL("./[thread_id]/page.tsx", import.meta.url)
  const source = await readFile(file, "utf8")

  assert.equal(source.includes("loadPendingThreadMessage(window.sessionStorage, threadId)"), true)
  assert.equal(source.includes("consumedRef.current = threadId;"), true)
  assert.equal(source.includes("void sendMessage(threadId, { text: pending.text, files: [] });"), true)
})
