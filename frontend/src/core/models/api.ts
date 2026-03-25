import { getBackendBaseURL } from "../config";

import type { Model } from "./types";

export async function loadModels() {
  const res = await fetch(`${getBackendBaseURL()}/api/models`, {
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`Failed to load models: ${res.status} ${res.statusText}`);
  }

  const data = (await res.json()) as { models?: Model[] };
  return Array.isArray(data.models) ? data.models : [];
}
