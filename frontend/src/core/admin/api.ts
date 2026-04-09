import { getBackendBaseURL } from "@/core/config";

import type {
  OrgDetail,
  OrgQuotas,
  OrgSummary,
  UsageSummary,
  UserUsageRanking,
} from "./types";

export async function listOrganizations(): Promise<OrgSummary[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/admin/organizations`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to list organizations: ${res.statusText}`);
  return res.json() as Promise<OrgSummary[]>;
}

export async function getOrganization(id: string): Promise<OrgDetail> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/admin/organizations/${id}`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error(`Failed to get organization: ${res.statusText}`);
  return res.json() as Promise<OrgDetail>;
}

export async function updateOrgQuotas(
  id: string,
  quotas: Partial<OrgQuotas>,
): Promise<OrgQuotas> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/admin/organizations/${id}/quotas`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(quotas),
    },
  );
  if (!res.ok) throw new Error(`Failed to update quotas: ${res.statusText}`);
  return res.json() as Promise<OrgQuotas>;
}

export async function getUsageSummary(): Promise<UsageSummary> {
  const res = await fetch(`${getBackendBaseURL()}/api/admin/usage`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to get usage summary: ${res.statusText}`);
  return res.json() as Promise<UsageSummary>;
}

export async function getUserUsageRanking(
  metric: "total_tokens" | "api_calls" | "input_tokens" | "output_tokens" = "total_tokens",
): Promise<UserUsageRanking> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/admin/usage/users?metric=${metric}`,
    {
      credentials: "include",
    },
  );
  if (!res.ok) throw new Error(`Failed to get user usage ranking: ${res.statusText}`);
  return res.json() as Promise<UserUsageRanking>;
}
