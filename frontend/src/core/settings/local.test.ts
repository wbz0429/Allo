import assert from "node:assert/strict";
import test from "node:test";

import { getLocalSettings } from "./local";

void test("getLocalSettings falls back to autonomous for legacy mode values", () => {
  const storage = new Map<string, string>();
  storage.set(
    "allo.local-settings",
    JSON.stringify({
      context: {
        mode: "flash",
      },
    }),
  );

  const localStorageMock = {
    getItem(key: string) {
      return storage.get(key) ?? null;
    },
    setItem(key: string, value: string) {
      storage.set(key, value);
    },
    removeItem(key: string) {
      storage.delete(key);
    },
  };

  Object.defineProperty(globalThis, "window", {
    value: { localStorage: localStorageMock },
    configurable: true,
  });
  Object.defineProperty(globalThis, "localStorage", {
    value: localStorageMock,
    configurable: true,
  });

  const settings = getLocalSettings();

  assert.equal(settings.context.mode, "autonomous");
});

void test("getLocalSettings preserves supported mode values", () => {
  const storage = new Map<string, string>();
  storage.set(
    "allo.local-settings",
    JSON.stringify({
      context: {
        mode: "precise",
      },
    }),
  );

  const localStorageMock = {
    getItem(key: string) {
      return storage.get(key) ?? null;
    },
    setItem(key: string, value: string) {
      storage.set(key, value);
    },
    removeItem(key: string) {
      storage.delete(key);
    },
  };

  Object.defineProperty(globalThis, "window", {
    value: { localStorage: localStorageMock },
    configurable: true,
  });
  Object.defineProperty(globalThis, "localStorage", {
    value: localStorageMock,
    configurable: true,
  });

  const settings = getLocalSettings();

  assert.equal(settings.context.mode, "precise");
});
