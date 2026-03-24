import { getBackendBaseURL } from "@/core/config";

import type {
  OrgDetail,
  OrgQuotas,
  OrgSummary,
  OrgUsageBreakdown,
  UsageSummary,
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

export async function getUsageByOrg(): Promise<OrgUsageBreakdown[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/admin/organizations`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to get usage by org: ${res.statusText}`);
  const orgs = (await res.json()) as OrgSummary[];
  return orgs.map((org) => ({
    org_id: org.id,
    org_name: org.name,
    input_tokens: 0,
    output_tokens: 0,
    api_calls: 0,
  }));
}
