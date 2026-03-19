import { getBackendBaseURL } from "../config";

import type { UserMemory } from "./types";

export async function loadMemory() {
  const memory = await fetch(`${getBackendBaseURL()}/api/memory`, {
    credentials: "include",
  });
  const json = await memory.json();
  return json as UserMemory;
}
