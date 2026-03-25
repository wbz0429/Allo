import { getBackendBaseURL } from "@/core/config";

import type {
  ModelInfo,
  ModelsConfig,
  TenantConfig,
  ToolGroupInfo,
  ToolsConfig,
} from "./types";

export async function getTenantConfig(): Promise<TenantConfig> {
  const res = await fetch(`${getBackendBaseURL()}/api/config`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to load config: ${res.statusText}`);
  return res.json() as Promise<TenantConfig>;
}

export async function updateTenantConfig(
  config: Partial<TenantConfig>,
): Promise<TenantConfig> {
  const res = await fetch(`${getBackendBaseURL()}/api/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(`Failed to update config: ${res.statusText}`);
  return res.json() as Promise<TenantConfig>;
}

export async function listModels(): Promise<ModelInfo[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/config/models`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to load models: ${res.statusText}`);
  const data = (await res.json()) as { models?: ModelInfo[] };
  return Array.isArray(data.models) ? data.models : [];
}

export async function updateModelsConfig(
  config: ModelsConfig,
): Promise<ModelsConfig> {
  const res = await fetch(`${getBackendBaseURL()}/api/config/models`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(config),
  });
  if (!res.ok)
    throw new Error(`Failed to update models config: ${res.statusText}`);
  return res.json() as Promise<ModelsConfig>;
}

export async function listToolGroups(): Promise<ToolGroupInfo[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/config/tools`, {
    credentials: "include",
  });
  if (!res.ok)
    throw new Error(`Failed to load tool groups: ${res.statusText}`);
  const data = (await res.json()) as { tool_groups: ToolGroupInfo[] };
  return data.tool_groups;
}

export async function updateToolsConfig(
  config: ToolsConfig,
): Promise<ToolsConfig> {
  const res = await fetch(`${getBackendBaseURL()}/api/config/tools`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(config),
  });
  if (!res.ok)
    throw new Error(`Failed to update tools config: ${res.statusText}`);
  return res.json() as Promise<ToolsConfig>;
}
