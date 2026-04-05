import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import test from "node:test"

void test("useThreadStream defers onStart until the stream creates the thread", async () => {
  const file = new URL("./hooks.ts", import.meta.url)
  const source = await readFile(file, "utf8")

  assert.equal(
    source.includes("_handleOnStart(threadId);"),
    false,
    "useThreadStream should not trigger onStart before thread.submit() for new threads",
  )
})

void test("useThreadStream does not pre-create the LangGraph thread before submit", async () => {
  const file = new URL("./hooks.ts", import.meta.url)
  const source = await readFile(file, "utf8")

  assert.equal(
    source.includes("await ensureLangGraphThread(gatewayThreadId, isMock);"),
    false,
    "useThreadStream should let useStream.submit() create the LangGraph thread for new chats",
  )
})

void test("useThreadStream switches internal stream thread id before submit for new chats", async () => {
  const file = new URL("./hooks.ts", import.meta.url)
  const source = await readFile(file, "utf8")

  assert.equal(
    source.includes("setOnStreamThreadId(normalizedThreadId);"),
    true,
    "useThreadStream should sync internal stream thread id when the page switches to a real thread",
  )
})
