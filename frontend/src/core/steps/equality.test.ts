import assert from "node:assert/strict";
import test from "node:test";

import type { ExecutionStep } from "./types";

async function loadEqualityModule() {
  return import(new URL("./equality.ts", import.meta.url).href);
}

function createStep(id: string, overrides: Partial<ExecutionStep> = {}): ExecutionStep {
  return {
    id,
    index: 0,
    type: "response",
    title: `step-${id}`,
    status: "completed",
    groupId: id,
    ...overrides,
  };
}

void test("areStepsEqual returns true for identical step arrays", async () => {
  const { areStepsEqual } = await loadEqualityModule();
  const steps = [createStep("a"), createStep("b", { index: 1 })];

  assert.equal(areStepsEqual(steps, [...steps]), true);
});

void test("areStepsEqual returns false when step content changes", async () => {
  const { areStepsEqual } = await loadEqualityModule();

  assert.equal(
    areStepsEqual([createStep("a")], [createStep("a", { status: "in_progress" })]),
    false,
  );
});

void test("areStepsEqual returns false when lengths differ", async () => {
  const { areStepsEqual } = await loadEqualityModule();

  assert.equal(areStepsEqual([createStep("a")], [createStep("a"), createStep("b")]), false);
});
