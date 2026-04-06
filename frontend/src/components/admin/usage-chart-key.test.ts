import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

void test("usage chart key generation uses id before fallback", async () => {
  const file = new URL("./usage-chart.tsx", import.meta.url);
  const source = await readFile(file, "utf8");

  assert.equal(source.includes("bar.id ?? `${bar.label}-${index}`"), true);
});

void test("usage chart key generation no longer depends on label and values only", async () => {
  const file = new URL("./usage-chart.tsx", import.meta.url);
  const source = await readFile(file, "utf8");

  assert.equal(
    source.includes("`${bar.label}-${bar.value}-${bar.secondaryValue ?? 0}`"),
    false,
  );
});
