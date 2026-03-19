import { getBackendBaseURL } from "../config";

import type { Model } from "./types";

export async function loadModels() {
  const res = await fetch(`${getBackendBaseURL()}/api/models`, {
    credentials: "include",
  });
  const { models } = (await res.json()) as { models: Model[] };
  return models;
}
