import assert from "node:assert/strict"
import test from "node:test"

class MemoryStorage implements Storage {
  private map = new Map<string, string>()

  get length() {
    return this.map.size
  }

  clear() {
    this.map.clear()
  }

  getItem(key: string) {
    return this.map.get(key) ?? null
  }

  key(index: number) {
    return Array.from(this.map.keys())[index] ?? null
  }

  removeItem(key: string) {
    this.map.delete(key)
  }

  setItem(key: string, value: string) {
    this.map.set(key, value)
  }
}

async function loadPendingModule() {
  return import(new URL("./pending.ts", import.meta.url).href)
}

void test("pending thread message round-trips text payload", async () => {
  const { loadPendingThreadMessage, savePendingThreadMessage } = await loadPendingModule()
  const storage = new MemoryStorage()

  savePendingThreadMessage(storage, {
    threadId: "thread-1",
    text: "hello",
  })

  assert.deepEqual(loadPendingThreadMessage(storage, "thread-1"), {
    threadId: "thread-1",
    text: "hello",
  })
})

void test("loading pending thread message clears it", async () => {
  const { loadPendingThreadMessage, savePendingThreadMessage } = await loadPendingModule()
  const storage = new MemoryStorage()

  savePendingThreadMessage(storage, {
    threadId: "thread-2",
    text: "hello again",
  })

  assert.equal(loadPendingThreadMessage(storage, "thread-2")?.text, "hello again")
  assert.equal(loadPendingThreadMessage(storage, "thread-2"), null)
})

void test("clearPendingThreadMessage removes stored payload", async () => {
  const {
    clearPendingThreadMessage,
    loadPendingThreadMessage,
    savePendingThreadMessage,
  } = await loadPendingModule()
  const storage = new MemoryStorage()

  savePendingThreadMessage(storage, {
    threadId: "thread-3",
    text: "bye",
  })
  clearPendingThreadMessage(storage, "thread-3")

  assert.equal(loadPendingThreadMessage(storage, "thread-3"), null)
})
