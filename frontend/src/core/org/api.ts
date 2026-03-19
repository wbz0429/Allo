import { getBackendBaseURL } from "@/core/config";

import type {
  OrgMember,
  OrgUsageStats,
  UserUsageBreakdown,
} from "./types";

export async function listOrgMembers(): Promise<OrgMember[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/org/members`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to list members: ${res.statusText}`);
  const data = (await res.json()) as { members: OrgMember[] };
  return data.members;
}

export async function inviteMember(email: string): Promise<OrgMember> {
  const res = await fetch(`${getBackendBaseURL()}/api/org/members/invite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error(`Failed to invite member: ${res.statusText}`);
  return res.json() as Promise<OrgMember>;
}

export async function removeMember(userId: string): Promise<void> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/org/members/${userId}`,
    {
      method: "DELETE",
      credentials: "include",
    },
  );
  if (!res.ok) throw new Error(`Failed to remove member: ${res.statusText}`);
}

export async function updateMemberRole(
  userId: string,
  role: "admin" | "member",
): Promise<OrgMember> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/org/members/${userId}/role`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ role }),
    },
  );
  if (!res.ok) throw new Error(`Failed to update role: ${res.statusText}`);
  return res.json() as Promise<OrgMember>;
}

export async function getOrgUsage(): Promise<OrgUsageStats> {
  const res = await fetch(`${getBackendBaseURL()}/api/org/usage`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to get org usage: ${res.statusText}`);
  return res.json() as Promise<OrgUsageStats>;
}

export async function getOrgUsageByUser(): Promise<UserUsageBreakdown[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/org/usage/by-user`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to get usage by user: ${res.statusText}`);
  const data = (await res.json()) as { usage: UserUsageBreakdown[] };
  return data.usage;
}
