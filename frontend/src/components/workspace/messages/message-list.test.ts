import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

void test("MessageList syncs steps through effect", async () => {
  const file = new URL("./message-list.tsx", import.meta.url);
  const source = await readFile(file, "utf8");

  assert.equal(source.includes("useEffect(() => {\n    setSteps(steps);\n  }, [steps, setSteps]);"), true);
});

void test("MessageList derives step data from messages and streaming state", async () => {
  const file = new URL("./message-list.tsx", import.meta.url);
  const source = await readFile(file, "utf8");

  assert.equal(source.includes("() => extractSteps(messages, t, thread.isLoading)"), true);
});
