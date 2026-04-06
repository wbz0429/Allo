import test from "node:test";
import assert from "node:assert/strict";


function createStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear() {
      map.clear();
    },
    getItem(key: string) {
      return map.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(map.keys())[index] ?? null;
    },
    removeItem(key: string) {
      map.delete(key);
    },
    setItem(key: string, value: string) {
      map.set(key, value);
    },
  } as Storage;
}

async function loadPendingModule() {
  return import(new URL("./pending.ts", import.meta.url).href);
}

test("pending thread message preserves selected knowledge bases", async () => {
  const { loadPendingThreadMessage, savePendingThreadMessage } = await loadPendingModule();
  const storage = createStorage();

  savePendingThreadMessage(storage, {
    threadId: "thread-1",
    text: "hello",
    knowledgeBases: [{ id: "kb-1", name: "Contracts" }],
  });

  assert.deepEqual(loadPendingThreadMessage(storage, "thread-1"), {
    threadId: "thread-1",
    text: "hello",
    files: undefined,
    knowledgeBases: [{ id: "kb-1", name: "Contracts" }],
  });
});

test("pending thread message preserves first-message files", async () => {
  const { loadPendingThreadMessage, savePendingThreadMessage } = await loadPendingModule();
  const storage = createStorage();

  savePendingThreadMessage(storage, {
    threadId: "thread-files",
    text: "hello with file",
    files: [{ type: "file", filename: "report.pdf", mediaType: "application/pdf", url: "blob:abc" }],
  });

  assert.deepEqual(loadPendingThreadMessage(storage, "thread-files"), {
    threadId: "thread-files",
    text: "hello with file",
    files: [{ type: "file", filename: "report.pdf", mediaType: "application/pdf", url: "blob:abc" }],
    knowledgeBases: undefined,
  });
});

test("pending thread message round-trips text payload", async () => {
  const { loadPendingThreadMessage, savePendingThreadMessage } = await loadPendingModule();
  const storage = createStorage();

  savePendingThreadMessage(storage, {
    threadId: "thread-2",
    text: "hello again",
  });

  assert.deepEqual(loadPendingThreadMessage(storage, "thread-2"), {
    threadId: "thread-2",
    text: "hello again",
    files: undefined,
    knowledgeBases: undefined,
  });
});

test("loading pending thread message clears it", async () => {
  const { loadPendingThreadMessage, savePendingThreadMessage } = await loadPendingModule();
  const storage = createStorage();

  savePendingThreadMessage(storage, {
    threadId: "thread-3",
    text: "bye",
  });

  assert.equal(loadPendingThreadMessage(storage, "thread-3")?.text, "bye");
  assert.equal(loadPendingThreadMessage(storage, "thread-3"), null);
});

test("clearPendingThreadMessage removes stored payload", async () => {
  const {
    clearPendingThreadMessage,
    loadPendingThreadMessage,
    savePendingThreadMessage,
  } = await loadPendingModule();
  const storage = createStorage();

  savePendingThreadMessage(storage, {
    threadId: "thread-4",
    text: "clear me",
  });
  clearPendingThreadMessage(storage, "thread-4");

  assert.equal(loadPendingThreadMessage(storage, "thread-4"), null);
});
