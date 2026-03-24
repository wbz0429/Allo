import { getBackendBaseURL } from "@/core/config";

import type {
  MarketplaceSkill,
  MarketplaceTool,
  OrgInstalledSkill,
  OrgInstalledTool,
} from "./types";

// --- Tools ---

export async function listMarketplaceTools(): Promise<MarketplaceTool[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/marketplace/tools`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to load tools: ${res.statusText}`);
  return res.json() as Promise<MarketplaceTool[]>;
}

export async function getMarketplaceTool(
  id: string,
): Promise<MarketplaceTool> {
  const res = await fetch(`${getBackendBaseURL()}/api/marketplace/tools/${id}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to load tool: ${res.statusText}`);
  return res.json() as Promise<MarketplaceTool>;
}

export async function installTool(
  id: string,
  configJson: Record<string, string>,
): Promise<OrgInstalledTool> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/marketplace/tools/${id}/install`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ config_json: JSON.stringify(configJson) }),
    },
  );
  if (!res.ok) throw new Error(`Failed to install tool: ${res.statusText}`);
  return res.json() as Promise<OrgInstalledTool>;
}

export async function uninstallTool(id: string): Promise<void> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/marketplace/tools/${id}/install`,
    {
      method: "DELETE",
      credentials: "include",
    },
  );
  if (!res.ok) throw new Error(`Failed to uninstall tool: ${res.statusText}`);
}

export async function listOrgTools(): Promise<OrgInstalledTool[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/marketplace/installed/tools`, {
    credentials: "include",
  });
  if (!res.ok)
    throw new Error(`Failed to load installed tools: ${res.statusText}`);
  return res.json() as Promise<OrgInstalledTool[]>;
}

// --- Skills ---

export async function listMarketplaceSkills(): Promise<MarketplaceSkill[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/marketplace/skills`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to load skills: ${res.statusText}`);
  return res.json() as Promise<MarketplaceSkill[]>;
}

export async function getMarketplaceSkill(
  id: string,
): Promise<MarketplaceSkill> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/marketplace/skills/${id}`,
    {
      credentials: "include",
    },
  );
  if (!res.ok) throw new Error(`Failed to load skill: ${res.statusText}`);
  return res.json() as Promise<MarketplaceSkill>;
}

export async function installSkill(id: string): Promise<OrgInstalledSkill> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/marketplace/skills/${id}/install`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    },
  );
  if (!res.ok) throw new Error(`Failed to install skill: ${res.statusText}`);
  return res.json() as Promise<OrgInstalledSkill>;
}

export async function uninstallSkill(id: string): Promise<void> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/marketplace/skills/${id}/install`,
    {
      method: "DELETE",
      credentials: "include",
    },
  );
  if (!res.ok)
    throw new Error(`Failed to uninstall skill: ${res.statusText}`);
}

export async function listOrgSkills(): Promise<OrgInstalledSkill[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/marketplace/installed/skills`, {
    credentials: "include",
  });
  if (!res.ok)
    throw new Error(`Failed to load installed skills: ${res.statusText}`);
  return res.json() as Promise<OrgInstalledSkill[]>;
}
