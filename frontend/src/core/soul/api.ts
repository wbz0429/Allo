import { getBackendBaseURL } from "@/core/config";

export async function getSoul(): Promise<string> {
  const resp = await fetch(`${getBackendBaseURL()}/api/users/me/soul`, {
    credentials: "include",
  });
  if (!resp.ok) return "";
  const data = await resp.json();
  return data.content ?? "";
}

export async function saveSoul(content: string): Promise<void> {
  await fetch(`${getBackendBaseURL()}/api/users/me/soul`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ content }),
  });
}
