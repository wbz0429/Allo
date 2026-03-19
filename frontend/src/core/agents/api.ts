import { getBackendBaseURL } from "@/core/config";

import type {
  Agent,
  AgentTemplate,
  CreateAgentFromTemplateRequest,
  CreateAgentRequest,
  UpdateAgentRequest,
} from "./types";

export async function listAgents(): Promise<Agent[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/agents`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to load agents: ${res.statusText}`);
  const data = (await res.json()) as { agents: Agent[] };
  return data.agents;
}

export async function getAgent(name: string): Promise<Agent> {
  const res = await fetch(`${getBackendBaseURL()}/api/agents/${name}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Agent '${name}' not found`);
  return res.json() as Promise<Agent>;
}

export async function createAgent(request: CreateAgentRequest): Promise<Agent> {
  const res = await fetch(`${getBackendBaseURL()}/api/agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to create agent: ${res.statusText}`);
  }
  return res.json() as Promise<Agent>;
}

export async function updateAgent(
  name: string,
  request: UpdateAgentRequest,
): Promise<Agent> {
  const res = await fetch(`${getBackendBaseURL()}/api/agents/${name}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to update agent: ${res.statusText}`);
  }
  return res.json() as Promise<Agent>;
}

export async function deleteAgent(name: string): Promise<void> {
  const res = await fetch(`${getBackendBaseURL()}/api/agents/${name}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to delete agent: ${res.statusText}`);
}

export async function checkAgentName(
  name: string,
): Promise<{ available: boolean; name: string }> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/agents/check?name=${encodeURIComponent(name)}`,
    { credentials: "include" },
  );
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      err.detail ?? `Failed to check agent name: ${res.statusText}`,
    );
  }
  return res.json() as Promise<{ available: boolean; name: string }>;
}

export async function listAgentTemplates(): Promise<AgentTemplate[]> {
  const res = await fetch(`${getBackendBaseURL()}/api/agent-templates`, {
    credentials: "include",
  });
  if (!res.ok)
    throw new Error(`Failed to load templates: ${res.statusText}`);
  const data = (await res.json()) as { templates: AgentTemplate[] };
  return data.templates;
}

export async function getAgentTemplate(
  templateId: string,
): Promise<AgentTemplate> {
  const res = await fetch(
    `${getBackendBaseURL()}/api/agent-templates/${templateId}`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error(`Template '${templateId}' not found`);
  return res.json() as Promise<AgentTemplate>;
}

export async function createAgentFromTemplate(
  request: CreateAgentFromTemplateRequest,
): Promise<Agent> {
  const res = await fetch(`${getBackendBaseURL()}/api/agents/from-template`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      err.detail ?? `Failed to create agent from template: ${res.statusText}`,
    );
  }
  return res.json() as Promise<Agent>;
}
